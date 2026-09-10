#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""opening_entry.py — 期初建账分录生成器（P1.5 / P7.2）

两种用法：

1. 经典 YAML 模式（手工/脚本）：
   venv/Scripts/python src/opening_entry.py --date 2025-08-01
   读取 config/opening_balances.yaml，生成 journals/<date>-opening.journal。

2. 初始化向导 JSON 模式（Paisa /api/pcfo/init/opening 调用）：
   venv/Scripts/python src/opening_entry.py --json config/opening_init.json --force
   JSON 包含三类数据：
   - balances：货币类科目余额（Assets:现金/银行存款、Liabilities:…，字符串金额）
   - investments：逐项投资 {name, category, code, market_value, lots:[{date,qty,price}]}
       成本 = 建账日及之前每笔 qty×price 之和；填了 market_value 则期初资产按市值
       入账，市值与成本的差额自然进入 Equity:期初调整（历史盈亏不进当期收益）。
   - fixed_assets：逐项固定资产 {name, category, cost, purchase_date, years, salvage}
       自动追溯累计折旧（从购买月到建账日的完整月数，直线法，残值封底），
       期初表记“期初净值”；同时生成 journals/fixed-assets-recurring.journal，
       以后按月继续折剩余部分。
"""
import argparse
import json as _json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
JOURNALS_DIR = ROOT / "journals"
CONFIG_DIR = ROOT / "config"
OPENING_FILE = CONFIG_DIR / "opening_balances.yaml"
FIXED_RECURRING = JOURNALS_DIR / "fixed-assets-recurring.journal"

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


def _money(s, label="金额"):
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace(",", "")
    try:
        return __import__("finance").parse_money_strict(s)
    except ValueError:
        raise ValueError(f"{label}无法解析：{s!r}")


def _account_safe(s: str) -> str:
    """账户名/类别清洗：hledger 账户内不允许出现冒号作为层级分隔以外的内容。"""
    s = (s or "").strip().replace(":", "-").replace(";", "").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip(" -")
    return s[:40]


def _parse_day(s: str, label="日期") -> date:
    try:
        return date.fromisoformat((s or "").strip())
    except ValueError:
        raise ValueError(f"{label}非法：{s!r}")


def _month_diff(start: date, end: date) -> int:
    """start 到 end 的完整自然月数（折旧口径，向下取整）。"""
    return (end.year - start.year) * 12 + (end.month - start.month)


def _add_months(y: int, m: int, delta: int):
    total = y * 12 + (m - 1) + delta
    return total // 12, total % 12 + 1


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
        if not acct.startswith(("Assets:", "Liabilities:")):
            sys.exit(f"第 {ln} 行科目须以 Assets:/Liabilities: 开头：{acct!r}")
        try:
            v = __import__("finance").parse_money_strict(amt)
        except ValueError:
            sys.exit(f"第 {ln} 行金额无法解析：{amt!r}")
        if abs(v) > 0.004:
            balances[acct] = v
    return balances


def _posting_lines(postings):
    lines = []
    width = max(len(a) for a in postings)
    for acct in sorted(postings):
        v = postings[acct]
        sign = "- " if v < 0 else ""
        lines.append(f"    {acct:<{width}}    {sign}{abs(v):,.2f} CNY")
    return lines


def build_from_json(payload: dict):
    """返回 (postings, notes, fixed_rules)。postings: {acct: signed_amount}。"""
    opening_day = _parse_day(payload.get("date", "2025-08-01"))
    postings: dict[str, float] = {}
    notes: list[str] = []

    # 1) 货币类余额
    for acct, raw in (payload.get("balances") or {}).items():
        acct = acct.strip()
        if not acct.startswith(("Assets:", "Liabilities:")):
            raise ValueError(f"科目须以 Assets:/Liabilities: 开头：{acct!r}")
        v = _money(raw, f"余额 {acct}")
        if v is None or abs(v) < 0.004:
            continue
        # P7.6：不再自动把正数负债转负——信用卡可能有溢缴款（正数），
        # 欠款请填负数，由用户显式决定符号
        postings[acct] = round(v, 2)

    # 2) 投资逐项（每笔买入：日期+数量+单价；成本=Σ qty×price，只计建账日及之前）
    for inv in payload.get("investments") or []:
        name = _account_safe(inv.get("name", ""))
        category = _account_safe(inv.get("category", "其他"))
        if not name:
            raise ValueError("投资项缺少名称")
        acct = f"Assets:投资:{category}:{name}"
        cost, included, excluded = 0.0, 0, 0
        for lot in inv.get("lots") or []:
            d = _parse_day(lot.get("date", ""), f"投资[{name}]买入日期")
            qty = _money(lot.get("qty", ""), f"投资[{name}]数量")
            price = _money(lot.get("price", ""), f"投资[{name}]单价")
            if qty is None or price is None or qty < 0 or price < 0:
                raise ValueError(f"投资[{name}]买入记录非法：{lot!r}")
            if d <= opening_day:
                cost += qty * price
                included += 1
            else:
                excluded += 1
        cost = round(cost, 2)
        mv = _money(inv.get("market_value", ""), f"投资[{name}]当前市值")
        value = round(mv if mv is not None else cost, 2)
        if value == 0 and excluded == 0:
            continue  # 全空项跳过
        postings[acct] = value
        if excluded:
            notes.append(f"[{name}] 有 {excluded} 笔买入在建账日之后，未计入期初成本"
                         f"（建议后续在 Wealthfolio 录入）")
        if mv is not None and abs(mv - cost) >= 0.005:
            notes.append(f"[{name}] 买入成本 {cost:,.2f}，期初按市值 {mv:,.2f} 入账，"
                         f"差额 {mv - cost:,.2f} 进入期初调整（历史盈亏）")
        else:
            notes.append(f"[{name}] 期初成本 {cost:,.2f}")

    # 3) 固定资产逐项（自动追溯累计折旧；期初记净值；剩余折旧按月继续）
    fixed_rules: list[dict] = []
    for fa in payload.get("fixed_assets") or []:
        name = _account_safe(fa.get("name", ""))
        category = _account_safe(fa.get("category", "其他"))
        if not name:
            raise ValueError("固定资产项缺少名称")
        cost = _money(fa.get("cost", ""), f"固定资产[{name}]原价")
        years = float(fa.get("years") or "0")
        if cost is None or cost <= 0 or not (1 <= years <= 60):
            raise ValueError(f"固定资产[{name}]原价/年限非法")
        purchase = _parse_day(fa.get("purchase_date", ""), f"固定资产[{name}]购买日期")
        if purchase > opening_day:
            # P7.6：建账日之后购买的大件不属于期初资产负债表；
            # 请在购买发生后按日常分录/后续功能登记，不再混进期初
            notes.append(f"[{name}] 购买日期 {purchase.isoformat()} 晚于建账日 "
                         f"{opening_day.isoformat()}，未计入期初（请在购置后单独登记）")
            continue
        salvage = _money(fa.get("salvage", ""), f"固定资产[{name}]残值") or 0.0
        salvage = min(salvage, cost)
        total_months = int(years * 12)
        monthly = (cost - salvage) / total_months
        months_used = max(0, _month_diff(purchase, opening_day))
        months_used = min(months_used, total_months)
        acc_dep = round(monthly * months_used, 2)
        acc_dep = min(acc_dep, round(cost - salvage, 2))
        net = round(max(salvage, cost - acc_dep), 2)
        acct = f"Assets:固定资产:{category}:{name}"
        postings[acct] = net
        notes.append(f"[{name}] 原价 {cost:,.2f}，截至建账日已折旧 {acc_dep:,.2f}，"
                     f"期初净值 {net:,.2f}（剩余 {total_months - months_used} 个月按月折旧）")
        remaining = total_months - months_used
        if remaining > 0:
            base_y = opening_day.year if purchase <= opening_day else purchase.year
            base_m = opening_day.month if purchase <= opening_day else purchase.month
            first_y, first_m = _add_months(base_y, base_m, 1)  # 次月起折
            end_y, end_m = _add_months(first_y, first_m, remaining - 1)
            fixed_rules.append({
                "name": name,
                "start": f"{first_y}-{first_m:02d}",
                "end": f"{end_y}-{end_m:02d}",
                "monthly": round(monthly, 2),
            })

    if not postings:
        raise ValueError("没有任何非零期初数据（余额/投资/固定资产都为空）")

    return postings, notes, fixed_rules


def write_opening(opening_day: date, postings: dict, notes: list, force: bool):
    out = JOURNALS_DIR / f"{opening_day.isoformat()}-opening.journal"
    if out.exists() and not force:
        raise FileExistsError(f"{out.name} 已存在（防重复建账）。确认重建请加 --force")
    total = round(sum(postings.values()), 2)
    width = max([len(a) for a in postings] + [len("Equity:期初调整")])
    lines = [f"; 期初建账 {opening_day.isoformat()}（opening_entry 生成）",
             "; 差额自动进 Equity:期初调整 = 历史盈亏轧差（正常，非错误）"]
    lines += [f"; {n}" for n in notes]
    lines.append(f"{opening_day.strftime('%Y/%m/%d')} * 期初余额")
    lines += _posting_lines(postings)
    sign = "- " if -total < 0 else ""
    lines.append(f"    {'Equity:期初调整':<{width}}    {sign}{abs(total):,.2f} CNY")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已写入 {out.name}（{len(postings)} 个科目；Equity:期初调整 {-total:,.2f}）")
    return out


def write_fixed_rules(fixed_rules: list):
    lines = ["; 固定资产折旧规则（opening_entry 生成，仅本地，勿手改）",
             "; 修改请在初始化向导第②步重新生成期初。"]
    for r in fixed_rules:
        lines += ["",
                  f"; {r['name']}：每月 {r['monthly']:,.2f}，{r['start']} 起折",
                  f"~ monthly from {r['start']} to {r['end']}",
                  f"    Expenses:折旧    {r['monthly']:,.2f} CNY",
                  f"    Assets:累计折旧:{r['name']}    -{r['monthly']:,.2f} CNY"]
    FIXED_RECURRING.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已写入 {FIXED_RECURRING.name}（{len(fixed_rules)} 条折旧规则）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2025-08-01", help="建账日（默认 2025-08-01 账单起点）")
    ap.add_argument("--force", action="store_true", help="允许覆盖已有 opening journal")
    ap.add_argument("--json", help="JSON 初始化文件路径（向导模式）")
    args = ap.parse_args()

    if args.json:
        payload = _json.loads(Path(args.json).read_text(encoding="utf-8"))
        opening_day = _parse_day(payload.get("date", args.date))
        postings, notes, fixed_rules = build_from_json(payload)
        write_opening(opening_day, postings, notes, args.force)
        write_fixed_rules(fixed_rules)
        from finance import check, refresh_paisa_includes
        refresh_paisa_includes()
        check()
        return

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
    write_opening(day, balances, [], args.force)
    from finance import check, refresh_paisa_includes
    refresh_paisa_includes()
    check()


if __name__ == "__main__":
    main()
