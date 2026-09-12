#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backup.py — PersonalCFO 账本加密备份 / 校验 / 恢复（P7.17）

为什么要它：journals/raw/reports/close/paisa.db 都是 gitignore 的敏感数据，
主仓库与账本仓都只覆盖 journals 的一部分；本脚本把"全部敏感数据"打成
AES-256-GCM 加密归档，防止误删/磁盘故障，并可离线校验与恢复。

用法（仓库根，venv/Scripts/python）：
  python scripts/backup.py backup                # 生成 backups/personalcfo-<ts>.pcfobak
  python scripts/backup.py verify <archive>      # 解密+解压到临时目录，逐文件校验 sha256 + hledger check
  python scripts/backup.py restore <archive> --to <dir> [--force]
  python scripts/backup.py list                  # 列出本地归档

密码来源（三选一，优先级从高到低）：
  --password <str> / 环境变量 PCFO_BACKUP_PASS / config/backup_secret.txt（首次 backup 自动生成，gitignore）

归档格式：magic(8) "PCFOBAK1" + salt(16) + nonce(12) + AESGCM(ciphertext)
  key = PBKDF2-HMAC-SHA256(password, salt, 600_000, dklen=32)
"""
import argparse
import getpass
import hashlib
import io
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover
    sys.exit("需要 cryptography：venv/Scripts/python -m pip install cryptography")

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "backups"
SECRET_FILE = ROOT / "config" / "backup_secret.txt"
MAGIC = b"PCFOBAK1"
ITERATIONS = 600_000

# 需要备份的内容（相对仓库根）；目录递归，文件单加
INCLUDE = [
    "journals",
    "raw",
    "reports",
    "close",
    "config",
    "paisa_test/paisa.yaml",
    "paisa_test/paisa.db",
    "docs/本地敏感信息_DO_NOT_COMMIT.md",
    "任务计划.md",
    "docs/STATUS.md",
]
# 绝不进归档的东西（密码本身、临时文件、node_modules 等）
EXCLUDE_NAMES = {"backup_secret.txt", ".deg-tmp", "node_modules", "__pycache__"}
EXCLUDE_SUFFIX = (".pcfobak", ".tmp", ".lock")


def sha256_file(path: Path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def git_rev(path: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else "n/a"
    except Exception:  # noqa: BLE001
        return "n/a"


def load_password(args) -> str:
    if args.password:
        return args.password
    if os.environ.get("PCFO_BACKUP_PASS"):
        return os.environ["PCFO_BACKUP_PASS"]
    if SECRET_FILE.exists():
        pw = SECRET_FILE.read_text(encoding="utf-8").strip()
        if pw:
            return pw
    # 首次运行：生成随机密码并落盘（仅本地，gitignore），提醒用户抄到密码管理器
    pw = secrets.token_urlsafe(24)
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_FILE.write_text(pw + "\n", encoding="utf-8")
    print(f"⚠️  首次运行：已生成备份密码并写入 {SECRET_FILE.relative_to(ROOT)}（gitignore）")
    print("    请立即把该文件内容抄进密码管理器——密码丢失则归档无法恢复。")
    return pw


def collect_files():
    files, missing = [], []
    for rel in INCLUDE:
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if not f.is_file():
                    continue
                parts = set(f.parts)
                if parts & EXCLUDE_NAMES or f.suffix in EXCLUDE_SUFFIX or f.name.startswith(".deg-tmp"):
                    continue
                files.append(f)
        else:
            files.append(p)
    return files, missing


def cmd_backup(args):
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    files, missing = collect_files()
    if not files:
        sys.exit("没有可备份的文件")
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "root": str(ROOT),
        "git_main": git_rev(ROOT),
        "git_journals": git_rev(ROOT / "journals"),
        "file_count": len(files),
        "total_bytes": sum(f.stat().st_size for f in files),
        "missing": missing,
        "files": {},
    }

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=6) as tar:
        for f in files:
            arc = f"backup-{ts}/{f.relative_to(ROOT).as_posix()}"
            tar.add(f, arcname=arc, recursive=False)
            manifest["files"][f.relative_to(ROOT).as_posix()] = {
                "size": f.stat().st_size,
                "sha256": sha256_file(f),
            }
        man = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        info = tarfile.TarInfo(f"backup-{ts}/MANIFEST.json")
        info.size = len(man)
        info.mtime = int(time.time())
        tar.addfile(info, io.BytesIO(man))

    password = load_password(args)
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=32)
    ciphertext = AESGCM(key).encrypt(nonce, buf.getvalue(), MAGIC)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    out = BACKUP_DIR / f"personalcfo-{ts}.pcfobak"
    out.write_bytes(MAGIC + salt + nonce + ciphertext)
    digest = sha256_file(out)
    print(f"✅ 备份完成：{out.relative_to(ROOT)}")
    print(f"   文件 {len(files)} 个 / 原始 {manifest['total_bytes']/1024/1024:.1f} MB"
          f" → 归档 {out.stat().st_size/1024/1024:.1f} MB")
    print(f"   sha256 {digest}")
    if missing:
        print(f"   ⚠️ 未找到（跳过）：{', '.join(missing)}")
    _prune(args.keep)
    return 0


def _prune(keep: int):
    archives = sorted(BACKUP_DIR.glob("personalcfo-*.pcfobak"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in archives[keep:]:
        old.unlink()
        print(f"   已清理旧归档 {old.name}")


def _decrypt(archive: Path, password: str) -> io.BytesIO:
    raw = archive.read_bytes()
    if raw[:8] != MAGIC:
        sys.exit(f"{archive} 不是 PersonalCFO 备份格式")
    salt, nonce, ct = raw[8:24], raw[24:36], raw[36:]
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=32)
    try:
        data = AESGCM(key).decrypt(nonce, ct, MAGIC)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"解密失败（密码错误或归档损坏）：{e}")
    return io.BytesIO(data)


def cmd_verify(args):
    archive = Path(args.archive)
    buf = _decrypt(archive, load_password(args))
    tmp = Path(tempfile.mkdtemp(prefix="pcfo-verify-"))
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        tar.extractall(tmp)
    sub = next(tmp.iterdir())
    manifest = json.loads((sub / "MANIFEST.json").read_text(encoding="utf-8"))
    bad = []
    for rel, meta in manifest["files"].items():
        p = sub / rel
        if not p.exists() or p.stat().st_size != meta["size"] or sha256_file(p) != meta["sha256"]:
            bad.append(rel)
    print(f"清单：{manifest['file_count']} 文件 / {manifest['total_bytes']/1024/1024:.1f} MB"
          f"（主仓 {manifest['git_main']}，账本仓 {manifest['git_journals']}）")
    print(f"sha256 校验：{'✅ 全部一致' if not bad else '❌ 不一致 ' + str(bad[:5])}")
    # 恢复演练：用还原出来的 journals 跑 hledger 平衡检查
    hledger = ROOT / "tools" / "hledger-bin" / "hledger.exe"
    journals = sorted((sub / "journals").glob("*.journal"))
    if hledger.exists() and journals:
        cmd = [str(hledger), "-I"]
        for j in journals:
            cmd += ["-f", str(j)]
        r = subprocess.run(cmd + ["check", "balanced"], capture_output=True)
        print(f"恢复演练 hledger check balanced：{'✅ rc=0' if r.returncode == 0 else '❌ ' + r.stderr.decode('utf-8','replace')[:200]}")
    shutil.rmtree(tmp, ignore_errors=True)
    ok = not bad
    print("结论：" + ("✅ 归档可用，可放心恢复" if ok else "❌ 归档存在问题"))
    return 0 if ok else 1


def cmd_restore(args):
    archive = Path(args.archive)
    target = Path(args.to).resolve()
    if target.exists() and any(target.iterdir()) and not args.force:
        sys.exit(f"{target} 非空；确认覆盖请加 --force")
    buf = _decrypt(archive, load_password(args))
    tmp = Path(tempfile.mkdtemp(prefix="pcfo-restore-"))
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        tar.extractall(tmp)
    sub = next(tmp.iterdir())
    target.mkdir(parents=True, exist_ok=True)
    for item in sub.iterdir():
        if item.name == "MANIFEST.json":
            continue
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"✅ 已恢复到 {target}（原账本未被覆盖，请人工确认后替换）")
    return 0


def cmd_list(_args):
    archives = sorted(BACKUP_DIR.glob("personalcfo-*.pcfobak"), reverse=True)
    if not archives:
        print("backups/ 下没有归档")
        return 0
    for a in archives:
        st = a.stat()
        print(f"{a.name}  {st.st_size/1024/1024:6.1f} MB  {datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="PersonalCFO 账本加密备份")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("backup", cmd_backup), ("verify", cmd_verify), ("restore", cmd_restore)):
        p = sub.add_parser(name)
        p.set_defaults(func=fn)
        p.add_argument("archive", nargs="?" if name == "backup" else None,
                       help="归档路径（backup 不需要）")
        p.add_argument("--password", help="备份密码（默认读 PCFO_BACKUP_PASS 或 config/backup_secret.txt）")
        if name == "backup":
            p.add_argument("--keep", type=int, default=10, help="保留最近 N 份（默认 10）")
        if name == "restore":
            p.add_argument("--to", required=True, help="恢复目标目录")
            p.add_argument("--force", action="store_true", help="目标非空时覆盖")
    p = sub.add_parser("list")
    p.set_defaults(func=cmd_list)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
