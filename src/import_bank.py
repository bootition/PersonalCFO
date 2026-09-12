#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""import_bank.py — 银行账单导入（建行 ccb / 招行 cmb / 工行 icbc）（P7.22）

背景：`finance.py import` 只自动处理支付宝 CSV / 微信 XLSX / 花呗 PDF；
银行账单需要各自 provider + 配置，本脚本把这一步做成一条命令。

用法（仓库根，venv/Scripts/python）：
  # 先干跑：生成到 .planning/bank-<bank>-<stem>.journal，只报笔数/平衡，不动正式账本
  venv/Scripts/python src/import_bank.py --bank ccb --dry-run "raw/建行-交易明细.xls"
  # 确认后正式导入：写 journals/import-<bank>-<stem>.journal + 自动刷新 include + check
  venv/Scripts/python src/import_bank.py --bank ccb "raw/建行-交易明细.xls"

约定：
  - 同一银行多份账单可一次传多个文件；
  - 正式导入后跑 `vendor/paisa/paisa.exe update --config paisa_test/paisa.yaml` 同步 UI；
  - 首次导入默认全部落 Expenses:FIXME / Assets:银行存款:<行>，请按冒烟报告补 config/<bank>.yaml 规则。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finance as F  # noqa: E402

ZONEINFO = F.ROOT / "tools" / "zoneinfo.zip"   # P7.22：Windows 无 tzdata，deg 解析时区需要

BANKS = {
    "ccb": "config/ccb.yaml",    # 建设银行（csv/xls/xlsx）
    "cmb": "config/cmb.yaml",    # 招商银行（csv，借记/信用卡）
    "icbc": "config/icbc.yaml",  # 工商银行（csv，借记/信用卡自动识别）
}


def import_one(bank: str, bill: Path, out_stem: str, dry_run: bool) -> bool:
    if not bill.exists():
        print(f"❌ 文件不存在：{bill}")
        return False
    out_dir = F.ROOT / ".planning" if dry_run else F.JOURNALS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"import-{bank}-{out_stem}.journal"
    subprocess.run(["chcp.com", "65001"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    res = subprocess.run(
        [str(F.DEG), "translate", "-p", bank, "-t", "ledger",
         "--config", str(F.ROOT / BANKS[bank]),
         str(bill), "-o", str(out)],
        capture_output=True,
        env={**os.environ, "ZONEINFO": str(ZONEINFO)})
    if res.returncode != 0:
        print(f"❌ deg 导入失败（{bill.name}）：{res.stderr.decode('utf-8', errors='replace')[:400]}")
        return False
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    txs = sum(1 for l in text.splitlines() if l[:4].isdigit() and "/" in l[:10])
    # 用 hledger 校验这份 journal 自身平衡
    chk = subprocess.run([str(F.ROOT / "tools" / "hledger-bin" / "hledger.exe"),
                          "-f", str(out), "check", "balanced"], capture_output=True)
    ok = chk.returncode == 0
    print(f"{'[干跑]' if dry_run else '[导入]'} {bill.name} -> {out.name}：{txs} 笔，"
          f"平衡 {'✅' if ok else '❌ ' + chk.stderr.decode('utf-8', errors='replace')[:200]}")
    if not ok:
        return False
    if not dry_run:
        F.refresh_paisa_includes()
        F.check()
        print("   已刷新 paisa include；接下来运行 paisa update 同步界面")
    return True


def main():
    ap = argparse.ArgumentParser(description="银行账单导入（建行/招行/工行）")
    ap.add_argument("--bank", required=True, choices=sorted(BANKS))
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="只写 .planning/ 并报数，不改正式账本")
    args = ap.parse_args()
    # 同一批文件 stem 相同（如借记/信用卡都叫 example-cmb-records）时加序号，避免互相覆盖
    seen: dict[str, int] = {}
    jobs = []
    for f in args.files:
        seen[f.stem] = seen.get(f.stem, 0) + 1
        stem = f.stem if seen[f.stem] == 1 else f"{f.stem}-{seen[f.stem]}"
        jobs.append((f, stem))
    ok = all(import_one(args.bank, f, stem, args.dry_run) for f, stem in jobs)
    if args.dry_run and ok:
        print("\n干跑通过。确认无误后去掉 --dry-run 正式导入；有疑问先看 .planning/ 下的 journal。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
