"""把 PersonalCFO 复位到空白状态，以便重新走 Paisa「初始化」向导（/init ①②③④）。

⚠️ 本操作**不是无损的**（早期版本误写为 lossless，已更正）。它会：
  1. 尽力停止正在运行的 paisa.exe（Windows；失败不阻断）。
  2. 把 raw/* 搬到 backups/raw-bak/<ts>/ —— 账本记录**不含**账单原件；
     账单原件仍在项目外的原始账单目录（路径见 docs/本地敏感信息_DO_NOT_COMMIT.md）。
     （早期版本把它搬到 journals/bak/<ts>/raw/，而 journals 仓当时没有 .gitignore，
       一旦执行 `git add .` 就会把含姓名与账号的账单提交进账本仓 —— 已修）
  3. 把 journals/import-*.journal 搬到 journals/bak/<ts>/（journals/.gitignore 已排除 bak/）。
  4. 删除 paisa_test/paisa.db（含 sqlite -journal/-shm/-wal），使 Paisa 从空缓存重建。
  5. **删除** config/local.yaml（花呗 PDF 密码）、opening_balances.yaml、
     recurring_rules.yaml —— 这些是 gitignore 的本地唯一副本。

因此调用前请先跑 `python scripts/backup.py backup`。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── 控制台编码兜底（管道/重定向下 stdout 为 CP936，中文与符号会崩）──
# 本段自足，不依赖文件内已有的 import（有些模块没有 import sys）
import sys as _sys
import pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent))
from _console import setup_console  # noqa: E402
setup_console()

ROOT = Path(__file__).resolve().parent.parent
JOURNALS = ROOT / "journals"
BAK = JOURNALS / "bak"                 # 账本快照（journals/.gitignore 已排除 bak/）
RAW_BAK = ROOT / "backups" / "raw-bak"  # 账单原件快照，**不放 journals/**
                                        # （账单含真实姓名与账号，放账本仓有误入库风险；
                                        #   根 .gitignore 已排除 /backups/）
RAW = ROOT / "raw"
PAISA_TEST = ROOT / "paisa_test"
CONFIG = ROOT / "config"
ALL_JOURNAL = PAISA_TEST / "all.journal"

GITIGNORED_YAMLS = [
    CONFIG / "local.yaml",
    CONFIG / "opening_balances.yaml",
    CONFIG / "recurring.yaml",
    CONFIG / "recurring_rules.yaml",  # P7 红队 P2-2：实际文件名为 recurring_rules.yaml
]


def stop_paisa() -> None:
    if os.name != "nt":
        return
    try:
        # 必须用 "/IM" 而不是 "//IM"：
        # "//IM" 只在 MSYS/Git-Bash 下会被路径转换改写成 "/IM"；
        # Python 走 CreateProcess 原样传参 → taskkill 报 "Invalid argument/option - '//IM'"，
        # 而 check=False + capture_output 把错误吞掉 → 进程从未被杀 → 删 paisa.db 抛 PermissionError，
        # 停在"raw 已归档、journals 已归档、config 未删、db 还在"的半重置态。
        r = subprocess.run(
            ["taskkill", "/IM", "paisa.exe", "/F"],
            check=False,
            capture_output=True,
        )
        if r.returncode not in (0, 128):  # 128：进程本来就没在跑
            msg = r.stderr.decode("gbk", errors="replace").strip()[:120]
            print(f"  [警告] taskkill 返回 {r.returncode}：{msg}")
    except FileNotFoundError:
        pass
    # P7 红队 P2-2：0.3s 曾致 paisa.db 仍被进程占用；等 1.5s 再删
    time.sleep(1.5)


def move_into(src_dir: Path, dst: Path, pattern: str) -> list[Path]:
    moved: list[Path] = []
    if not src_dir.exists():
        return moved
    for p in sorted(src_dir.glob(pattern)):
        target = dst / p.name
        if target.exists():
            target = dst / f"{p.stem}_{int(time.time())}{p.suffix}"
        shutil.move(str(p), str(target))
        moved.append(target)
    return moved


def reset_all_journal() -> None:
    ALL_JOURNAL.write_text(
        "# Paisa 合并入口（finance.py import 自动维护，勿手改）\n",
        encoding="utf-8",
    )


def remove_sqlite_db(db: Path) -> None:
    for suffix in ("", "-journal", "-shm", "-wal"):
        f = Path(str(db) + suffix)
        for attempt in range(3):
            if not f.exists():
                break
            try:
                f.unlink()
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.5)


def main() -> int:
    stop_paisa()
    ts = time.strftime("%Y%m%d-%H%M%S")
    target = BAK / ts
    target.mkdir(parents=True, exist_ok=True)
    raw_target = RAW_BAK / ts
    raw_target.mkdir(parents=True, exist_ok=True)

    raw_moved = move_into(RAW, raw_target, "*")
    imports_moved = move_into(JOURNALS, target, "import-*.journal")
    # P7 红队 P2-2：期初分录与定期规则 journal 也归档，不留残留
    opening_moved = move_into(JOURNALS, target, "*-opening.journal")
    recurring_moved = move_into(JOURNALS, target, "recurring.journal")

    db = PAISA_TEST / "paisa.db"
    remove_sqlite_db(db)

    reset_all_journal()

    removed_yamls: list[str] = []
    for y in GITIGNORED_YAMLS:
        if y.exists():
            y.unlink()
            removed_yamls.append(y.name)

    print("reset complete:")
    print(f"  archive dir: {target.relative_to(ROOT)}")
    if raw_moved:
        print(f"  raw archive: {raw_target.relative_to(ROOT)}")
    if raw_moved:
        print(f"  raw files archived: {len(raw_moved)}")
    if imports_moved:
        print(f"  import journals archived: {len(imports_moved)}")
    print(f"  deleted: paisa.db (+sidecars), all.journal reset")
    if removed_yamls:
        print(f"  deleted config yamls: {', '.join(removed_yamls)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
