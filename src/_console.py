#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_console.py — Windows 控制台编码统一兜底

问题
----
Windows 上 Python 的 stdout 编码取决于"目标是不是控制台"：

* 直接输出到**控制台** → 走 WriteConsoleW，UTF-8 正常；
* 被**管道 / 重定向 / 其它程序捕获**（`python x.py | tee`、`> log.txt`、
  CI、以及 Paisa 的 `pcfoExec`）→ 用 ANSI 代码页（简体中文系统 = **CP936/GBK**）。

而本项目大量输出 `✓ ✗ ✅ ❌ ⚠️ → · ─` 等非 GBK 字符，
于是**一旦输出被重定向就 `UnicodeEncodeError` 崩掉**。实测：

    venv/Scripts/python.exe -c "import sys;print(sys.stdout.encoding)"   # gbk
    venv/Scripts/python.exe scripts/reconcile-check.py | tail
    → UnicodeEncodeError: 'gbk' codec can't encode character '\\u2705'

注意：先执行 `chcp.com 65001` **不能**解决 —— chcp 只影响控制台代码页，
对已经建立的管道无效。

影响面（修复前）
----------------
只有 `src/finance.py` 有兜底，其余全崩：

* `scripts/backup.py verify` 崩 → 恢复演练永不执行；
* `scripts/e2e-sweep.py` 崩在有失败项时 → **失败清单根本不打印**；
* `src/import_bank.py` 崩在 journal 已落盘、include 未刷新之前 → **Paisa 口径分裂**。

用法
----
在**每个可执行入口**的最前面调用一次（幂等）：

    from _console import setup_console
    setup_console()

或在脚本顶部（当同目录模块可能不在 sys.path 时）：

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _console import setup_console
    setup_console()
"""
import sys


def setup_console() -> None:
    """把 stdout/stderr 切成 UTF-8 + 容错，避免中文/符号输出崩在管道上。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — 某些被替换过的流没有 reconfigure
            pass
