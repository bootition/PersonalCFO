#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-zoneinfo.py — 生成 tools/zoneinfo.zip（Windows 时区库）

为什么需要它
------------
Windows 没有系统 tzdata；deg（Go 写的）解析账单时间时必须有一个时区库，
否则报 `unknown time zone Asia/Shanghai`。

Go 的 `time.LoadLocationFromTZData` / zoneinfo 读取器**只支持 ZIP_STORED**
（不支持 deflate 压缩的条目），所以不能直接把 pip 的 tzdata 包打成一个普通的 zip。
本脚本按 IANA 目录结构（`Asia/Shanghai` 这种）逐条写入，并强制 `ZIP_STORED`。

产物随仓库分发（`tools/zoneinfo.zip`，约 0.6 MB），见 `tools/README.md` 与
`THIRD-PARTY-NOTICES.md`（tzdata 为 Apache-2.0，底层 IANA 数据为 public domain）。

用法
----
    venv/Scripts/python.exe scripts/gen-zoneinfo.py            # 生成/覆盖
    venv/Scripts/python.exe scripts/gen-zoneinfo.py --check    # 只校验现有文件

时区数据来源：优先用 venv 里的 `tzdata` 包；没有则退到 Python 自带的
`zoneinfo` 能解析的系统路径（Linux/macOS 有 /usr/share/zoneinfo）。
"""
import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from _console import setup_console  # noqa: E402

setup_console()

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "zoneinfo.zip"

# Go 的 zoneinfo 只认这些文件名形态：区域/城市 或 单文件元数据
SKIP_PARTS = {"__pycache__", "dist-info", "zoneinfo.dist-info"}


def tzdata_root() -> Path | None:
    """定位可用的 IANA 时区目录。"""
    try:
        import tzdata  # type: ignore
        p = Path(tzdata.__file__).parent / "zoneinfo"
        if p.is_dir():
            return p
    except ImportError:
        pass
    for sys_path in ("/usr/share/zoneinfo", "/usr/lib/zoneinfo", "/etc/zoneinfo"):
        p = Path(sys_path)
        if p.is_dir():
            return p
    return None


def collect(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if rel.suffix in (".py", ".pyc", ".pyi"):
            continue
        files.append(p)
    return files


def build(root: Path) -> int:
    files = collect(root)
    if not files:
        sys.exit(f"[错误] {root} 下没找到时区数据文件")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_STORED) as z:
        for p in files:
            z.write(p, p.relative_to(root).as_posix())
    size = OUT.stat().st_size
    print(f"已生成 {OUT.relative_to(ROOT)}：{len(files)} 条，{size:,} 字节"
          f"（ZIP_STORED，Go zoneinfo 要求）")
    return 0


def check() -> int:
    if not OUT.exists():
        print(f"✗ 缺少 {OUT.relative_to(ROOT)}；运行 `python scripts/gen-zoneinfo.py` 生成")
        return 1
    with zipfile.ZipFile(OUT) as z:
        infos = z.infolist()
        bad = [i.filename for i in infos if i.compress_type != zipfile.ZIP_STORED]
        names = {i.filename for i in infos}
    problems = []
    if bad:
        problems.append(f"{len(bad)} 条用了压缩（Go 会读失败），例如 {bad[:3]}")
    for need in ("Asia/Shanghai", "UTC"):
        if need not in names:
            problems.append(f"缺少必需的时区条目 {need}")
    if problems:
        print("✗ " + "；".join(problems))
        return 1
    print(f"✓ {OUT.relative_to(ROOT)} 合法：{len(infos)} 条全部 STORED，含 Asia/Shanghai 与 UTC")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="生成/校验 tools/zoneinfo.zip")
    ap.add_argument("--check", action="store_true", help="只校验现有文件，不生成")
    args = ap.parse_args()

    if args.check:
        return check()
    root = tzdata_root()
    if root is None:
        sys.exit("找不到时区数据。请先 `pip install tzdata`，或在 Linux/macOS 上运行（有 /usr/share/zoneinfo）")
    print(f"时区数据来源：{root}")
    rc = build(root)
    return rc or check()


if __name__ == "__main__":
    sys.exit(main())
