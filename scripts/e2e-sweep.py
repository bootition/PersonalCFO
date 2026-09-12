#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""e2e-sweep.py — PersonalCFO 真实数据端到端走查（P7.8 机制）

用途：每次构建后，用真实账本数据把全部页面扫一遍，自动发现：
  1. 页面报错（console error / pageerror）
  2. 空白页（正文过短且没有可操作提示）
  3. 英文残留（界面文案级；账户名/对方/商品等用户数据自动放行）
  4. 图表 x 轴早于真实数据（1980/1990 这类默认范围回归）
  5. 首页出现交易明细（设计红线：首页只放数值与图表）
  6. 导航隐藏项泄漏 + 隐藏路由直达崩页
  7. 默认主题不是纸面浅色

前置：
  1. 启动服务：./vendor/paisa/paisa.exe serve --config paisa_test/paisa.yaml
  2. 运行：python scripts/e2e-sweep.py --base-url http://localhost:7500

依赖：playwright（系统 python 已有；Edge channel）。
退出码：0 = 全部通过；1 = 有失败项（详见输出与 --report JSON）。
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("需要 playwright：python -m pip install playwright && python -m playwright install msedge")

VISIBLE_ROUTES = [
    "/", "/init", "/cfo",
    "/cash_flow/income_statement", "/cash_flow/monthly", "/cash_flow/yearly", "/cash_flow/recurring",
    "/expense/monthly", "/expense/yearly",
    "/assets/balance", "/assets/networth", "/assets/investment", "/assets/gain",
    "/liabilities/balance", "/liabilities/repayment", "/liabilities/interest",
    "/income",
    "/ledger/editor", "/ledger/transaction", "/ledger/posting", "/ledger/price",
    "/more/config", "/more/doctor", "/more/logs", "/more/sheets",
]
# 已从导航隐藏但直达不能崩（应有中文说明页）
HIDDEN_ROUTES = [
    "/assets/allocation", "/assets/analysis", "/liabilities/credit_cards",
    "/more/goals", "/ledger/import", "/does-not-exist",
]
NAV_MUST_HIDE = ["分析", "配置", "信用卡", "目标", "导入"]
# 技术性页面：日志消息/结构化字段来自后端，不参与英文文案扫描
TECHNICAL_ROUTES = {"/more/logs"}
EN_ALLOW = {
    "XIRR", "FIRE", "PAISA", "PERSONALCFO", "CNY", "PDF", "CSV", "XLSX", "HTML", "JSON", "YAML", "SQL",
    "URL", "URI", "API", "ID", "IBAN", "ETF", "IPO", "APR", "AI", "GPU", "CPU",
    "RAM", "USB", "TAB", "N/A", "CN", "USD", "CTRL", "HLEDGER", "FINANCE", "REPORTS",
    "CHECK", "FIXME", "ALIPAY", "WECHAT", "SCHEDULE", "AL",
    # 科目路径前缀：属账本数据（Assets:现金:支付宝），不是界面文案
    "ASSETS", "LIABILITIES", "INCOME", "EXPENSES", "EQUITY",
    # 账本技术名词：文件名/查询语法关键字（journal 文件名、account= / payee= 查询 DSL）
    "JOURNAL", "JOURNALS", "INCLUDE", "IMPORT", "OPENING", "FIXED", "ACCOUNT", "PAYEE", "RECURRING",
}
# 合法空状态：短文本但包含以下词即视为"有说明"
EMPTY_OK = ("没有", "暂无", "尚未", "为空", "无负债", "不适用", "迁移", "初始化", "未配置", "无数据")


def text_of(page):
    try:
        return page.evaluate("document.querySelector('.container')?.innerText || document.body.innerText || ''")
    except Exception:
        return ""


def english_words(text, data_words=None):
    # 先剔除科目路径（Assets:... / Liabilities:...）与用户数据（对方/持仓名/时区枚举）
    cleaned = re.sub(r"\b(?:Assets|Liabilities|Income|Expenses|Equity):[^\s]+", " ", text)
    words = set(re.findall(r"[A-Za-z]{4,}", cleaned))
    data = {w.upper() for w in (data_words or set())}
    return sorted(
        w for w in words
        if w.upper() not in EN_ALLOW and w.upper() not in data and not re.fullmatch(r"[A-Z]{2,}", w)
    )


def is_blank(txt):
    s = txt.strip()
    if len(s) >= 40:
        return False
    if any(k in s for k in EMPTY_OK):
        return False
    if re.search(r"\d", s):  # 有数字（金额/笔数）就算有内容
        return False
    return True


def collect_data_words(page, base_url):
    """从 /api/dashboard（对方/科目）与 /api/config schema enum（时区城市等）收集用户数据词，
    避免把数据当界面英文残留。"""
    words = set()

    def add(s):
        if isinstance(s, str):
            words.update(re.findall(r"[A-Za-z]{4,}", s))

    def walk(o):
        if isinstance(o, str):
            add(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    try:
        # 编辑器接口返回的是账本数据（科目/对方/journal 文件名/版本等），整棵树都算数据词
        walk(page.request.get(base_url + "/api/editor/files").json())
    except Exception:
        pass

    try:
        # /api/transaction 返回全量交易（dashboard 只有近期），能覆盖所有对方/科目名
        trx = page.request.get(base_url + "/api/transaction").json()
        for t in (trx.get("transactions") or []):
            add(t.get("payee"))
            for p in t.get("postings", []) or []:
                add(p.get("account"))
                add(p.get("payee"))
                add(p.get("note"))
    except Exception:
        pass
    try:
        dash = page.request.get(base_url + "/api/dashboard").json()
        for t in dash.get("transactions", []) or []:
            add(t.get("payee"))
            for p in t.get("postings", []) or []:
                add(p.get("account"))
                add(p.get("payee"))
                add(p.get("note"))
    except Exception:
        pass

    def walk_enums(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "enum" and isinstance(v, list):
                    for x in v:
                        add(x)
                else:
                    walk_enums(v)
        elif isinstance(o, list):
            for v in o:
                walk_enums(v)

    try:
        cfg = page.request.get(base_url + "/api/config").json()
        walk_enums(cfg.get("schema"))
    except Exception:
        pass
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:7500")
    ap.add_argument("--report", default=".planning/e2e-sweep-report.json")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    failures, results = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=not args.headed)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)[:200]))
        page.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)

        data_words = collect_data_words(page, args.base_url)

        def visit(route, check_blank=True):
            errs.clear()
            page.goto(args.base_url + route, wait_until="networkidle", timeout=30000)
            time.sleep(1.0)
            txt = text_of(page)
            item = {"route": route, "errors": list(errs), "text_len": len(txt.strip())}
            if errs:
                failures.append(f"{route}: 页面报错 {errs[:1]}")
            if check_blank and is_blank(txt):
                failures.append(f"{route}: 空白页（正文 {len(txt.strip())} 字）")
            return txt, item

        # 1) 可见页面
        for r in VISIBLE_ROUTES:
            txt, item = visit(r)
            words = [] if r in TECHNICAL_ROUTES else english_words(txt, data_words)
            item["english"] = words
            item["technical_page"] = r in TECHNICAL_ROUTES
            if words:
                failures.append(f"{r}: 英文残留 {words[:6]}")
            years = sorted(set(re.findall(r"19\d\d", page.evaluate(
                "Array.from(document.querySelectorAll('svg text')).map(e=>e.textContent).join(' ')"))))
            item["early_years"] = years
            if years:
                failures.append(f"{r}: 图表出现 19xx 年份 {years[:3]}")
            results.append(item)

        # 2) 首页专项：无交易明细、4 张摘要卡
        page.goto(args.base_url + "/", wait_until="networkidle")
        time.sleep(2.0)
        stats = page.locator(".pcfo-stat").count()
        tx_rows = page.locator(".transaction").count()
        if stats < 4:
            failures.append(f"/: 摘要卡只有 {stats} 张（应 ≥4）")
        if tx_rows > 0:
            failures.append(f"/: 首页出现交易明细 {tx_rows} 行（设计红线：不应有）")
        if not page.locator("#d3-home-networth path").count():
            failures.append("/: 首页净值走势图未渲染")
        results.append({"route": "/", "stat_cards": stats, "tx_rows": tx_rows})

        # 3) 主题默认浅色
        page.goto(args.base_url + "/init", wait_until="networkidle")
        time.sleep(0.8)
        theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        results.append({"route": "/init", "theme": theme, "body_bg": bg})
        if theme != "light":
            failures.append(f"默认主题不是 light（实际 {theme}）")

        # 4) 导航隐藏项
        nav = page.locator(".pcfo-nav").inner_text()
        leaked = [x for x in NAV_MUST_HIDE if x in nav]
        if leaked:
            failures.append(f"导航泄漏隐藏项 {leaked}")

        # 5) 隐藏路由直达不崩、且是中文说明
        for r in HIDDEN_ROUTES:
            txt, item = visit(r, check_blank=False)
            item["hidden_ok"] = True
            if errs:
                failures.append(f"隐藏路由 {r}: 直达崩页 {errs[:1]}")
            if r != "/does-not-exist" and is_blank(txt):
                failures.append(f"隐藏路由 {r}: 说明页为空")
            results.append(item)

        browser.close()

    report = {"base_url": args.base_url, "failures": failures, "results": results}
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== e2e-sweep: {len(VISIBLE_ROUTES) + len(HIDDEN_ROUTES)} 路由, 失败 {len(failures)} 项 ===")
    for f in failures:
        print("  ❌", f)
    if not failures:
        print("  ✅ 全部通过")
    print(f"报告：{args.report}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
