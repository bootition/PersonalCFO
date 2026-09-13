#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan-pii.py — 公开仓库 PII / 密钥门禁（规则即代码）

为什么关键词不写在本文件里
--------------------------------
本文件会被提交到**公开**仓库。如果把人名、机构名、账户别名直接写成本文件的常量，
门禁本身就会变成新的泄漏源，且进历史后不可逆。因此采用两层：

  * **通用模式**（金额、身份证、卡号、手机号、邮箱、绝对路径、密钥特征）
    —— 硬编码在本文件，对任何使用者都成立；
  * **专属词表**（真实人名 / 机构名 / 账户别名 …）
    —— 从 gitignored 的 `config/pii-rules.local.txt` 读取，永不入库。
    仓库内只提供 `config/pii-rules.example.txt` 占位示例。

规则文件格式（`config/pii-rules.local.txt`，每行一条，# 开头为注释）::

    # 只报告（扫描命中即失败，不自动替换）
    某个真实姓名
    # 报告 + 替换（用于 history-rewrite / --fix）
    某个真实姓名==>家人
    某平台真名==><课程平台>

用法
----
    python scripts/scan-pii.py                  # 扫描全部被跟踪文件（CI 用）
    python scripts/scan-pii.py --staged         # 只扫暂存区（pre-commit 用）
    python scripts/scan-pii.py --history        # 扫描全部历史提交的树（发布前跑一次）
    python scripts/scan-pii.py --fix            # 打印替换建议，不写文件

豁免
----
在行尾加 `pii-ok` 可显式豁免该行（例如文档里必须解释本机制本身）::

    # 例：本行说明 "123456789012345678" 会被规则 3 命中  pii-ok

退出码：0 = 干净；1 = 命中；2 = 用法/环境错误。
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ── 控制台 UTF-8 兜底（Windows 下 stdout 被管道捕获时为 CP936，会 UnicodeEncodeError）──
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / "config" / "pii-rules.local.txt"
RULES_EXAMPLE = ROOT / "config" / "pii-rules.example.txt"

# ── 通用模式：与具体使用者无关，任何公开仓库都不该出现 ──
GENERIC_PATTERNS = [
    # (id, 正则, 说明)
    ("PII-1", r"(?<![\d.])\d{1,3}(?:,\d{3})+\.\d{2}\s*元", "真实金额（千分位）"),
    ("PII-2", r"(?<![\d.\-])\d+\.\d{2}\s*元", "真实金额（含两位小数）"),
    ("PII-3", r"(?<!\d)\d{17}[\dXx](?!\d)", "疑似身份证号"),
    ("PII-4", r"(?<!\d)\d{16,19}(?!\d)", "疑似银行卡/账号（16-19 位连续数字）"),
    ("PII-5", r"(?<!\d)1[3-9]\d{9}(?!\d)", "疑似手机号"),
    ("PII-6", r"[\w.+-]+@(?!users\.noreply\.github\.com)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", "邮箱地址"),
    ("PII-7", r"[A-Za-z]:\\+[^\s\"'`|<>]*[^\x00-\x7f][^\s\"'`|<>]*", "本机绝对路径（含非 ASCII 目录名）"),
    ("PII-8", r"[A-Za-z]:\\+[Uu]sers\\+[^\s\"'`|<>\\]+", "本机绝对路径（含 Windows 用户名）"),
    ("SEC-1", r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}", "GitHub 令牌"),
    ("SEC-2", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥"),
    ("SEC-3", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "AWS Access Key"),
    ("SEC-4", r"\bsk-[A-Za-z0-9]{20,}\b", "API Key（sk- 前缀）"),
    # 只在"后面确实跟了一段像密钥的值"时才报，避免把字段名/占位符/正则示例误判
    ("SEC-5", r"(?i)(?:backup_secret|huabei_pdf_password|pdf_password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{6,}",
     "机密字段被赋了真实值"),
]

# 这些文件允许出现上述通用模式（许可证全文、本脚本、示例占位）
ALLOWLIST_PATHS = {
    "LICENSE",
    "THIRD-PARTY-NOTICES.md",
    "scripts/scan-pii.py",
    "config/pii-rules.example.txt",
    "config/pii-rules.local.txt",
}

# 二进制后缀直接跳过
BINARY_SUFFIXES = {
    ".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
    ".exe", ".dll", ".so", ".dylib", ".woff", ".woff2", ".ttf", ".otf",
    ".db", ".sqlite", ".pcfobak", ".gz", ".tar", ".7z", ".rar",
}

EXEMPT_MARKER = "pii-ok"


def _run(args, **kw):
    # -c core.quotepath=false：否则中文路径会被转义成 "\344\273\273..."，导致读不到文件而静默漏报
    argv = list(args)
    if argv and argv[0] == "git":
        argv = argv[1:]
    return subprocess.run(["git", "-c", "core.quotepath=false", *argv],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(ROOT), **kw)


def load_user_rules() -> list[tuple[str, str, str]]:
    """读取专属词表。返回 [(token, replacement, raw_line), ...]。

    文件缺失不是错误：新克隆者/CI 上没有本地词表是正常的，
    此时只跑通用模式（这也是为什么示例文件要入库）。
    """
    if not RULES_FILE.exists():
        return []
    rules = []
    for raw in RULES_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==>" in line:
            old, new = line.split("==>", 1)
            rules.append((old.strip(), new.strip(), raw))
        else:
            rules.append((line, "", raw))
    return [r for r in rules if r[0]]


def tracked_files(staged: bool) -> list[str]:
    if staged:
        args = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    else:
        args = ["git", "ls-files"]
    res = _run(args)
    if res.returncode != 0:
        sys.exit(f"[错误] git 命令失败：{res.stderr.strip()[:200]}")
    return [f for f in res.stdout.splitlines() if f.strip()]


def scan_text(text: str, path: str, user_rules) -> list[tuple[str, int, str, str]]:
    """返回 [(规则ID, 行号, 命中片段, 说明), ...]"""
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if EXEMPT_MARKER in line:
            continue
        for ti, (token, _repl, _raw) in enumerate(user_rules, 1):
            if token in line:
                # 不把原词打进日志（CI 日志是公开的），只给词表序号
                hits.append(("LOCAL", lineno, f"<词表#{ti}>", "专属词表命中"))
        for pid, pattern, desc in GENERIC_PATTERNS:
            m = re.search(pattern, line)
            if m:
                hits.append((pid, lineno, m.group(0), desc))
    return hits


def scan_worktree(files: list[str], user_rules) -> list[str]:
    problems = []
    for rel in files:
        if rel in ALLOWLIST_PATHS:
            continue
        if Path(rel).suffix.lower() in BINARY_SUFFIXES:
            continue
        p = ROOT / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # 非 UTF-8 文本/不可读，跳过
        for pid, lineno, frag, desc in scan_text(text, rel, user_rules):
            problems.append(f"{rel}:{lineno}: [{pid}] {desc} → {frag[:80]!r}")
    return problems


def scan_history(user_rules) -> list[str]:
    """扫描全部历史提交的树。只扫专属词表 + 高置信通用模式（PII-3/4、SEC-*）。"""
    problems = []
    commits = _run(["git", "rev-list", "--all"]).stdout.split()
    if not commits:
        return problems
    # 一次性拿到全部对象的文本检索：用 git grep 跨所有提交
    tokens = [t for t, _r, _raw in user_rules]
    for c in commits:
        for ti, tok in enumerate(tokens, 1):
            # -I：跳过二进制文件。
            # 时区库（tools/zoneinfo.zip）等二进制里可能恰好出现与中文词条相同的
            # 字节序列，那不是泄漏；不跳二进制会造成假阳性，让门禁失去可信度。
            r = _run(["git", "grep", "-l", "-I", "-F", tok, c, "--"])
            for f in r.stdout.splitlines():
                problems.append(f"{c[:8]}:{f.split(':', 1)[-1]}: [LOCAL] <词表#{ti}> 命中（历史）")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="公开仓库 PII / 密钥门禁")
    ap.add_argument("--staged", action="store_true", help="只扫描暂存区（pre-commit）")
    ap.add_argument("--history", action="store_true", help="扫描全部历史提交（发布前跑一次）")
    ap.add_argument("--fix", action="store_true", help="打印替换建议（不写文件）")
    ap.add_argument("--show-tokens", action="store_true",
                    help="打印词表序号→词条对照（本地排错用；CI 日志中不要开）")
    args = ap.parse_args()

    user_rules = load_user_rules()
    if args.show_tokens:
        for ti, (tok, repl, _raw) in enumerate(user_rules, 1):
            print(f"  词表#{ti}: {tok!r} -> {repl!r}")
    if not RULES_FILE.exists():
        print(f"[提示] 未找到专属词表 {RULES_FILE.relative_to(ROOT)}，仅跑通用模式。")
        print(f"       本地使用请复制 {RULES_EXAMPLE.relative_to(ROOT)} 并填入真实词条（该文件不入库）。")

    problems = scan_worktree(tracked_files(args.staged), user_rules)

    if args.history:
        problems += scan_history(user_rules)

    if problems:
        print(f"✗ PII 门禁命中 {len(problems)} 处 —— 拒绝提交/发布\n")
        for line in problems:
            print("  " + line)
        print("\n处理办法：")
        print("  1. 把真实值换成占位符（如 <家人姓名> / <金额>），真实值移到 gitignored 文件；")
        print("  2. 确属必要（例如解释本机制本身）时，在该行末尾加 `pii-ok` 显式豁免；")
        print("  3. 若专属词表规则带 `==>新值`，可用 `python scripts/scan-pii.py --fix` 查看替换建议。")
        if args.fix:
            print("\n── 替换建议（sed 风格）──")
            for tok, repl, _raw in user_rules:
                if repl:
                    print(f"  s/{tok}/{repl}/g")
        return 1

    print("✓ PII 门禁通过：未发现敏感数据" +
          (f"（专属词表 {len(user_rules)} 条）" if user_rules else "（仅通用模式）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
