#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reconcile-check.py — PersonalCFO 报表自洽复核（P7.15）

校验内容：
  1. hledger check：账本结构/平衡（balances, accounts, ordereddates...）
  2. 月度借贷恒等：每月末 资产 + 负债 + 权益 + 收入 + 支出 = 0（delta 应为 0.00）
  3. 财年勾稽：hledger 的收入/支出合计 vs Paisa /api/income_statement（FY 4 月起）
  4. 期初分录：opening journal 自平衡，且 Equity:期初调整 = -(资产 + 负债)
  5. FIXME 规模（笔数/金额占比，仅本地输出）

用法：
  python scripts/reconcile-check.py --journal paisa_test/all.journal \
      --opening "journals/2026-09-10-opening.journal" --api http://localhost:7500

退出码：0 全部通过；1 有失败项。明细 JSON 写 .planning/reconcile-report.json。
注意：本脚本会在本地打印金额用于排查；写入 docs 的报告只应包含"delta/是否通过"等聚合结论。
"""
import argparse
import csv
import io
import json
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HLEDGER = ROOT / "tools" / "hledger-bin" / "hledger.exe"


def hledger(args):
    r = subprocess.run([str(HLEDGER), *args], capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace")


def balance_map(journal, begin=None, end=None):
    args = ["-f", str(journal), "balance", "-O", "csv", "--no-total"]
    if begin:
        args += ["--begin", begin]
    if end:
        args += ["--end", end]
    rc, out, err = hledger(args)
    if rc != 0:
        raise RuntimeError(f"hledger balance 失败：{err[:200]}")
    result = {}
    for row in csv.DictReader(io.StringIO(out)):
        bal = (row.get("balance") or "").replace(",", "").strip()
        amt = float(bal.split()[0]) if bal else 0.0
        result[row["account"]] = amt
    return result


def group_sums(bal):
    groups = {"Assets": 0.0, "Liabilities": 0.0, "Equity": 0.0, "Income": 0.0, "Expenses": 0.0}
    other = 0.0
    for account, amount in bal.items():
        top = account.split(":")[0]
        if top in groups:
            groups[top] += amount
        else:
            other += amount
    groups["Other"] = other
    return groups


def month_ends(first: date, last: date):
    y, m = first.year, first.month
    while True:
        if m == 12:
            nxt = date(y + 1, 1, 1)
        else:
            nxt = date(y, m + 1, 1)
        end = date.fromordinal(nxt.toordinal() - 1)
        if end >= first:
            yield end
        if (y, m) >= (last.year, last.month):
            break
        y, m = nxt.year, nxt.month


def first_txn_date(journal):
    rc, out, err = hledger(["-f", str(journal), "register", "--begin", "1971-01-01", "-O", "csv"])
    if rc != 0:
        raise RuntimeError(f"hledger register 失败：{err[:200]}")
    rows = list(csv.reader(io.StringIO(out)))
    for row in rows[1:]:
        if len(row) > 1 and row[1].strip():
            return date.fromisoformat(row[1].strip()[:10])
    return None


def fy_bounds(fy_start_month=4):
    today = date.today()
    start_year = today.year if today.month >= fy_start_month else today.year - 1
    fys = []
    for y in range(start_year - 1, start_year + 1):
        fys.append((f"{y} - {str(y+1)[2:]}", date(y, fy_start_month, 1), date(y + 1, fy_start_month, 1)))
    return fys


def fetch_json(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default="paisa_test/all.journal")
    ap.add_argument("--opening", default="journals/2026-09-10-opening.journal")
    ap.add_argument("--api", default="http://localhost:7500")
    ap.add_argument("--allow-no-api", action="store_true",
                    help="API 不可用时允许跳过财年/跨源核对（默认不允许，避免静默假绿）")
    ap.add_argument("--report", default=".planning/reconcile-report.json")
    args = ap.parse_args()

    journal = ROOT / args.journal
    opening = ROOT / args.opening
    failures, report = [], {"journal": str(journal)}

    # 1) hledger check：交易平衡 + 日期有序
    #（不查 accounts/payees/uniqueleafnames：本账本未写 account/payee 声明，
    #  且 Paisa 科目允许重名叶子，这三项会在严格模式下误报）
    rc, out, err = hledger(["-f", str(journal), "check", "balanced", "ordereddates"])
    report["hledger_check"] = {"ok": rc == 0, "output": (out + err).strip()[:400]}
    if rc != 0:
        failures.append(f"hledger check 失败：{err.strip()[:200]}")

    # 2) 月度借贷恒等
    first = first_txn_date(journal)
    today = date.today()
    deltas = []
    for end in month_ends(first, today):
        g = group_sums(balance_map(journal, end=end.isoformat()))
        delta = round(g["Assets"] + g["Liabilities"] + g["Equity"] + g["Income"] + g["Expenses"], 2)
        deltas.append({"end": end.isoformat(), "delta": delta})
    max_delta = max((abs(d["delta"]) for d in deltas), default=0.0)
    months_with_data = 0
    for end in month_ends(first, today):
        g = group_sums(balance_map(journal, end=end.isoformat()))
        if any(abs(v) > 0.005 for v in g.values()):
            months_with_data += 1
    report["identity"] = {"months": len(deltas), "max_abs_delta": max_delta,
                          "months_with_data": months_with_data,
                          "first": deltas[0] if deltas else None, "last": deltas[-1] if deltas else None}
    if max_delta > 0.005:
        failures.append(f"月度恒等式最大偏差 {max_delta}")
    # 覆盖度断言：样本太少/无数据时不允许"通过"（红队 S2-3）
    if len(deltas) < 6:
        failures.append(f"月度恒等样本过少（{len(deltas)} 个月末，应 ≥6）")
    if months_with_data < 3:
        failures.append(f"有数据的月末过少（{months_with_data}，应 ≥3；可能读错账本）")

    # 3) 财年勾稽（hledger vs Paisa API）
    api = None
    api_error = None
    try:
        api = fetch_json(args.api + "/api/income_statement")
    except Exception as e:  # noqa: BLE001
        api_error = str(e)
    if api_error:
        report["fy"] = {"skipped": f"API 不可用：{api_error}"}
        if not args.allow_no_api:
            failures.append(f"财年勾稽无法执行（API 不可用：{api_error[:80]}）；如确需跳过加 --allow-no-api")
    if api:
        yearly = api.get("yearly", {})
        checks = []
        for label, begin, end in fy_bounds():
            stmt = yearly.get(label)
            if not stmt:
                continue
            ledger = group_sums(balance_map(journal, begin=begin.isoformat(), end=end.isoformat()))
            ledger_income = round(-ledger["Income"], 2)
            ledger_expense = round(ledger["Expenses"], 2)
            # API 侧收入为负、支出为正（各自的方向），统一取绝对值比较
            api_income = round(abs(sum(stmt.get("income", {}).values())), 2)
            api_expense = round(abs(sum(stmt.get("expenses", {}).values())), 2)
            checks.append({"fy": label, "ledger_income": ledger_income, "api_income": api_income,
                           "ledger_expense": ledger_expense, "api_expense": api_expense,
                           "income_delta": round(ledger_income - api_income, 2),
                           "expense_delta": round(ledger_expense - api_expense, 2)})
        report["fy"] = checks
        for c in checks:
            if abs(c["income_delta"]) > 0.01 or abs(c["expense_delta"]) > 0.01:
                failures.append(f"财年 {c['fy']} 勾稽不一致：收入差 {c['income_delta']} / 支出差 {c['expense_delta']}")

    # 3.5) 跨源账户余额核对（Paisa API 的 DB 口径 vs hledger 直读；红队 S2-3）
    if api is not None:
        try:
            assets = fetch_json(args.api + "/api/assets/balance").get("asset_breakdowns", {}) or {}
            liabs = fetch_json(args.api + "/api/liabilities/balance").get("liability_breakdowns", []) or []
        except Exception as e:  # noqa: BLE001
            failures.append(f"跨源账户核对取数失败：{e}")
        else:
            led = balance_map(journal)
            checked, mismatches = 0, []
            all_names = set(assets.keys()) | {a for a, _ in
                (list(liabs.items()) if isinstance(liabs, dict) else [(i.get("group"), i) for i in liabs])}
            def is_leaf(acc):
                return not any(o != acc and o.startswith(acc + ":") for o in all_names)
            for acc, item in assets.items():
                # 只比现金/银行等无估值口径的科目（投资科目 hledger 是成本价，API 是市值）
                if not acc.startswith(("Assets:现金", "Assets:银行存款")) or not is_leaf(acc):
                    continue
                api_amt = abs(round(float(item.get("marketAmount", 0.0) or 0.0), 2))
                led_amt = abs(round(led.get(acc, 0.0), 2))
                checked += 1
                if abs(api_amt - led_amt) > 0.01:
                    mismatches.append(acc)
            liab_items = (
                list(liabs.items()) if isinstance(liabs, dict)
                else [(i.get("group"), i) for i in liabs]
            )
            for acc, item in liab_items:
                if not is_leaf(acc):
                    continue
                api_amt = abs(round(float(item.get("balance_amount", 0.0) or 0.0), 2))
                led_amt = abs(round(led.get(acc, 0.0), 2))
                checked += 1
                if abs(api_amt - led_amt) > 0.01:
                    mismatches.append(acc)
            report["cross_source"] = {"checked": checked, "mismatches": len(mismatches)}
            if checked < 3:
                failures.append(f"跨源账户核对样本过少（{checked}，应 ≥3）")
            if mismatches:
                failures.append(f"跨源账户余额不一致 {len(mismatches)} 个：{mismatches[:3]}")

    # 4) 期初分录
    if opening.exists():
        g = group_sums(balance_map(opening))
        total = round(sum(g.values()), 2)
        equity = round(g["Equity"], 2)
        expect = round(-(g["Assets"] + g["Liabilities"]), 2)
        report["opening"] = {"total": total, "equity": equity, "expected_equity": expect,
                             "assets": round(g["Assets"], 2), "liabilities": round(g["Liabilities"], 2)}
        if abs(total) > 0.005:
            failures.append(f"期初分录不平衡：合计 {total}")
        if abs(equity - expect) > 0.005:
            failures.append(f"期初权益不符：{equity} vs {expect}")
    else:
        report["opening"] = {"skipped": "opening journal 不存在"}

    # 5) FIXME 规模
    all_bal = balance_map(journal)
    fixme_accounts = {k: v for k, v in all_bal.items() if "FIXME" in k}
    fixme_total = round(sum(abs(v) for v in fixme_accounts.values()), 2)
    total_abs = round(sum(abs(v) for v in all_bal.values()), 2)
    report["fixme"] = {"accounts": len(fixme_accounts), "amount": fixme_total,
                       "share_of_abs_balance": round(fixme_total / total_abs * 100, 2) if total_abs else 0}

    ok = not failures
    report["failures"] = failures
    Path(ROOT / args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(ROOT / args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("══ 报表自洽复核 ══")
    print(f"  hledger check: {'✅' if report['hledger_check']['ok'] else '❌'}")
    print(f"  月度恒等:     {'✅' if max_delta <= 0.005 else '❌'}  {len(deltas)} 个月末（有数据 {months_with_data}），最大偏差 {max_delta}")
    if isinstance(report.get("fy"), list):
        for c in report["fy"]:
            okmark = "✅" if abs(c["income_delta"]) <= 0.01 and abs(c["expense_delta"]) <= 0.01 else "❌"
            print(f"  财年 {c['fy']}: {okmark} 收入差 {c['income_delta']} / 支出差 {c['expense_delta']}")
    else:
        print(f"  财年勾稽:     跳过（{report.get('fy', {}).get('skipped')}）")
    if "checked" in report.get("cross_source", {}):
        cs = report["cross_source"]
        print(f"  跨源账户:     {'✅' if cs['mismatches'] == 0 and cs['checked'] >= 3 else '❌'}"
              f"  核对 {cs['checked']} 个现金/银行/负债科目，不一致 {cs['mismatches']} 个")
    else:
        print("  跨源账户:     跳过")
    if "total" in report.get("opening", {}):
        o = report["opening"]
        print(f"  期初分录:     {'✅' if abs(o['total']) <= 0.005 and abs(o['equity'] - o['expected_equity']) <= 0.005 else '❌'}"
              f"  合计 {o['total']}，权益 {o['equity']}（应 {o['expected_equity']}）")
    print(f"  FIXME 规模:   {report['fixme']['accounts']} 科目 / {report['fixme']['amount']} 元"
          f"（占绝对余额 {report['fixme']['share_of_abs_balance']}%）")
    print(f"  结论:         {'✅ 全部通过' if ok else '❌ ' + '；'.join(failures)}")
    print(f"  报告:         {args.report}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
