#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_fair_value.py — Wealthfolio 持仓公允价值季度回写（契约 C4）

读 Wealthfolio 导出的 holdings CSV（字段名做兼容断言，不符即报错而非猜），
对比 journal 中投资科目账面成本，生成季度公允价值调整分录：

    市值 > 账面:  借 Assets:投资:X  delta  /  贷 Income:投资损益:公允价值  delta
    市值 < 账面:  借 Income:投资损益:公允价值 |delta|  /  贷 Assets:投资:X  |delta|

用法：
    venv/Scripts/python src/sync_fair_value.py holdings.csv [--date 2026-09-30] [--write]
默认只打印分录草稿；--write 追加到 journals/fair-value-<date>.journal。

科目映射（Wealthfolio 账户名 → journal 投资科目）见 CONFIG 节，按 P2.1 建户后核对。
"""
import argparse
import csv
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNALS_DIR = ROOT / "journals"
HL = ROOT / "tools" / "hledger-bin" / "hledger.exe"

# ── 契约 C4：holdings CSV 必填字段（Wealthfolio 导出；缺失即报错）──
REQUIRED_FIELDS = ["account_name", "symbol_name", "market_value", "cost_basis"]

# Wealthfolio 账户名 → journal 投资科目（P2.1 建户后核对/扩充）
ACCOUNT_MAP = {
    "哈利布朗": "Assets:投资:基金",
    "攒股收息": "Assets:投资:股票",
    "虚拟货币": "Assets:投资:虚拟货币",
    "CS饰品": "Assets:投资:CS饰品",
}

INVEST_ROOT = "Assets:投资"
FV_ACCOUNT = "Income:投资损益:公允价值"


def read_holdings(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_FIELDS if c not in (reader.fieldnames or [])]
        if missing:
            sys.exit(f"holdings CSV 字段不符契约 C4，缺少: {missing}；实际字段: {reader.fieldnames}"
                     "（断言失败即停止，不猜字段名）")
        rows = list(reader)
    out = {}
    for r in rows:
        acct = r["account_name"].strip()
        target = ACCOUNT_MAP.get(acct)
        if target is None:
            print(f"[警告] 未映射的 Wealthfolio 账户 {acct!r}，已跳过（请在 ACCOUNT_MAP 配置）")
            continue
        mv = float(r["market_value"].replace(",", "") or 0)
        out[target] = out.get(target, 0.0) + mv
    return out


def journal_invest_balances():
    """hledger 输出投资科目各叶子账面余额（成本口径）。"""
    subprocess.run(["chcp.com", "65001"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=False)
    files = sorted(JOURNALS_DIR.glob("*.journal"))
    args = [str(HL)]
    for f in files:
        args += ["-f", str(f)]
    args += ["balance", INVEST_ROOT, "--flat", "-O", "csv"]
    res = subprocess.run(args, capture_output=True)
    if res.returncode != 0:
        sys.exit(f"hledger 失败: {res.stderr.decode('utf-8', errors='replace')[:300]}")
    out = {}
    for row in csv.reader(res.stdout.decode("utf-8", errors="replace").splitlines()):
        if len(row) == 2 and row[0].startswith(INVEST_ROOT + ":"):
            amt = row[1].replace("CNY", "").replace(",", "").strip()
            out[row[0]] = float(amt or 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("holdings", type=Path)
    ap.add_argument("--date", default=date.today().isoformat(), help="调整分录日期（季度末）")
    ap.add_argument("--write", action="store_true", help="写入 journals/fair-value-<date>.journal")
    args = ap.parse_args()

    holdings = read_holdings(args.holdings)
    book = journal_invest_balances()

    lines = [f"; 公允价值调整 {args.date}（sync_fair_value 生成，来源 {args.holdings.name}）"]
    total_delta = 0.0
    print(f"{'科目':<28}{'账面成本':>14}{'Wealthfolio市值':>18}{'差额':>14}")
    for acct in sorted(set(book) | set(holdings)):
        b, m = book.get(acct, 0.0), holdings.get(acct, 0.0)
        delta = round(m - b, 2)
        total_delta += delta
        print(f"{acct:<28}{b:>14,.2f}{m:>18,.2f}{delta:>+14,.2f}")
        if abs(delta) < 0.005:
            continue
        if delta > 0:
            lines.append(f"\n{args.date} * 公允价值调整（{acct}，市值高于账面）")
            lines.append(f"    {acct}    {delta:.2f} CNY")
            lines.append(f"    {FV_ACCOUNT}    -{delta:.2f} CNY")
        else:
            lines.append(f"\n{args.date} * 公允价值调整（{acct}，市值低于账面）")
            lines.append(f"    {FV_ACCOUNT}    {abs(delta):.2f} CNY")
            lines.append(f"    {acct}    {delta:.2f} CNY")
    print(f"{'合计':<28}{sum(book.values()):>14,.2f}{sum(holdings.values()):>18,.2f}{total_delta:>+14,.2f}")

    if args.write:
        if abs(total_delta) < 0.005:
            print("账面与市值一致，无需调整")
            return
        out = JOURNALS_DIR / f"fair-value-{args.date}.journal"
        if out.exists():
            sys.exit(f"{out.name} 已存在，拒绝覆盖（防重复回写；请先核对删除旧文件）")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"已写入 {out.name}；请运行 python src/finance.py check 验证平衡")
    else:
        print("\n── 分录草稿（--write 才写入）──")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
