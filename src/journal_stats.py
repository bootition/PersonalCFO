#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""journal_stats.py — hledger/ledger journal 统计（冒烟测试用）

解析 journal 文件，输出：交易笔数、总流量、科目分布、FIXME 笔数/金额/占比。
deg 输出格式约定见 docs/contracts/01_文件契约.md（C1）。
"""
import re
from collections import defaultdict
from pathlib import Path

_TX_HEAD = re.compile(r"^(\d{4})[/\-](\d{2})[/\-](\d{2}) ")
_META = re.compile(r'^\s*; (\w+): "?(.*?)"?$')
_POSTING = re.compile(r"^\s+(\S[^;]*?)\s+(-?\s?[\d,]+(?:\.\d+)?)\s*CNY")


def parse_journal(path):
    """返回 [{head, year, meta, postings:[(account, amount)]}]；跳过 Open Balance。"""
    txs, cur = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = _TX_HEAD.match(line)
        if m:
            if cur:
                txs.append(cur)
            cur = {"head": line.strip(), "year": int(m.group(1)),
                   "meta": {}, "postings": []}
        elif cur is not None:
            mm = _META.match(line)
            if mm:
                cur["meta"][mm.group(1)] = mm.group(2)
                continue
            p = _POSTING.match(line)
            if p:
                amt = float(p.group(2).replace(",", "").replace(" ", ""))
                cur["postings"].append((p.group(1).strip(), amt))
    if cur:
        txs.append(cur)
    return [t for t in txs if t["postings"] and "Open Balance" not in t["head"]]


def journal_stats(path):
    """核心指标字典（全部为聚合值，不含明细）。"""
    txs = parse_journal(path)
    total_abs = sum(abs(a) for t in txs for _, a in t["postings"])
    fixme_txs = 0
    fixme_abs = 0.0
    dist = defaultdict(float)
    years = defaultdict(int)
    for t in txs:
        years[t["year"]] += 1
        fm = 0.0
        for acc, a in t["postings"]:
            dist[acc] += a
            if "FIXME" in acc:
                fm += abs(a)
        if fm:
            fixme_txs += 1
            fixme_abs += fm
    return {
        "txs": len(txs),
        "total_abs": total_abs,
        "fixme_txs": fixme_txs,
        "fixme_abs": fixme_abs,
        "fixme_ratio": (fixme_abs / total_abs) if total_abs else 0.0,
        "fixme_count_ratio": (fixme_txs / len(txs)) if txs else 0.0,
        "years": dict(sorted(years.items())),
        "account_dist": dict(sorted(dist.items())),
    }


def smoke_report(platform, journal_path, source_rows=None):
    """生成单平台冒烟报告文本（聚合指标，可打印/落盘）。"""
    s = journal_stats(journal_path)
    lines = [
        f"── 冒烟 [{platform}] {Path(journal_path).name}",
        f"   交易笔数: {s['txs']}" + (f"（源账单 {source_rows} 行，差异 {source_rows - s['txs']} 行为退款配对/关闭/撤销剔除）" if source_rows else ""),
        f"   年份分布: {s['years']}",
        f"   总流量(双边): {s['total_abs']:,.2f}",
        f"   FIXME: {s['fixme_txs']} 笔（笔数占比 {s['fixme_count_ratio']*100:.2f}%）/ "
        f"{s['fixme_abs']:,.2f} 元（金额占比 {s['fixme_ratio']*100:.2f}%）" +
        ("  ⚠️ 金额占比超 5% 阈值" if s['fixme_ratio'] > 0.05 else "  ✅ 金额占比 ≤5%"),
        f"   科目分布(净额): {len(s['account_dist'])} 个科目",
    ]
    return "\n".join(lines), s
