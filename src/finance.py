#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""finance.py — 个人财报原型编排器（薄壳）

职责：
  1. 调用 double-entry-generator (deg) 把支付宝/微信/银行账单翻译成 hledger journal；
  2. 调用 hledger 生成 一季报/半年报/三季报/年报（累计口径）五件套：
     资产负债表 / 利润表 / 现金流量表 / 含权益资产负债表 / 结账快照；
  3. 用 Edge headless 把 HTML 财报打印为 PDF；
  4. 结账/反结账：结账=快照+生成留存收益结转分录；反结账=撤掉该期结转。

设计原则：账本是纯文本（UTF-8），本脚本只是"胶水"，不实现任何会计引擎。
"""
import argparse
import csv
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journal_stats import smoke_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
JOURNALS_DIR = ROOT / "journals"
CLOSE_DIR = ROOT / "close"
REPORTS_DIR = ROOT / "reports"
RAW_DIR = ROOT / "raw"
CONFIG_DIR = ROOT / "config"
DEG = ROOT / "tools" / "double-entry-generator.exe"
HL = ROOT / "tools" / "hledger-bin" / "hledger.exe"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")

STATEMENTS = {
    "1_资产负债表": "balancesheet",
    "2_利润表": "incomestatement",
    "3_现金流量表": "cashflow",
    "4_含权益资产负债表": "balancesheetequity",
}


def run_console_utf8(args, capture=True):
    """在 UTF-8 控制台代码页下运行外部命令并拿到 UTF-8 字节输出。"""
    subprocess.run(["chcp.com", "65001"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=False)
    return subprocess.run(args, capture_output=capture)


def journal_files():
    files = sorted(JOURNALS_DIR.glob("*.journal"))
    if not files:
        sys.exit("journals/ 下没有 .journal 文件")
    return [str(f) for f in files]


def journal_args():
    args = []
    for f in journal_files():
        args += ["-f", f]
    return args


def hledger(*args, input_text=None):
    """运行 hledger；返回 UTF-8 解码后的 stdout。"""
    cmd = [str(HL), *[str(a) for a in args]]
    if input_text is not None:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate(input_text.encode("utf-8"))
        code = proc.returncode
    else:
        # 先切到 UTF-8 代码页，再运行
        subprocess.run(["chcp.com", "65001"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
        proc = subprocess.run(cmd, capture_output=True)
        out, err, code = proc.stdout, proc.stderr, proc.returncode
    if code != 0:
        sys.exit(f"hledger 失败({code}): {err.decode('utf-8', errors='replace')[:400]}")
    return out.decode("utf-8", errors="replace")


def check():
    out = hledger(*journal_args(), "check")
    print("check OK —", out or "账本平衡")


def _iter_alipay_rows(bill: Path):
    header = False
    with open(bill, encoding="gbk", errors="replace") as f:
        for row in csv.reader(f):
            if not row:
                continue
            if row[0].strip() == "交易时间":
                header = True
                continue
            if header and row[0] and not row[0].startswith("-"):
                yield row


def _iter_wechat_rows(bill: Path):
    import openpyxl
    wb = openpyxl.load_workbook(bill, read_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and str(r[0]).strip() == "交易时间")
    header = [str(c).strip() for c in rows[hi]]
    ix = {n: i for i, n in enumerate(header)}
    for r in rows[hi + 1:]:
        if r and r[0]:
            yield {n: (str(r[i]).strip() if i < len(r) and r[i] is not None else "")
                   for n, i in ix.items()}


def count_source_rows(platform, bill: Path):
    """数源账单数据行（冒烟比对用）。无法解析时返回 None。"""
    try:
        if platform == "alipay":
            return sum(1 for _ in _iter_alipay_rows(bill))
        if platform == "wechat":
            return sum(1 for _ in _iter_wechat_rows(bill))
    except Exception as e:  # noqa: BLE001
        print(f"   [警告] 源行数解析失败：{e}")
    return None


def attribute_drops(platform, bill: Path, journal_path: Path, deg_stderr: str):
    """精确行数归因：源 orderId 集合 − journal orderId 集合 = 被剔行，按状态分项。
    返回报告文本；无法解析时返回 None。"""
    import re
    try:
        if platform == "alipay":
            src = [(r[9].strip().strip("\t"), r[8].strip())
                   for r in _iter_alipay_rows(bill) if len(r) > 9]
        elif platform == "wechat":
            src = [(r.get("交易单号", ""), r.get("当前状态", "") + "|" + r.get("交易类型", ""))
                   for r in _iter_wechat_rows(bill)]
        else:
            return None
        jtext = journal_path.read_text(encoding="utf-8")
        jids = set(re.findall(r'; orderId: "([^"]+)"', jtext))
        dropped = [(oid, st) for oid, st in src if oid and oid not in jids]
        from collections import Counter
        by_status = Counter(st for _, st in dropped)
        # 退款配对中的原单（deg 日志 "Refund for [orderId X]" 的 X）
        refund_originals = set(re.findall(r"Refund for \[orderId ([^\]]+)\]", deg_stderr))
        n_originals = sum(1 for oid, st in dropped if oid in refund_originals)
        unexplained = [(oid, st) for oid, st in dropped
                       if oid not in refund_originals
                       and "关闭" not in st and "撤销" not in st
                       and "退款" not in st]
        parts = [f"剔除 {len(dropped)} 行："]
        for st, n in by_status.most_common():
            tag = "（退款配对原单）" if st in ("交易成功", "支付成功") and n == n_originals and n > 0 else ""
            parts.append(f"  {st} ×{n}{tag}")
        parts.append(f"未解释 {len(unexplained)} 行" +
                     ("  ✅" if not unexplained else f"  ⚠️ {unexplained[:3]}"))
        return "\n".join(parts)
    except Exception as e:  # noqa: BLE001
        return f"   [警告] 归因分析失败：{e}"


# deg v2.15.1 会静默吞掉支付宝 CSV 表头后第一行数据（红队 R1 探针实证）。
# 对策：表头后插入一行"献祭"占位行（状态=交易关闭，即使未被吞也会被 L0 规则丢弃）。
DUMMY_ROW = ("1970-01-01 00:00:00,其他,占位,/,deg首行吞行占位(献祭行),支出,0.01,"
             "余额,交易关闭,,,\n")


def preprocess_alipay(bill: Path) -> Path:
    """生成插入献祭行的临时 CSV，返回临时文件路径。"""
    tmp = bill.with_name(f".deg-tmp-{bill.name}")
    text = bill.read_text(encoding="gbk", errors="replace")
    lines = text.splitlines(keepends=True)
    hi = next(i for i, l in enumerate(lines) if l.startswith("交易时间"))
    lines.insert(hi + 1, DUMMY_ROW)
    tmp.write_text("".join(lines), encoding="gbk", errors="replace")
    return tmp


# 各平台导入任务：pattern 匹配 raw/ 下账单；deg_extra 为该 provider 的额外参数
IMPORT_JOBS = [
    ("alipay", "支付宝交易明细*.csv", "config/alipay.yaml", []),
    ("wechat", "微信支付账单流水文件*.xlsx", "config/wechat.yaml",
     ["--ignore-invalid-tx-types"]),  # 理财通赎回等 deg 未收录类型靠规则原文匹配
]


def import_bills():
    """raw/ 下的支付宝 CSV / 微信 XLSX → deg → journals/import-*.journal，逐平台冒烟。"""
    any_import = False
    alipay_outputs = []
    for platform, pattern, cfg, deg_extra in IMPORT_JOBS:
        bills = sorted(RAW_DIR.glob(pattern))
        if not bills:
            print(f"[跳过] raw/ 下没有 {platform} 账单（{pattern}）")
            continue
        for bill in bills:
            any_import = True
            out_file = JOURNALS_DIR / f"import-{platform}-{bill.stem}.journal"
            src_rows = count_source_rows(platform, bill)
            tmp = preprocess_alipay(bill) if platform == "alipay" else bill
            subprocess.run(["chcp.com", "65001"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
            res = subprocess.run(
                [str(DEG), "translate", "-p", platform, "-t", "ledger",
                 "--config", str(ROOT / cfg), *deg_extra,
                 str(tmp), "-o", str(out_file)],
                capture_output=True)
            if tmp != bill:
                tmp.unlink(missing_ok=True)
            if res.returncode != 0:
                sys.exit(f"deg 导入失败：{res.stderr.decode('utf-8', errors='replace')[:400]}")
            err = res.stderr.decode("utf-8", errors="replace")
            pairs = err.count("Refund for")
            unprocessed = err.count("unprocessed")
            print(f"已导入 {bill.name} -> {out_file.name}"
                  f"（deg 日志：退款配对 {pairs} 次；保留但提示 {unprocessed} 条；"
                  f"献祭行{'已被吞(R1对策生效)' if platform == 'alipay' and '吞行占位' not in out_file.read_text(encoding='utf-8') else '留存检查'}）")
            report, s = smoke_report(platform, out_file, src_rows)
            print(report)
            attr = attribute_drops(platform, bill, out_file, err)
            if attr:
                print(f"   行数归因: 源 {src_rows} 行 → journal {s['txs']} 笔；{attr}")
            if platform == "alipay":
                alipay_outputs.append(out_file)
    if not any_import:
        print("raw/ 下没有可导入账单")
        return
    # 花呗拆分：有 PDF + 本地密码配置才执行（契约 C3/C6）
    if alipay_outputs and (CONFIG_DIR / "local.yaml").exists() \
            and list(RAW_DIR.glob("*花呗*.pdf")):
        for out in alipay_outputs:
            print(f"── 花呗拆分 {out.name}")
            sp = subprocess.run(
                [sys.executable, str(ROOT / "src" / "split_huabei.py"), str(out)],
                capture_output=True)
            txt = sp.stdout.decode("utf-8", errors="replace")
            print("\n".join(txt.splitlines()[:9]))
            if sp.returncode != 0:
                sys.exit(f"split_huabei 失败：{sp.stderr.decode('utf-8', errors='replace')[:400]}")
            # 拆后终态冒烟（拆分会新增补录分录，FIXME 以拆后为准）
            report, _ = smoke_report(platform, out, None)
            print(f"── 拆后终态 {report.splitlines()[1]}\n   {report.splitlines()[-2]}\n   {report.splitlines()[-1]}")
    # 汇总平衡校验（hledger check 全部 journal）
    check()
    print("导入完成；FIXME 队列见：tools/hledger-bin/hledger.exe -f journals/import-*.journal register FIXME")


def gen_statement(kind: str, start: str, end: str) -> str:
    """kind: bs / is / cf / bse"""
    cmd = {"bs": "balancesheet", "is": "incomestatement",
           "cf": "cashflow", "bse": "balancesheetequity"}[kind]
    return hledger(*journal_args(), cmd, "-b", start, "-e", end)


def report(year: int):
    out_dir = REPORTS_DIR / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    periods = {
        "Q1": f"{year}-04-01",
        "H1": f"{year}-07-01",
        "Q3": f"{year}-10-01",
        "AN": f"{year + 1}-01-01",
    }
    titles = {"Q1": "一季报", "H1": "半年报", "Q3": "三季报", "AN": "年报"}
    for period, end in periods.items():
        html_parts = []
        for fname, cmd in STATEMENTS.items():
            txt = hledger(*journal_args(), cmd,
                          "-b", f"{year}-01-01", "-e", end)
            html = hledger(*journal_args(), cmd,
                           "-b", f"{year}-01-01", "-e", end, "-O", "html")
            (out_dir / f"{period}_{fname}.txt").write_text(txt, encoding="utf-8")
            (out_dir / f"{period}_{fname}.html").write_text(html, encoding="utf-8")
            # CSV 输出与 txt 类似，均从 stdout 生成
            csv = hledger(*journal_args(), cmd,
                          "-b", f"{year}-01-01", "-e", end, "-O", "csv")
            (out_dir / f"{period}_{fname}.csv").write_text(csv, encoding="utf-8")
            html_parts.append(f"<h2>{titles[period]} · {fname}</h2>\n{html}")
        # 汇总单页 + PDF
        combined = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{year}{titles[period]}</title><style>body{{font-family:'Microsoft YaHei',sans-serif;margin:2em}}
table{{border-collapse:collapse;margin-bottom:2em}} th,td{{padding:.3em 1em}}
h2{{border-left:6px solid #2a7;padding-left:.5em}}</style></head>
<body><h1>{year} 年{titles[period]}（累计口径）</h1>{"".join(html_parts)}</body></html>"""
        html_file = out_dir / f"{period}_财报汇总.html"
        html_file.write_text(combined, encoding="utf-8")
        pdf_file = out_dir / f"{period}_财报汇总.pdf"
        if EDGE.exists():
            res = subprocess.run(
                [str(EDGE), "--headless", "--disable-gpu", "--no-sandbox",
                 f"--print-to-pdf={pdf_file}", "--no-pdf-header-footer",
                 html_file.resolve().as_uri()], capture_output=True)
            if res.returncode == 0 and pdf_file.exists():
                print(f"{period}: {pdf_file.name} ({pdf_file.stat().st_size} bytes)")
            else:
                print(f"{period}: PDF 生成失败 {res.stderr[:120]}")
        else:
            print(f"{period}: 未找到 Edge，跳过 PDF")
    print(f"完成：{out_dir}")


def close(year: int, period: str):
    """结账：快照当前账本 + 生成该期留存收益结转分录（不混入报表输入）。"""
    if period not in ("Q1", "H1", "Q3", "AN"):
        sys.exit("period 必须是 Q1/H1/Q3/AN")
    end = {"Q1": f"{year}-04-01", "H1": f"{year}-07-01",
           "Q3": f"{year}-10-01", "AN": f"{year + 1}-01-01"}[period]
    stamp = date.today().isoformat()
    snap_dir = CLOSE_DIR / f"snapshot-{year}-{period}-{stamp}"
    snap_dir.mkdir(parents=True, exist_ok=True)
    for f in JOURNALS_DIR.glob("*.journal"):
        shutil.copy2(f, snap_dir / f.name)
    # 生成结转分录（留存收益）；读取时用 -I 忽略余额断言
    closing = hledger(*journal_args(), "close", "--retain", "-e", end)
    close_file = CLOSE_DIR / f"{year}-{period}-close.journal"
    close_file.write_text(closing, encoding="utf-8")
    print(f"结账完成：快照 {snap_dir}；结转分录 {close_file.name}（后续财报如需'结账后'口径，运行：")
    print(f"  hledger -I -f journals/2026.journal -f close/{close_file.name} <命令>")


def reopen(year: int, period: str):
    close_file = CLOSE_DIR / f"{year}-{period}-close.journal"
    if close_file.exists():
        close_file.unlink()
        print(f"反结账完成：已删除 {close_file.name}（快照仍在 close/ 下可查）")
    else:
        print("没有该期的结账分录")


# ═══════════════ P4.1 现金流预测 + 应急金覆盖月数 ═══════════════

CASH_ACCOUNTS = ["Assets:现金", "Assets:银行存款"]      # 应急金口径：现金及等价物+活期
ESSENTIAL_EXPENSES = ["Expenses:日常三餐", "Expenses:出行交通", "Expenses:日常缴费",
                      "Expenses:医疗健康", "Expenses:房租摊销"]  # 必要支出口径（可随用户调整）


def _balance_map(account_root):
    """hledger balance <root> --flat -O csv → {科目: 金额}"""
    out = hledger(*journal_args(), "balance", account_root, "--flat", "-O", "csv")
    res = {}
    for row in csv.reader(out.splitlines()):
        if len(row) == 2 and row[0].startswith(account_root + ":"):
            amt = row[1].replace("CNY", "").replace(",", "").strip()
            try:
                res[row[0]] = float(amt or 0)
            except ValueError:
                pass
    return res


def forecast(months: int = 12):
    """现金流预测报表 + 应急金覆盖月数（F6/P4.1）。"""
    cash = {a: v for root in CASH_ACCOUNTS for a, v in _balance_map(root).items()}
    cash_total = sum(cash.values())
    # 支出月均值：用利润表区间口径（取账本覆盖月数）
    first = hledger(*journal_args(), "print", "-O", "csv").splitlines()
    dates = sorted(r[1] for r in csv.reader(first)
                   if len(r) > 1 and r[1][:4].isdigit() and int(r[1][:4]) >= 2000)
    span_months = 1
    if dates:
        y1, m1 = int(dates[0][:4]), int(dates[0][5:7])
        y2, m2 = int(dates[-1][:4]), int(dates[-1][5:7])
        span_months = max(1, (y2 - y1) * 12 + (m2 - m1) + 1)
    exp = {a: v for a, v in _balance_map("Expenses").items()}
    essential = sum(v for k, v in exp.items()
                    if any(k == e or k.startswith(e + ":") for e in ESSENTIAL_EXPENSES))
    essential_monthly = essential / span_months
    total_monthly = sum(exp.values()) / span_months
    if essential_monthly > 0:
        coverage_txt = f"{cash_total / essential_monthly:.1f} 个月"
    else:
        coverage_txt = "N/A（账本中无必要支出记录，无法计算）"

    lines = [
        "══ 现金流预测与应急金指标 ══",
        f"账本覆盖: {span_months} 个月",
        f"现金及等价物余额: {cash_total:,.2f}",
        f"  " + "  ".join(f"{a.split(':')[-1]}={v:,.0f}" for a, v in sorted(cash.items()) if abs(v) > 0.005),
        f"月均必要支出（{ '/'.join(e.split(':')[-1] for e in ESSENTIAL_EXPENSES) }）: {essential_monthly:,.2f}",
        f"月均总支出: {total_monthly:,.2f}",
        f"★ 应急金覆盖月数（现金/月均必要支出）: {coverage_txt}",
        "  ⚠️ 注：期初建账（P1.5）前余额为净流量口径（可能为负），指标仅作流程演示；建账后即为真实值。",
        "",
        f"── 未来 {months} 个月预测（hledger --forecast；依赖 `~ monthly` 定期规则，P1.6 金额待用户）──",
    ]
    fc = hledger(*journal_args(), "balance", *CASH_ACCOUNTS,
                 "--forecast", f"today..+{months}months", "--flat")
    lines.append(fc if fc.strip() else "（当前无定期规则，预测=现状平推；P1.6 落地后自动生效）")
    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"forecast-{date.today().isoformat()}.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:9]))
    print(f"完整: {out}")


# ═══════════════ P4.2 月度账实核对 ═══════════════

ACTUAL_FILE = CONFIG_DIR / "actual_balances.yaml"
ACTUAL_TEMPLATE = """# 账实核对：每月手动盘点真实余额后填写（本文件被 .gitignore 排除，仅本地）
# 格式： 科目全名: 实际余额（负债记负数）。没填的科目跳过核对。
# Assets:现金:支付宝: 0.00
# Assets:现金:余额宝: 0.00
# Assets:现金:微信: 0.00
# Assets:现金:零钱通: 0.00
# Assets:银行存款:建设银行: 0.00
# Liabilities:花呗: -0.00
"""


def reconcile(write: bool = False):
    """账面余额 vs 手动实录 → 差异清单 → （--write）调账分录到 journals/reconcile-<date>.journal。"""
    if not ACTUAL_FILE.exists():
        ACTUAL_FILE.write_text(ACTUAL_TEMPLATE, encoding="utf-8")
        print(f"已生成盘点模板 {ACTUAL_FILE}（仅本地，不入库）\n请按真实余额填写后重跑 reconcile")
        return
    actual = {}
    for line in ACTUAL_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        acct, _, amt = line.rpartition(":")
        amt = amt.strip().replace(",", "")
        if amt:
            try:
                actual[acct.strip()] = float(amt)
            except ValueError:
                print(f"[跳过] 无法解析金额: {line}")
    if not actual:
        print(f"{ACTUAL_FILE} 没有有效盘点行（全部注释/空），请先填写真实余额")
        return
    book = {}
    for root in ("Assets", "Liabilities"):
        book.update(_balance_map(root))
    diffs, entries = [], []
    stamp = date.today().isoformat()
    print(f"{'科目':<30}{'账面':>14}{'实盘':>14}{'差异':>12}")
    for acct, av in sorted(actual.items()):
        bv = book.get(acct, 0.0)
        d = round(av - bv, 2)
        mark = "  ⚠️" if abs(d) >= 0.01 else ""
        print(f"{acct:<30}{bv:>14,.2f}{av:>14,.2f}{d:>+12,.2f}{mark}")
        if abs(d) >= 0.01:
            diffs.append((acct, d))
            if d > 0:
                entries += [f"\n{stamp} * 账实核对调账（{acct} 实盘多于账面）",
                            f"    {acct}    {d:.2f} CNY",
                            f"    Equity:期初调整    -{d:.2f} CNY"]
            else:
                entries += [f"\n{stamp} * 账实核对调账（{acct} 实盘少于账面）",
                            f"    Equity:期初调整    {abs(d):.2f} CNY",
                            f"    {acct}    {d:.2f} CNY"]
    if not diffs:
        print("账实一致 ✅，无需调账")
        return
    print(f"\n差异 {len(diffs)} 项" + ("；调账分录已写入，请 check" if write else "（--write 生成分录）"))
    if write:
        out = JOURNALS_DIR / f"reconcile-{stamp}.journal"
        if out.exists():
            sys.exit(f"{out.name} 已存在，拒绝覆盖（同日重复核对请先删除旧文件）")
        out.write_text("; 账实核对调账（reconcile 生成）\n" + "\n".join(entries) + "\n",
                       encoding="utf-8")
        print(f"已写入 {out.name}")
        check()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("import")
    p = sub.add_parser("report"); p.add_argument("year", type=int)
    p = sub.add_parser("close"); p.add_argument("year", type=int); p.add_argument("period")
    p = sub.add_parser("reopen"); p.add_argument("year", type=int); p.add_argument("period")
    p = sub.add_parser("forecast"); p.add_argument("--months", type=int, default=12)
    p = sub.add_parser("reconcile"); p.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.cmd == "check":
        check()
    elif args.cmd == "import":
        import_bills()
    elif args.cmd == "report":
        report(args.year)
    elif args.cmd == "close":
        close(args.year, args.period)
    elif args.cmd == "reopen":
        reopen(args.year, args.period)
    elif args.cmd == "forecast":
        forecast(args.months)
    elif args.cmd == "reconcile":
        reconcile(args.write)


if __name__ == "__main__":
    main()
