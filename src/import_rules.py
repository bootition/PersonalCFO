#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""import_rules.py — deg 规则的分层合成（公共模板 + 私人覆盖）

为什么需要它
------------
deg 的 `--config` 只接受**单个**文件（`translate --help` 无叠加选项），
而"可公开发布的规则模板"与"含真实对手方名称的私人规则"必须分离：

    config/alipay.yaml        公共模板，入库（只有通用规则 + 占位符）
    config/alipay.local.yaml  私人规则，**永不入库**（真实人名/商户名匹配串）

本模块把两者合成到 `config/.merged-<platform>.yaml`（同样不入库），再交给 deg。

语义保证
--------
deg 的规则引擎是"按顺序逐条评估、命中即赋值、后命中覆盖先命中"。
因此**私人规则一律追加在公共规则之后** —— 与原来"在文件末尾追加用户定性规则"
的行为完全一致，导入结果不变。

用法
----
    from import_rules import merged_config
    cfg = merged_config("alipay")     # -> Path，公共文件无本地覆盖时原样返回

CLI（供排错/自检）：

    python src/import_rules.py alipay --show     # 打印合成结果摘要
    python src/import_rules.py --check           # 校验全部平台
"""
import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("需要 PyYAML：venv/Scripts/python.exe -m pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

# 支持的平台（与 finance.IMPORT_JOBS / import_bank.BANKS 对齐）
PLATFORMS = ("alipay", "wechat", "ccb", "cmb", "icbc")


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        sys.exit(f"[规则] {path.name} 顶层必须是映射（YAML mapping）")
    return data


def _provider_rules(doc: dict, platform: str) -> list:
    """从配置文档里取出规则列表。兼容两种写法：
        platform: {rules: [...]}      ← deg 官方格式
        rules: [...]                  ← 片段格式
    """
    if isinstance(doc.get(platform), dict):
        rules = doc[platform].get("rules")
    else:
        rules = doc.get("rules")
    if rules is None:
        return []
    if not isinstance(rules, list):
        sys.exit(f"[规则] {platform} 的 rules 必须是列表")
    return rules


def merged_config(platform: str, base_dir: Path = CONFIG_DIR) -> Path:
    """合成公共模板 + 私人覆盖，返回可交给 deg 的配置文件路径。

    * 没有 `config/<platform>.local.yaml` 时，直接返回公共模板（零行为变化）
    * 有本地覆盖时，生成 `config/.merged-<platform>.yaml`
    """
    base = base_dir / f"{platform}.yaml"
    if not base.exists():
        sys.exit(f"[规则] 找不到公共模板 {base}")
    local = base_dir / f"{platform}.local.yaml"

    if not local.exists():
        return base

    base_doc = _load(base)
    local_doc = _load(local)

    merged = dict(base_doc)
    # 本地可覆盖顶层标量（如 defaultMinusAccount），但 provider 规则永远是"追加"
    for k, v in local_doc.items():
        if k != platform and not (isinstance(v, list) and k == "rules"):
            if k in ("rules",):
                continue
            merged[k] = v

    merged_rules = list(_provider_rules(base_doc, platform))
    merged_rules += _provider_rules(local_doc, platform)

    if platform in base_doc and isinstance(base_doc[platform], dict):
        merged[platform] = dict(base_doc[platform])
        merged[platform]["rules"] = merged_rules
    else:
        merged.pop(platform, None)
        merged["rules"] = merged_rules

    out = base_dir / f".merged-{platform}.yaml"
    header = (
        f"# 本文件由 src/import_rules.py 自动生成，请勿手改。\n"
        f"# 来源：{base.name}（公共模板） + {local.name}（私人覆盖，不入库）\n"
        f"# 私人规则追加在末尾 —— 依 deg「后命中覆盖先命中」语义，行为与原单文件一致。\n"
    )
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        yaml.safe_dump(merged, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="deg 规则分层合成")
    ap.add_argument("platform", nargs="?", choices=PLATFORMS, help="平台名")
    ap.add_argument("--show", action="store_true", help="打印合成摘要")
    ap.add_argument("--check", action="store_true", help="校验全部平台")
    args = ap.parse_args()

    targets = PLATFORMS if args.check or not args.platform else (args.platform,)
    rc = 0
    for p in targets:
        base = CONFIG_DIR / f"{p}.yaml"
        if not base.exists():
            print(f"  {p:<8} 跳过（无公共模板）")
            continue
        local = CONFIG_DIR / f"{p}.local.yaml"
        out = merged_config(p)
        n_base = len(_provider_rules(_load(base), p))
        n_local = len(_provider_rules(_load(local), p)) if local.exists() else 0
        tag = "合成" if local.exists() else "直接使用公共模板"
        print(f"  {p:<8} {tag}：公共 {n_base} 条"
              + (f" + 私人 {n_local} 条 = {n_base + n_local} 条 → {out.name}" if local.exists() else ""))
        if args.show and local.exists():
            print(f"           {out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
