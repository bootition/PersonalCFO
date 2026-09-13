---
title: 导入规则：怎么写、怎么分层（公共模板 + 私人覆盖）
status: approved
last_reviewed: 2026-09-13
---

# 导入规则

PersonalCFO 用 [double-entry-generator](https://github.com/deb-sig/double-entry-generator)
（下称 deg）把账单翻译成 hledger journal。规则写在 YAML 里。

```
raw/支付宝交易明细.csv ──deg(config/alipay.yaml + config/alipay.local.yaml)──> journals/import-alipay-*.journal
```

## 一、规则分层（重要）

deg 的 `--config` **只接受单个文件**（没有叠加选项），但"可以公开的规则模板"与
"含真实对手方名称的私人规则"必须分开 —— 否则你的家人姓名、常用商户就会进公开仓库。

因此本项目把规则拆成两层，由 `src/import_rules.py` 在导入时合成：

| 文件 | 是否入库 | 内容 |
|---|---|---|
| `config/alipay.yaml` | ✅ 入库 | 公共模板：通用规则（退款/关闭丢弃、支付方式、平台名、科目映射） |
| `config/alipay.local.yaml` | ❌ **永不入库** | 私人规则：真实对手方名称、你自己命名的账户、个人定性结论 |
| `config/.merged-alipay.yaml` | ❌ 自动生成 | 上面两者的合成结果，实际交给 deg |

**合成语义**：私人规则一律**追加在公共规则之后**。
deg 的规则引擎是「按顺序逐条评估、命中即赋值、**后命中覆盖先命中**」，
所以效果与"直接写在公共文件末尾"完全一致 —— 上游公共规则升级不会覆盖你的私人规则。

```bash
# 查看合成结果（不会写任何账本）
venv/Scripts/python.exe src/import_rules.py --check
venv/Scripts/python.exe src/import_rules.py alipay --show
```

支持的后端：`alipay`（支付宝）、`wechat`（微信）、`ccb`（建行）、`cmb`（招行）、`icbc`（工行）。

> **升级提示**：本项目升级时只会替换公共模板 `config/<platform>.yaml`，
> 你的 `*.local.yaml` 不受影响，导入结果保持不变。

## 二、私人规则怎么写

复制一份公共模板里你最像的规则，写成 `config/alipay.local.yaml`：

```yaml
alipay:
  rules:
    # 例：某个平台/商户，指定到你自己的科目
    - peer: <对手方名称关键字>
      targetAccount: Expenses:书籍学习

    # 例：限定方向的收入规则（防止转出被误判）
    - type: 收入
      peer: <家人称呼>
      targetAccount: Income:生活费

    # 例：某类固定充值
    - item: 充值-普通充值
      targetAccount: Expenses:日常三餐
```

字段含义（deg 语义）：

| 字段 | 说明 |
|---|---|
| `peer` | 交易对手方名称，**包含匹配** |
| `item` | 商品/交易说明，**包含匹配** |
| `type` | `收入` / `支出` / `不计收支` |
| `method` | 支付方式 |
| `category` | 账单自带的分类 |
| `status` | 交易状态 |
| `targetAccount` | 支出→借方；收入→贷方来源（通常写 `Income:*`） |
| `methodAccount` | 支出→贷方；收入→借方 |
| `ignore: true` | 丢弃该笔（用于状态过滤） |

**规则顺序**：宽规则在前、具体规则在后。写在自己文件里的规则天然在最后，
所以会覆盖公共模板 —— 这正是你要的效果。

## 三、从 FIXME 队列迭代

**没被任何规则命中的交易会落到 `Expenses:FIXME` / `Assets:FIXME`** ——
这不是 bug，是设计特性：它就是你的"待定性队列"。

```bash
# 看当前 FIXME 规模与分布
venv/Scripts/python.exe src/journal_stats.py journals/import-*.journal

# 逐笔查看
tools/hledger-bin/hledger.exe -f journals/import-alipay-*.journal register FIXME

# 按对手方聚合（找出该补哪条规则）
tools/hledger-bin/hledger.exe -f journals/import-alipay-*.journal register FIXME --layout=bare
```

把高频的对手方补进 `config/<platform>.local.yaml` → 重新 `import` → FIXME 收敛。

> 目标：金额占比 < 5%。`journal_stats.py` 会在超阈值时打 ⚠️。

## 四、重导是幂等的

原始账单是唯一事实源，规则改动后**重新导入即可**：

```bash
venv/Scripts/python.exe src/finance.py import
```

生成物 `journals/import-*.journal` 会被覆盖重建（deg 默认非 append 模式，已实测笔数不会翻倍）。
所以"改错规则"没有风险：改回来、重跑就行 —— 这也是本方案把账本做成纯文本的核心理由。

**不要手改 `journals/import-*.journal`** —— 下次导入会覆盖掉。要修正就改规则或写冲销分录。

## 五、银行账单

三家国内银行已预置 provider，按文件名关键字自动路由：

```bash
# 把导出文件丢进 raw/，然后
venv/Scripts/python.exe src/finance.py import
```

| 银行 | 文件名需包含 | 配置文件 |
|---|---|---|
| 建设银行 | `建行` 或 `ccb` | `config/ccb.yaml` |
| 招商银行 | `招行` / `招商银行` / `cmb` | `config/cmb.yaml` |
| 工商银行 | `工行` / `工商银行` / `icbc` | `config/icbc.yaml` |

三家默认**全部落 `Expenses:FIXME`**（不猜科目），首次导入后按 FIXME 报告补规则。
光大银行（`ceb`）当前无 provider，需先手工转换，见 `docs/runbooks/04_Wealthfolio与银行接入.md`。

## 六、别把敏感值写进公共文件

写完规则先跑一次门禁：

```bash
python scripts/scan-pii.py
```

它会把真实人名/金额/本机路径拦下来。想了解更多见 `docs/privacy.md`。
