#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""split_huabei.py — 花呗组合支付拆分（契约见 docs/contracts/01_文件契约.md C1/C3）

输入：
  1. 花呗账单证明 PDF（pypdf + 密码；密码读 config/local.yaml 的 huabei_pdf_password，不入库）
  2. deg 生成的 import-alipay journal（组合支付整笔先记 Liabilities:花呗）

输出（原地改写 journal，原文件备份到 journals/bak/）：
  - 组合支付分录改写：贷 花呗=PDF承担额，贷 组合另一方=差额
    （余额宝/储蓄卡→对应资产科目；红包/立减券/特惠/花呗金→Income:其他收入）
  - PDF 自动还款无对应 journal 分录 → 补录 借:花呗/贷:Assets:FIXME
  - PDF 退款还款可定位原消费 → 生成冲销 借:花呗/贷:<原消费科目>；无法定位 → FIXME 清单
  - 拆分报告 reports/huabei-split-<日期>.txt（仅本地；含商户名，不入库）

匹配两级：美团 26 位单号/XP 单号精确 > 日期+名称模糊（纯花呗带金额、组合支付不带金额）。
验收口径：PDF 消费行在支付宝账单覆盖期内（≤账单截止日）的匹配率 ≥95%，拆后 hledger check 平衡。

用法：
  venv/Scripts/python src/split_huabei.py <journal文件> [--pdf raw/xxx.pdf] [--coverage-end 2026-07-31]
"""
import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CFG = ROOT / "config" / "local.yaml"
BAK_DIR = ROOT / "journals" / "bak"
REPORTS_DIR = ROOT / "reports"

# ═══════════════ PDF 解析 ═══════════════

@dataclass
class PdfRow:
    month: str          # 账单段 "2026-07"
    day: date           # 交易日期
    name: str           # 名称（换行已拼接）
    amount: float       # 消费为正，还款/退款为负
    fee: float
    time: str = ""

_SECTION = re.compile(r"^(\d{4})年(\d{2})月_花呗账单\s*$")
_DATE_LINE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})\s*$")
_TIME = re.compile(r"(\d{2}:\d{2}:\d{2})")
_AMT_FEE = re.compile(r"^(.*?)\s+(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*$")


def read_pdf_password(cfg=LOCAL_CFG):
    if not cfg.exists():
        sys.exit(f"缺少 {cfg}（格式：huabei_pdf_password: \"...\"，文件被 .gitignore 排除）")
    m = re.search(r'huabei_pdf_password:\s*["\']?([^"\'\s]+)', cfg.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"{cfg} 中找不到 huabei_pdf_password")
    return m.group(1)


def parse_pdf(pdf_path: Path, password: str):
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        reader.decrypt(password)
    rows, section = [], None
    cur = None  # 当前累积的行块

    def flush():
        nonlocal cur
        if cur is None:
            return
        # 块内最后一行含 amount fee；名称=金额行前文+此前名称行
        text_lines = [l for l in cur if l.strip()]
        amt_idx = None
        for i in range(len(text_lines) - 1, -1, -1):
            if _AMT_FEE.match(text_lines[i]):
                amt_idx = i
                break
        if amt_idx is not None and section:
            m = _AMT_FEE.match(text_lines[amt_idx])
            tail, amount, fee = m.group(1).strip(), float(m.group(2)), float(m.group(3))
            tail = _TIME.sub("", tail).strip()  # 去掉金额行开头的时间 token
            name_parts = [l.strip() for l in text_lines[:amt_idx]
                          if not _DATE_LINE.match(l) and not _TIME.fullmatch(l.strip())]
            if tail:
                name_parts.append(tail)
            name = "".join(name_parts)
            name = re.sub(r"\s+", "", name)
            t = ""
            for l in text_lines:
                tm = _TIME.search(l)
                if tm:
                    t = tm.group(1)
                    break
            rows.append(PdfRow(section, cur_date, name, amount, fee, t))
        cur = None

    cur_date = None
    for page in reader.pages:
        for raw in page.extract_text().splitlines():
            line = raw.strip()
            sm = _SECTION.match(line)
            if sm:
                flush()
                section = f"{sm.group(1)}-{sm.group(2)}"
                continue
            if line.startswith("时间") or not line:
                continue
            dm = _DATE_LINE.match(line)
            if dm:
                flush()
                cur_date = date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
                cur = []
                continue
            if cur is not None:
                cur.append(line)
            else:
                # 日期前的游离行（跨页换行）并入上一行块
                if rows and line and not line.startswith("═══"):
                    # 跨页续行：拼到上一条名称（罕见，仅名称换页）
                    rows[-1].name += re.sub(r"\s+", "", line)
    flush()
    return rows


# ═══════════════ journal 解析（保留原文块） ═══════════════

@dataclass
class Tx:
    head: str
    lines: list           # head 之后的原始行（注释+分录）
    day: date = None
    meta: dict = field(default_factory=dict)
    postings: list = field(default_factory=list)  # [行号, account, amount]
    matched: bool = False

_TX_HEAD = re.compile(r"^(\d{4})[/\-](\d{2})[/\-](\d{2}) ")
_META = re.compile(r'^\s*; (\w+): "?(.*?)"?$')
_POSTING = re.compile(r"^(\s+)(\S[^;]*?)(\s+)(-?\s?[\d,]+(?:\.\d+)?)\s*(CNY.*)$")


def parse_journal_raw(path: Path):
    """返回 (prelude, [Tx])；Tx.lines 为原始行，可改写后拼回。"""
    prelude, txs, cur = [], [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _TX_HEAD.match(line)
        if m:
            cur = Tx(head=line, lines=[], day=date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            txs.append(cur)
            continue
        if cur is None:
            prelude.append(line)
        else:
            cur.lines.append(line)
    for tx in txs:
        for i, l in enumerate(tx.lines):
            mm = _META.match(l)
            if mm:
                tx.meta[mm.group(1)] = mm.group(2)
                continue
            pm = _POSTING.match(l)
            if pm:
                amt = float(pm.group(4).replace(",", "").replace(" ", ""))
                tx.postings.append((i, pm.group(2).strip(), amt))
    return prelude, txs


def fmt_amount(x: float) -> str:
    return f"{x:.2f}"


def render_posting(account: str, amount: float) -> str:
    sign = "- " if amount < 0 else ""
    return f"    {account}    {sign}{abs(amount):.2f} CNY"


# ═══════════════ 匹配 ═══════════════

def norm_name(s: str) -> str:
    s = re.sub(r"[\s*＊]+", "", s or "")
    return s.lower()


def name_tokens(s: str):
    """切词：先按脱敏符 */＊ 断开（脱敏遮挡的字不参与匹配），再按非文字字符细分，
    取 ≥2 字符的 token（单字如 *鸿 的"鸿"不单独成词）。"""
    raw = re.sub(r"\s+", "", (s or "").lower())
    frags = re.split(r"[*＊]+", raw)
    toks = []
    for f in frags:
        toks.extend(re.split(r"[^\w一-鿿]+", f))
    return [t for t in toks if len(t) >= 2]


def name_fuzzy(pdf_name: str, tx) -> bool:
    """PDF 名称与 journal 首行（对方 - 商品）匹配：整体包含，或全部 ≥2 字 token 都出现。"""
    pn = norm_name(pdf_name)
    head = norm_name(tx.head)
    if pn and pn in head:
        return True
    toks = name_tokens(pdf_name)
    return bool(toks) and all(t in head for t in toks)


ORDER26 = re.compile(r"(26\d{24})")
XP_ORDER = re.compile(r"(XP\d{6,})")
INSTALL = re.compile(r"^(.*?)(\d+)/(\d+)$")


def aggregate_installments(rows):
    """花呗分期：PDF 把一笔分期拆成 n 行（"名称1/3".."n/3"），合并回一条（金额求和）再匹配。"""
    groups, out = {}, []
    for r in rows:
        m = INSTALL.match(r.name)
        if m and r.amount > 0:
            groups.setdefault(norm_name(m.group(1)), []).append((m, r))  # 分期行跨月账单段，按名称归组
        else:
            out.append(r)
    for _base, items in groups.items():
        if len(items) >= 2:
            first = min(items, key=lambda x: x[1].day)[1]
            out.append(PdfRow(first.month, first.day, items[0][0].group(1),
                              round(sum(r.amount for _, r in items), 2),
                              round(sum(r.fee for _, r in items), 2), first.time))
        else:
            out.extend(r for _, r in items)
    return out


def method_co_account(method: str):
    """组合支付方式去掉花呗部分后，另一方应落科目。返回 (account, part_desc) 或 None。"""
    method = (method or "").replace("&amp;", "&")
    parts = [p for p in method.split("&") if p]
    rest = []
    for p in parts:
        if p == "花呗" or p.startswith("花呗分期"):
            continue  # 花呗侧
        rest.append(p)
    if not rest:
        return None
    acct = None
    for p in rest:
        if "余额宝" in p:
            acct = acct or "Assets:现金:余额宝"
        elif "储蓄卡" in p:
            bank = re.sub(r"^中国?", "", p)
            bank = bank.split("储蓄卡")[0]
            acct = acct or f"Assets:银行存款:{bank}"
        elif p in ("余额", "账户余额"):
            acct = acct or "Assets:现金:支付宝"
        # 红包/立减券/特惠/花呗金等 = 平台补贴 → 其他收入（不占用 acct 主位时并入）
    if acct:
        return acct, "&".join(rest)
    return "Income:其他收入", "&".join(rest)


@dataclass
class SplitResult:
    splits: list = field(default_factory=list)      # (tx, pdf_row, co_account, co_amount)
    verified_pure: int = 0
    pure_amount_mismatch: list = field(default_factory=list)
    unmatched_pdf: list = field(default_factory=list)      # 覆盖期内 PDF 有、journal 无
    out_of_period_pdf: list = field(default_factory=list)  # 期外
    unmatched_tx: list = field(default_factory=list)       # journal 有、PDF 无
    repay_verify: int = 0
    repay_create: list = field(default_factory=list)       # PDF 自动还款无对应 → 补录
    refund_reverse: list = field(default_factory=list)     # (pdf_row, 原消费tx) → 冲销
    refund_fixme: list = field(default_factory=list)
    refund_paired: int = 0  # PDF 消费+退款两侧留痕但 journal 已被 deg 双剔（自解释，非 FIXME）
    refund_already_booked: int = 0  # PDF 退款还款，但 journal 已有同额退款分录（无需动作）
    subaccount_expected: int = 0    # journal 侧亲情卡/代付：主花呗账单不含子账，属正常
    out_of_period_negative: int = 0 # PDF 负数行晚于覆盖期（如下月还款），不在本期处理


def match_all(pdf_rows, txs, coverage_end: date):
    res = SplitResult()
    hb_txs = [t for t in txs if "花呗" in t.meta.get("method", "")]
    consumption = [r for r in pdf_rows if r.amount > 0]
    negatives = [r for r in pdf_rows if r.amount < 0]

    # 索引：单号 → tx
    by_mid = {}
    for t in hb_txs:
        mid = t.meta.get("merchantId", "")
        if mid:
            by_mid.setdefault(mid, []).append(t)

    def tx_amount(t):
        return max((abs(a) for _, _, a in t.postings), default=0)

    def candidates(r: PdfRow, with_amount: bool, days: int = 0):
        """日期窗内按名称模糊匹配；days=0 表示仅当日。返回 [(Δdays, Δamount, tx)] 升序。"""
        out = []
        for t in hb_txs:
            if t.matched:
                continue
            dd = abs((t.day - r.day).days)
            if dd > days or (days == 0 and dd != 0):
                continue
            tamt = tx_amount(t)
            if with_amount and abs(tamt - r.amount) > 0.005:
                continue
            if name_fuzzy(r.name, t):
                out.append((dd, abs(tamt - r.amount), t))
        out.sort(key=lambda x: (x[0], x[1]))
        return out

    def uniq(cands):
        """候选唯一才命中；头部并列（Δdays、Δamount 均同）视为歧义放弃。"""
        if not cands:
            return None
        if len(cands) >= 2 and cands[0][:2] == cands[1][:2]:
            return None
        return cands[0][2]

    for r in consumption:
        # 期外行（账单截止日之后）不配：等下期账单导入后自然匹配，防止窗口级误配
        if r.day > coverage_end:
            res.out_of_period_pdf.append(r)
            continue
        hit = None
        # L1 单号精确
        for pat in (ORDER26, XP_ORDER):
            m = pat.search(r.name)
            if m:
                cands = [t for t in by_mid.get(m.group(1), []) if not t.matched]
                if len(cands) == 1:
                    hit = cands[0]
                elif len(cands) > 1:
                    hit = next((t for t in cands if t.day == r.day), cands[0])
                if hit:
                    break
        # L2 当日+金额+名称（纯花呗）
        if hit is None:
            cands = candidates(r, with_amount=True)
            if len(cands) == 1:
                hit = cands[0][2]
        # L3 当日+名称（组合支付，PDF 金额=花呗承担额≠总额）
        if hit is None:
            cands = [c for c in candidates(r, with_amount=False)
                     if tx_amount(c[2]) >= r.amount - 0.005]
            if len(cands) == 1:
                hit = cands[0][2]
            elif cands:
                hit = sorted(cands, key=lambda c: c[1])[0][2]
        # L4 窗口匹配：PDF 入账日可能晚于支付日（确认收货才出账），±15 天
        if hit is None:
            hit = uniq(candidates(r, with_amount=True, days=15))       # 纯花呗：金额须等
        if hit is None:
            cands = [c for c in candidates(r, with_amount=False, days=15)
                     if tx_amount(c[2]) >= r.amount - 0.005]
            hit = uniq(cands)                                          # 组合：名称+总额≥
        # L5 代付/亲情卡：账单只写"代付"，PDF 写真实商户——只能按金额+窗口配
        if hit is None:
            daifu = [(abs((t.day - r.day).days), 0, t) for t in hb_txs
                     if not t.matched and ("代付" in t.head or "亲情卡" in t.head)
                     and abs(tx_amount(t) - r.amount) < 0.005
                     and abs((t.day - r.day).days) <= 10]
            daifu.sort(key=lambda x: x[0])
            hit = uniq(daifu)
        if hit is None:
            res.unmatched_pdf.append(r)
            continue
        hit.matched = True
        full = max((abs(a) for _, _, a in hit.postings), default=0)
        is_combo = "&" in hit.meta.get("method", "").replace("&amp;", "&")
        if is_combo:
            co = method_co_account(hit.meta.get("method", ""))
            remainder = round(full - r.amount, 2)
            if co is None or remainder < -0.005:
                res.pure_amount_mismatch.append((hit, r, "组合支付拆分异常"))
            else:
                res.splits.append((hit, r, co[0], remainder))
        else:
            if abs(full - r.amount) > 0.005:
                res.pure_amount_mismatch.append((hit, r, f"纯花呗金额不符 journal={full} pdf={r.amount}"))
            else:
                res.verified_pure += 1

    res.unmatched_tx = [t for t in hb_txs if not t.matched]

    # 还款类交易（借花呗）在负数行循环单独核对，不应出现在"账单无对"消费清单里
    res.unmatched_tx = [
        t for t in res.unmatched_tx
        if not ("还款" in t.head
                and any(acc == "Liabilities:花呗" and a > 0 for _, acc, a in t.postings))
    ]

    # 亲情卡/代付：花呗主账单不列子账消费，journal 有、PDF 无属正常，不计 FIXME
    subaccount = [t for t in res.unmatched_tx if "亲情卡" in t.head or "代付" in t.head]
    if subaccount:
        res.unmatched_tx = [t for t in res.unmatched_tx if t not in subaccount]
        res.subaccount_expected = len(subaccount)

    # ── 负数行：自动还款 / 退款还款 ──
    # 匹配池限定"还款"类借方花呗分录（防同额退款幻影核对）；容差 ±0.1（花呗金尾差）+ 同日±1
    repay_txs = [t for t in txs
                 if "还款" in t.head
                 and any(acc == "Liabilities:花呗" and a > 0 for _, acc, a in t.postings)]
    for r in negatives:
        if r.day > coverage_end:
            # 如下月账单的自动还款：不属于本期，天然无 journal 对应
            res.out_of_period_negative += 1
            continue
        if "自动还款" in r.name or "主动还款" in r.name:
            hit = next((t for t in repay_txs
                        if abs((t.day - r.day).days) <= 1
                        and any(abs(a - abs(r.amount)) < 0.1 for _, acc, a in t.postings
                                if acc == "Liabilities:花呗")), None)
            if hit:
                res.repay_verify += 1
            else:
                res.repay_create.append(r)
        elif "退款还款" in r.name:
            # 先判：journal 已有一笔同额"退款"分录（deg 已把退款入账）→ 无需动作
            booked = any(
                "退款" in t.head
                and abs((t.day - r.day).days) <= 7
                and any(acc == "Liabilities:花呗" and abs(a - abs(r.amount)) < 0.005
                        for _, acc, a in t.postings)
                for t in txs
            )
            if booked:
                res.refund_already_booked += 1
                continue
            # 再判"deg 已双剔"：同额 PDF 消费行也未匹配（±45 天）→ 两侧留痕、无需动作
            pair = next((pr for pr in res.unmatched_pdf
                         if abs(pr.amount - abs(r.amount)) < 0.005
                         and abs((pr.day - r.day).days) <= 60), None)
            if pair is not None:
                res.unmatched_pdf.remove(pair)
                res.refund_paired += 1
                continue
            # 否则找回已入账的原消费（同额、且花呗在贷方的消费分录——排除还款类借方花呗），生成冲销
            def is_consumption(t):
                return any(acc == "Liabilities:花呗" and a < 0 for _, acc, a in t.postings)
            src = next((t for (t, pr, co, ca) in res.splits
                        if abs(pr.amount - abs(r.amount)) < 0.005 and is_consumption(t)), None)
            if src is None:
                src = next((t for t in hb_txs if t.matched and is_consumption(t) and
                            abs(max((abs(a) for _, _, a in t.postings), default=0)
                                - abs(r.amount)) < 0.005), None)
            if src is not None:
                res.refund_reverse.append((r, src))
            else:
                res.refund_fixme.append(r)
    return res


# ═══════════════ 改写与补录 ═══════════════

def apply_splits(txs, res: SplitResult):
    changed = 0
    for tx, pdf_row, co_account, co_amount in res.splits:
        # 找 Liabilities:花呗 分录行，金额改为 pdf 承担额；其后插入组合另一方
        for idx, (i, acc, amt) in enumerate(tx.postings):
            if acc == "Liabilities:花呗" and amt < 0:
                tx.lines[i] = render_posting(acc, -pdf_row.amount)
                insert_at = i + 1
                if co_amount > 0.005:
                    tx.lines.insert(insert_at, render_posting(co_account, -co_amount))
                    insert_at += 1
                tx.lines.insert(insert_at,
                    f"    ; huabei-split: pdf={pdf_row.amount:.2f} co={co_account} {co_amount:.2f} (2026 拆分)")
                changed += 1
                break
    return changed


def render_additions(res: SplitResult):
    """补录分录文本：自动还款补录 + 退款冲销。"""
    out = []
    if res.repay_create or res.refund_reverse:
        out.append("")
        out.append("; ══ split_huabei 补录分录 ══")
    for r in res.repay_create:
        out.append(f"{r.day.strftime('%Y/%m/%d')} * 花呗 - {r.name}（split_huabei 补录，还款来源待人工指定）")
        out.append(render_posting("Liabilities:花呗", abs(r.amount)))
        out.append(render_posting("Assets:FIXME", -abs(r.amount)))
        out.append("")
    for r, src in res.refund_reverse:
        plus_acct = next((acc for _, acc, a in src.postings if a > 0), "Expenses:FIXME")
        out.append(f"{r.day.strftime('%Y/%m/%d')} * 花呗 - {r.name}（split_huabei 退款冲销）")
        out.append(render_posting("Liabilities:花呗", abs(r.amount)))
        out.append(render_posting(plus_acct, -abs(r.amount)))
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journal", type=Path, help="deg 生成的 import-alipay journal")
    ap.add_argument("--pdf", type=Path, default=None, help="花呗账单证明 PDF（默认取 raw/ 下最新）")
    ap.add_argument("--coverage-end", default=None,
                    help="支付宝账单截止日（默认取 journal 内最大日期）")
    ap.add_argument("--dry-run", action="store_true", help="只出报告不改写")
    args = ap.parse_args()

    pdf = args.pdf
    if pdf is None:
        pdfs = sorted(ROOT.glob("raw/*花呗*.pdf"), key=lambda p: p.stat().st_mtime)
        if not pdfs:
            sys.exit("raw/ 下找不到花呗 PDF；可用 --pdf 指定")
        pdf = pdfs[-1]

    # 幂等护栏：已拆分的 journal 拒绝二次拆分（重复插入组合对方会失衡；须先重新 import）
    jtext = args.journal.read_text(encoding="utf-8")
    if "huabei-split:" in jtext or "split_huabei 补录分录" in jtext:
        sys.exit(f"拒绝执行：{args.journal.name} 已含拆分标记（huabei-split）。"
                 "重复拆分会导致组合对方分录重复。请先重新运行 finance.py import 再拆分。")

    password = read_pdf_password()
    pdf_rows = aggregate_installments(parse_pdf(pdf, password))
    prelude, txs = parse_journal_raw(args.journal)
    if args.coverage_end:
        coverage_end = date.fromisoformat(args.coverage_end)
    else:
        coverage_end = max(t.day for t in txs if t.day)
    res = match_all(pdf_rows, txs, coverage_end)

    consumption_in = [r for r in pdf_rows if r.amount > 0 and r.day <= coverage_end]
    matched_n = len(res.splits) + res.verified_pure + len(res.pure_amount_mismatch)
    rate = matched_n / len(consumption_in) * 100 if consumption_in else 100.0

    lines = [
        f"══ 花呗拆分报告 ══",
        f"PDF: {pdf.name}（{len(pdf_rows)} 行；消费 {sum(1 for r in pdf_rows if r.amount>0)}，负数 {sum(1 for r in pdf_rows if r.amount<0)}）",
        f"journal: {args.journal.name}（花呗相关 {sum(1 for t in txs if '花呗' in t.meta.get('method',''))} 笔）",
        f"覆盖期: ≤{coverage_end}（期内 PDF 消费行 {len(consumption_in)}）",
        f"匹配率: {rate:.2f}%（{'✅ ≥95%' if rate >= 95 else '⚠️ <95%'}）",
        f"  组合支付拆分: {len(res.splits)}  纯花呗验证: {res.verified_pure}  金额异常: {len(res.pure_amount_mismatch)}",
        f"  PDF 有账单无（期内，FIXME）: {len(res.unmatched_pdf)}  期外（下月再配）: {len(res.out_of_period_pdf)}",
        f"  账单有 PDF 无（FIXME）: {len(res.unmatched_tx)}  （另有亲情卡/代付 {res.subaccount_expected} 笔属正常：主账单不含子账）",
        f"  自动还款核对一致: {res.repay_verify}  补录: {len(res.repay_create)}  期外还款: {res.out_of_period_negative}  退款冲销: {len(res.refund_reverse)}  退款配对留痕(deg双剔): {res.refund_paired}  退款已入账: {res.refund_already_booked}  退款待人工: {len(res.refund_fixme)}",
        "",
        "── FIXME 明细 ──",
    ]
    for r in res.unmatched_pdf:
        lines.append(f"  [PDF无对] {r.day} {r.name[:40]} {r.amount}")
    for t in res.unmatched_tx[:60]:
        amt = max((abs(a) for _, _, a in t.postings), default=0)
        lines.append(f"  [账单无对] {t.day} {t.head[:60]} {amt} method={t.meta.get('method','')}")
    for hit, r, why in res.pure_amount_mismatch:
        lines.append(f"  [金额异常] {r.day} {r.name[:36]} {why}")
    for r in res.refund_fixme:
        lines.append(f"  [退款待人工] {r.day} {r.name[:36]} {r.amount}")
    report = "\n".join(lines)

    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (REPORTS_DIR / f"huabei-split-{stamp}.txt").write_text(report, encoding="utf-8")
    print(report.split("── FIXME 明细 ──")[0])

    if args.dry_run:
        print("[dry-run] 未改写 journal")
        return
    changed = apply_splits(txs, res)
    BAK_DIR.mkdir(exist_ok=True)
    shutil.copy2(args.journal, BAK_DIR / f"{args.journal.name}.{stamp}.bak")
    body = []
    for tx in txs:
        body.append(tx.head)
        body.extend(tx.lines)
    text = "\n".join(prelude + body)
    additions = render_additions(res)
    if additions:
        text = text.rstrip() + "\n" + additions + "\n"
    args.journal.write_text(text + "\n", encoding="utf-8")
    print(f"已改写 {args.journal.name}：拆分 {changed} 笔；原文件备份 journals/bak/；报告 reports/huabei-split-{stamp}.txt")
    print("下一步：python src/finance.py check")


if __name__ == "__main__":
    main()
