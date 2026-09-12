---
title: Wealthfolio 与银行账单接入（用户操作手册）
status: approved
last_reviewed: 2026-09-12
---

# Wealthfolio 与银行账单接入（只剩这两件需要你动手）

> 这是 26 项清单里最后两项需要你本人操作的任务。按本文做完，投资侧和银行侧就闭环了。
> 任何一步卡住，直接把报错发我。

## A. Wealthfolio（P3-1：投资与目标）

### A1. 安装

- 官网/发布页下载安装包（参考源码在 `reference/wealthfolio/`）：<https://wealthfolio.app> 或 GitHub `afadil/wealthfolio` Releases。
- 首次启动会让你建一个本地账本（数据存在本机 SQLite，不上传）。

### A2. 建账户（**名字必须照抄**，否则回写脚本认不出）

在 Wealthfolio 里建 4 个账户，名称与 `src/sync_fair_value.py` 的 `ACCOUNT_MAP` 一致：

| Wealthfolio 账户名 | 对应账本科目 |
|---|---|
| `哈利布朗` | `Assets:投资:基金` |
| `攒股收息` | `Assets:投资:股票` |
| `虚拟货币` | `Assets:投资:虚拟货币` |
| `CS饰品` | `Assets:投资:CS饰品` |

> 想用别的名字：改 `src/sync_fair_value.py` 的 `ACCOUNT_MAP`（键=Wealthfolio 账户名，值=账本科目），两处保持一致即可。

### A3. 录入持仓（以 2026-09-10 期初为准）

- 每笔持仓填：标的、数量、**成本价/成本额**（与期初 amount 对齐）；基金填份额，CS 饰品填数量与成本。
- 录入完在 Wealthfolio 里核对总成本 ≈ 期初账本 `Assets:投资:*` 的账面金额。

### A4. 每季末回写（我可以代跑，但需要你导出 CSV）

1. Wealthfolio 里导出 holdings CSV，放到 `raw/`（文件名随意）。
2. 先干跑看差异与警告：

```bash
venv/Scripts/python src/sync_fair_value.py raw/<holdings>.csv --date <季末日>
```

3. 确认无误后写入（写后自动 `check` + 自动刷新 Paisa include）：

```bash
venv/Scripts/python src/sync_fair_value.py raw/<holdings>.csv --date <季末日> --write
vendor/paisa/paisa.exe update --config paisa_test/paisa.yaml
venv/Scripts/python scripts/reconcile-check.py     # 全绿才算完成
```

> CSV 必填字段（不符会直接报错，不会猜）：`account_name, symbol_name, market_value, cost_basis`。
> 未映射的账户会警告并跳过——看到警告说明 Wealthfolio 账户名和 `ACCOUNT_MAP` 不一致。

## B. 银行账单（P3-2：银行卡脱离半追踪）

### B1. 导出

在各银行 App 里导出「交易明细/流水」，建议一次导出到当前月，放到 `收件箱\账单\` 或用软件
「初始化 → ① 上传账单」直接多选上传（csv/xlsx）。

### B2. 现状（重要）

- 已原生支持：**支付宝 CSV、微信 XLSX、花呗 PDF**（自动导入+拆分）。
- **银行已预置**（P7.22）：建行 `ccb`、招行 `cmb`、工行 `icbc` 三家的 provider + 配置 + 独立导入命令，
  用 deg 官方示例账单实测通过（建行 xls 7 笔、招行借记 6 笔/信用卡 7 笔、工行借记 12 笔/信用卡 10 笔，全部平衡）。
- 光大银行：deg 没有内置 provider，需要单独转换（把你的导出样例发我，我写一个转换器或规则）。
- 银行配置默认**全部落 FIXME**（不猜科目）；第一次导入后按冒烟报告补 `config/<bank>.yaml` 规则。

### B3. 接入步骤（现在就能做）

1. 各银行 App 导出交易明细，放到 `raw/`，建议文件名带行名方便辨认（如 `建行-交易明细.xls`、`招行-储蓄卡.csv`）。
2. **先干跑**（只写 `.planning/`，不动正式账本）：

```bash
venv/Scripts/python src/import_bank.py --bank ccb --dry-run "raw/建行-交易明细.xls"
venv/Scripts/python src/import_bank.py --bank cmb --dry-run "raw/招行-储蓄卡.csv"
venv/Scripts/python src/import_bank.py --bank icbc --dry-run "raw/工行-借记卡.csv"
```

3. 看笔数与"平衡 ✅"，然后正式导入（自动刷新 Paisa include + 跑 check）：

```bash
venv/Scripts/python src/import_bank.py --bank ccb "raw/建行-交易明细.xls"
vendor/paisa/paisa.exe update --config paisa_test/paisa.yaml
venv/Scripts/python scripts/reconcile-check.py     # 全绿才算完成
```

4. 首次导入后把高频商户补进 `config/<bank>.yaml` 的 rules（deg 匹配字段 `peer/item/type/method`，
   后命中覆盖先命中），下次导入就自动分类。

> 说明：脚本会自动带上 `tools/zoneinfo.zip`（Windows 缺 tzdata，招行信用卡解析时区会用到），
> 无需手工设置；同一批文件重名时输出自动加序号。

## C. 做完之后的自检

```bash
venv/Scripts/python src/finance.py check            # 账本平衡
venv/Scripts/python scripts/reconcile-check.py      # 恒等/勾稽/跨源全绿
python scripts/e2e-sweep.py --base-url http://localhost:7500   # UI 31 路由 0 失败
```

三项全绿 → P3-1/P3-2 关闭，26 项清单全部完成。
