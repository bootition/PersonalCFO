#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_recurring.py — 定期规则生成器（P1.6）

用户把工资/房租/固定资产数据填进 config/recurring_rules.yaml（仅本地，不入库；
缺失时自动生成模板），运行：

    venv/Scripts/python src/gen_recurring.py

生成 journals/recurring.journal（hledger `~ monthly` 定期规则）：
  - 工资月末计提（借 应收账款:工资 / 贷 主营收入:工资）；到账冲销属日常分录（导入时人工/规则）
  - 房租按月摊销（借 房租摊销 / 贷 预付账款:房租）；季度/年度预付属日常分录
  - 固定资产月度折旧（借 折旧 / 贷 累计折旧:X；直线法、启用次月起、年限到期自动停）
--forecast 报表随即生效。
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
JOURNALS_DIR = ROOT / "journals"
CONFIG_DIR = ROOT / "config"
RULES_FILE = CONFIG_DIR / "recurring_rules.yaml"

TEMPLATE = """# 定期规则数据（仅本地，永不入库）
# 填好后运行： venv/Scripts/python src/gen_recurring.py
# 所有字段留空即不生成对应规则。

# 工资月末计提（就业后生效；金额=税后到手数，社保公积金不入表——既定裁决）
salary:
  amount:            # 月计提额，如 8000.00；空=暂不启用
  note: 工资月末计提

# 房租摊销（季度/年度预付的付款分录走日常导入，这里只生成按月摊销规则）
rent:
  monthly:           # 月摊销额，如 2000.00；空=不启用

# 固定资产折旧（直线法；每项一行）
# - account: Assets:固定资产:电子设备   # 资产科目
#   cost: 12000.00                      # 历史原价
#   years: 3                            # 折旧年限
#   start: "2025-08"                    # 启用年月（次月起折）
depreciation: []
"""


def read_kv_blocks(text: str):
    """极简 YAML 读取（只认本模板结构）：返回 dict。避免引依赖。"""
    import re
    data = {"salary": {}, "rent": {}, "depreciation": []}
    section = None
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if re.match(r"^(salary|rent|depreciation):", s):
            section = s.split(":")[0]
            current = None
            continue
        if section in ("salary", "rent"):
            m = re.match(r"^(\w+):\s*(.*)$", s)
            if m:
                data[section][m.group(1)] = m.group(2).strip().strip('"').strip("'")
        elif section == "depreciation":
            if s.startswith("- "):
                current = {}
                data["depreciation"].append(current)
                s = s[2:].strip()
            m = re.match(r"^(\w+):\s*(.*)$", s)
            if m and current is not None:
                current[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return data


def _money(s, label):
    s = (s or "").strip()
    if not s:
        return None
    from finance import parse_money_strict
    try:
        return parse_money_strict(s)
    except ValueError as e:
        sys.exit(f"{label} {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="允许覆盖已有 recurring.journal")
    args = ap.parse_args()

    if not RULES_FILE.exists():
        RULES_FILE.write_text(TEMPLATE, encoding="utf-8")
        print(f"已生成模板 {RULES_FILE}（仅本地，不入库）")
        print("请填工资/房租/固定资产数据后重跑本命令。")
        return

    cfg = read_kv_blocks(RULES_FILE.read_text(encoding="utf-8"))
    blocks = ["; 定期规则（gen_recurring 生成，来源 config/recurring_rules.yaml）",
              "; 修改请改 yaml 后重新生成本文件，勿手改（会被覆盖）"]

    sal = cfg["salary"].get("amount")
    if sal:
        amount = _money(sal, "工资")
        blocks += ["",
                   "; 工资月末计提（就业后生效；到账冲销走日常分录）",
                   "~ monthly",
                   f"    ; {cfg['salary'].get('note', '工资计提')}",
                   f"    Assets:应收账款:工资    {amount:,.2f} CNY",
                   f"    Income:主营收入:工资    -{amount:,.2f} CNY"]

    rent = cfg["rent"].get("monthly")
    if rent:
        m = _money(rent, "房租")
        blocks += ["",
                   "; 房租按月摊销（预付分录走日常导入）",
                   "~ monthly",
                   f"    Expenses:房租摊销    {m:,.2f} CNY",
                   f"    Assets:预付账款:房租    -{m:,.2f} CNY"]

    for item in cfg["depreciation"]:
        try:
            acct = item["account"]
            cost = _money(item["cost"], "折旧原价")
            years = float(item["years"])
            start = item["start"]
        except (KeyError, ValueError) as e:
            sys.exit(f"折旧条目字段缺失/非法: {item} ({e})")
        if not acct.startswith("Assets:固定资产:"):
            sys.exit(f"折旧 account 须 Assets:固定资产: 开头: {acct}")
        leaf = acct.split(":")[-1]
        monthly = cost / (years * 12)
        y, m = int(start[:4]), int(start[5:7])
        # 次月起折：start+1 月；到期月 = start + years*12（含）
        sm = m + 1
        sy, sm = (y + 1, 1) if sm > 12 else (y, sm)
        end_m = (m + int(years) * 12 - 1) % 12 + 1
        end_y = y + (m + int(years) * 12 - 1) // 12
        blocks += ["",
                   f"; 折旧：{leaf} 原价 {cost:,.2f}，{years:.0f} 年直线，{start} 启用",
                   f"~ monthly from {sy}-{sm:02d} to {end_y}-{end_m:02d}",
                   f"    Expenses:折旧    {monthly:,.2f} CNY",
                   f"    Assets:累计折旧:{leaf}    -{monthly:,.2f} CNY"]

    if len(blocks) <= 2:
        sys.exit(f"{RULES_FILE} 全部留空：没有可生成的规则。请先填写数据。")

    out = JOURNALS_DIR / "recurring.journal"
    if out.exists() and not args.force:
        sys.exit(f"{out.name} 已存在。数据变更请加 --force 重建（会覆盖）")
    out.write_text("\n".join(blocks) + "\n", encoding="utf-8")
    print(f"已写入 {out.name}")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from finance import check, refresh_paisa_includes  # noqa: E402
    refresh_paisa_includes()
    check()
    print("提示：forecast 报表随即生效（venv/Scripts/python src/finance.py forecast）")


if __name__ == "__main__":
    main()
