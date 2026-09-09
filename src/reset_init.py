"""Reset PersonalCFO to blank initial state so the user can rerun the
self-guided initialization flow in Paisa (/init → ①②③④).

What it does (lossless — nothing is destroyed):
  1. Stops any running paisa.exe (best-effort, Windows).
  2. Moves raw/* into journals/bak/<ts>/raw/  (real uploaded bills are also
     preserved at the original path on D:\\Mr.Q\\掌控经济\\消费记录, but we
     keep a local copy in the ledger repo as a safety net).
  3. Moves journals/import-*.journal into journals/bak/<ts>/  (so the
     ledger repo's monthly SOP can re-import cleanly next cycle).
  4. Deletes paisa_test/paisa.db (+ sqlite -journal/-shm/-wal) so Paisa
     starts with an empty account/price cache.
  5. Resets paisa_test/all.journal to a header-only file (include list
     cleared; the next `finance.py import` will repopulate it).
  6. Deletes config/local.yaml (huabei password) and the two gitignored
     per-user yamls config/opening_balances.yaml / config/recurring.yaml
     so the user re-enters opening balances and recurring rules cleanly.

It never reads or prints the contents of local.yaml. Run again any time
to wipe the runtime back to blank.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNALS = ROOT / "journals"
BAK = JOURNALS / "bak"
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
        subprocess.run(
            ["taskkill", "//IM", "paisa.exe", "//F"],
            check=False,
            capture_output=True,
        )
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
    (target / "raw").mkdir(parents=True, exist_ok=True)

    raw_moved = move_into(RAW, target / "raw", "*")
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
        print(f"  raw files archived: {len(raw_moved)}")
    if imports_moved:
        print(f"  import journals archived: {len(imports_moved)}")
    print(f"  deleted: paisa.db (+sidecars), all.journal reset")
    if removed_yamls:
        print(f"  deleted config yamls: {', '.join(removed_yamls)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
