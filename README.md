# PersonalCFO

**把你自己当一家公司来经营**：复式记账、权责发生制、按上市公司节奏出四份个人财报
（一季报/半年报/三季报/年报），投资与目标由 Wealthfolio 子账本承担，日常界面用改造后的 Paisa。

## 一句话架构

```
支付宝/微信/花呗/银行卡账单 ──deg(规则)──> hledger journals（唯一真相，UTF-8+git）
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              finance.py（薄壳）       Paisa Fork（日常 UI）      Wealthfolio（投资/目标）
              四期财报/结账/对账         查账/编辑/账单日历        持仓/净值/再平衡/FIRE
                    ▲                                                   │
                    └────────── 季度 holdings.csv 回写（sync-fair-value）─┘
```

## 目录

| 路径 | 内容 | 入 git？ |
|---|---|---|
| `src/finance.py` | 编排器：import / check / report / close / reopen（后续新增 split-huabei、sync-fair-value、reconcile） | ✅ |
| `config/` | deg 规则（alipay.yaml、wechat.yaml，待补银行）、科目表草案 | ✅ |
| `docs/` | 权威总纲 `研究报告_v3_定稿.md`（含组合原理附录）+ `research/` 调研档案 | ✅ |
| `journals/` | **账本（唯一真相）** | ❌（独立私库 `PersonalCFO-ledger`） |
| `raw/` | 原始账单暂存（敏感） | ❌ |
| `reports/` | 财报输出（含 demo2026 演示包） | ❌ |
| `close/` | 结账快照与结转分录 | ❌ |
| `tools/` | deg / hledger / paisa 二进制（下载方式见 `tools/README.md`） | ❌ |
| `vendor/paisa` | Paisa Fork 工作副本（含 1 行 bug 补丁） | ❌（后续单独建 fork 仓库） |
| `reference/` | 调研期克隆的开源源码（hledger/deg/fava/django-ledger 等） | ❌ |
| `archive/` | 调研期实验产物 | ❌ |

## 快速开始

```bash
# 校验账本平衡
python src/finance.py check

# 生成 2026 四期财报（输出到 reports/2026/，含 PDF）
python src/finance.py report 2026

# 结账 / 反结账
python src/finance.py close 2026 Q1
python src/finance.py reopen 2026 Q1
```

## 实施

详见根目录 **`任务计划.md`**（分阶段、每阶段验收标准、命令速查、风险清单）。
权威决策见 `docs/研究报告_v3_定稿.md`。

## 仓库

- 主仓（代码/文档/配置）：`github.com/bootition/PersonalCFO`
- 账本私仓（journals，另行创建）：`PersonalCFO-ledger`
