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
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

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


def import_bills():
    """把 raw/ 下的支付宝 CSV / 微信 XLSX 翻译成 journals/import-*.journal。"""
    jobs = [
        ("alipay", "支付宝交易明细*.csv", "config/alipay.yaml"),
        ("wechat", "微信支付账单流水文件*.xlsx", "config/wechat.yaml"),
    ]
    for platform, pattern, cfg in jobs:
        bills = sorted(RAW_DIR.glob(pattern))
        if not bills:
            print(f"[跳过] raw/ 下没有 {platform} 账单（{pattern}）")
            continue
        for bill in bills:
            out_file = JOURNALS_DIR / f"import-{platform}-{bill.stem}.journal"
            subprocess.run(["chcp.com", "65001"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
            res = subprocess.run(
                [str(DEG), "translate", "-p", platform, "-t", "ledger",
                 "--config", str(ROOT / cfg), str(bill), "-o", str(out_file)],
                capture_output=True)
            if res.returncode != 0:
                sys.exit(f"deg 导入失败：{res.stderr.decode('utf-8', errors='replace')[:400]}")
            print(f"已导入 {bill.name} -> {out_file.name}")
    print("导入完成；请检查 journals/import-*.journal 中 Assets:FIXME/Expenses:FIXME 并补全规则")


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


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("import")
    p = sub.add_parser("report"); p.add_argument("year", type=int)
    p = sub.add_parser("close"); p.add_argument("year", type=int); p.add_argument("period")
    p = sub.add_parser("reopen"); p.add_argument("year", type=int); p.add_argument("period")
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


if __name__ == "__main__":
    main()
