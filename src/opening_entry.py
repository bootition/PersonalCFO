#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""opening_entry.py — 期初建账分录生成器（P1.5）

用户只需做一件事：把各账户真实余额填进 config/opening_balances.yaml（仅本地，不入库；
文件缺失时本脚本自动生成带注释的模板）。然后运行：

    venv/Scripts/python src/opening_entry.py --date 2025-08-01

生成 journals/<date>-opening.journal：每个非零科目一条 posting，差额进 Equity:期初调整，
随后自动 hledger check。同日防覆盖。
"""
import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNALS_DIR = ROOT / "journals"
CONFIG_DIR = ROOT / "config"
OPENING_FILE = CONFIG_DIR / "opening_balances.yaml"

TEMPLATE = """# 期初建账盘点表（仅本地，永不入库）
# 用法：把建账日（建议 2025-08-01，与账单起点对齐）各账户真实余额填在冒号后。
#   资产填正数；负债填负数（如 Liabilities:花呗: -3000.00）；没有的账户留空或删行。
# 填完运行： venv/Scripts/python src/opening_entry.py --date 2025-08-01
# 差额自动进 Equity:期初调整（建账差额=历史盈亏的轧差，正常）。
#
# ── 现金及等价物 ──
Assets:现金:支付宝:
Assets:现金:余额宝:
Assets:现金:微信:
Assets:现金:零钱通:
Assets:现金:现金:
# ── 银行存款 ──
Assets:银行存款:建设银行:
Assets:银行存款:工商银行:
Assets:银行存款:招商银行:
Assets:银行存款:光大银行:
# ── 应收/预付 ──
Assets:应收账款:工资:
Assets:预付账款:房租:
# ── 投资（成本口径） ──
Assets:投资:基金:
Assets:投资:股票:
Assets:投资:虚拟货币:
Assets:投资:CS饰品:
# ── 固定资产（历史原价） ──
Assets:固定资产:电子设备:
Assets:固定资产:家居家电:
Assets:固定资产:交通工具:
Assets:固定资产:房产:
# ── 借出款项 ──
Assets:借出款项:
# ── 负债（负数） ──
Liabilities:花呗:
Liabilities:信用卡:建设银行:
Liabilities:借款:
"""


def read_balances(path: Path):
    balances = {}
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        acct, _, amt = s.rpartition(":")
        acct, amt = acct.strip(), amt.strip().replace(",", "")
        if not amt:
            continue
        if not (acct.startswith(("Assets:", "Liabilities:"))):
            sys.exit(f"第 {ln} 行科目须以 Assets:/Liabilities: 开头：{acct!r}")
        try:
            v = float(amt)
        except ValueError:
            sys.exit(f"第 {ln} 行金额无法解析：{amt!r}")
        if abs(v) > 0.004:
            balances[acct] = v
    return balances


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2025-08-01", help="建账日（默认 2025-08-01 账单起点）")
    ap.add_argument("--force", action="store_true", help="允许覆盖已有 opening journal")
    args = ap.parse_args()
    day = date.fromisoformat(args.date)

    if not OPENING_FILE.exists():
        OPENING_FILE.write_text(TEMPLATE, encoding="utf-8")
        print(f"已生成盘点模板 {OPENING_FILE}（仅本地，不入库）")
        print("请按建账日真实余额填写后重跑本命令。科目可按需增删（须 Assets:/Liabilities: 开头）")
        return

    balances = read_balances(OPENING_FILE)
    if not balances:
        sys.exit(f"{OPENING_FILE} 没有有效余额行（全空/全注释）。请先填写真实余额。")

    total = sum(balances.values())
    out = JOURNALS_DIR / f"{day.isoformat()}-opening.journal"
    if out.exists() and not args.force:
        sys.exit(f"{out.name} 已存在（防重复建账）。确认要重建请加 --force")

    lines = [f"; 期初建账 {day.isoformat()}（opening_entry 生成，来源 config/opening_balances.yaml）",
             f"{day.strftime('%Y/%m/%d')} * 期初余额"]
    width = max(len(a) for a in balances)
    for acct in sorted(balances):
        v = balances[acct]
        sign = "- " if v < 0 else ""
        lines.append(f"    {acct:<{width}}    {sign}{abs(v):,.2f} CNY")
    # 差额 → Equity:期初调整（=-total，使分录配平）
    sign = "- " if -total < 0 else ""
    lines.append(f"    {'Equity:期初调整':<{width}}    {sign}{abs(total):,.2f} CNY")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"已写入 {out.name}（{len(balances)} 个科目；Equity:期初调整 差额 {-total:,.2f}）")
    # 平衡校验（借用 finance.py 的 hledger 封装）
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from finance import check  # noqa: E402
    check()


if __name__ == "__main__":
    main()
