---
title: 项目当前状态（单一真相源）
status: approved
last_reviewed: 2026-09-06
---

# 项目当前状态（Single Source of Truth）

> **本文件是项目当前状态的唯一权威来源。** 任何建议、结论、验收判断必须以此为准；
> `archive/` 中的历史报告只作追溯证据，不构成当前结论。
> 修改任何代码/数据/文档后，如影响状态，必须同步更新本文件。

- **最后更新**：2026-09-06
- **更新人**：P0 验收 + 文档/Git 治理基线建立

## 当前裁决（Verdict）

| 层面 | 状态 | 依据 |
|---|---|---|
| 架构总纲 | ✅ 已定稿：hledger 管账、deg 管导入、Wealthfolio 管投资与目标、Paisa Fork 管日常 UI；咬合点是文件契约 | `docs/decisions/01_架构总纲_v3定稿.md`（approved） |
| P0 仓库与环境 | ✅ 完成：主仓干净并与 origin/main 同步；.gitignore 抽查全部命中；venv 重建（pypdf 6.17.0 + pdfplumber 0.11.10）；`finance.py check` exit 0 | `任务计划.md` 执行日志 2026-09-06 |
| 文档/Git 治理基线 | ✅ 建立：Diátaxis 布局 + front-matter 生命周期 + 本文件 + `AGENTS.md`（含红队审查制度与 Git 纪律） | `AGENTS.md`、`docs/README.md` |
| P1 会计核心 | 🔄 进行中：1.1 导入流水线实测中（已发现 deg 规则异常，见缺口 1）；1.2~1.7 待做 | 本文件缺口清单 |

（✅=已通过 🔄=进行中 ⏳=待执行 ⏸=暂缓）

## 各阶段一览

| 阶段 | 状态 | 红队审查报告 |
|---|---|---|
| P0 仓库与环境 | ✅ 完成（2026-09-06） | 随 P1 首份报告追溯复核 |
| P1 会计核心上线 | 🔄 进行中 | 待出 |
| P2 Wealthfolio 接入 | ⏳ | — |
| P3 Paisa Fork | ⏳ | — |
| P4 打磨 | ⏳ | — |
| P1.4 银行全自动导入 | ⏸ 暂缓（用户决定，先半追踪模式） | — |
| 账本私仓 PersonalCFO-ledger | ⏸ 暂缓（本地 git 先用） | — |

## 已知剩余缺口（诚实披露）

1. **deg 支付宝规则疑似大面积失效**：对真实 2017 行账单实测，约 1955/1978 笔支出落 `Expenses:FIXME`，category 类规则（餐饮美食→日常三餐等）未生效；`余额宝-单次转入`（type+item 双条件）却生效。疑似规则覆盖语义与配置注释假设不符，须读 deg 源码（`reference/double-entry-generator`）确认匹配/覆盖算法后再迭代规则（P1.3）。
2. 花呗拆分脚本（P1.2）未写；PDF 样例格式已验证（附录 B）。
3. 期初建账（P1.5）需用户盘点真实余额，未开始。
4. journals/2026.journal 当前为**演示数据**（假数字）；真实历史重导（P1.7）前需将其移出（演示归档，账本 git 保留历史）。
5. Paisa Fork 补丁已改未构建（需先 npm 构建 web 资产）。
6. 银行卡明细未导出，银行卡处于半追踪模式。

## 进行中的工作

- P1.1：账单导入流水线（raw/ 已备料：支付宝 CSV 2017 行、微信 XLSX 349 行、花呗 PDF 17 页）；冒烟测试待随规则语义修正后落地。

## 当前有效文档（Current Truth）

| 文档 | 用途 | 注意 |
|---|---|---|
| `docs/STATUS.md` | 本文件：当前状态唯一权威 | 每次状态变化必须更新 |
| `任务计划.md`（根目录） | 分阶段实施计划与执行日志 | 每完成一条勾一条 |
| `docs/decisions/01_架构总纲_v3定稿.md` | 架构与全部决策（approved） | 变更架构先改此文档 |
| `docs/contracts/01_文件契约.md` | journal/YAML/CSV/PDF 咬合点格式契约 | 实测为准，改动需同步 |
| `config/科目表草案.md` | 科目表与期初建账模板 | 随真实建账迭代 |
| `AGENTS.md`（根目录） | AI 工作规则：文档引用、红队审查、Git 纪律、隐私红线 | 强制 |

## 维护规则（写文档的人必须遵守）

1. 状态变化时：更新本文件 → 相关报告写 `docs/reports/NN_主题_YYYY-MM-DD.md` → 被取代文档 front-matter 标 `superseded` + `superseded_by`。
2. 报告类文档一律放 `docs/reports/`，命名 `NN_主题_YYYY-MM-DD.md`，带 front-matter（`status: approved`）。
3. 会话产物（中间分析、草稿）只放 `.planning/`（不入 git）；机器证据（JSON/命令输出）只放 `docs/evidence/`（不入 git）。
4. **报告与证据只含聚合指标（计数、比率、匹配率），禁止写入账户余额、交易明细、卡号、身份证等敏感数据**。
5. 给 AI 的建议/结论必须附带依据文档路径与 `last_reviewed` 日期。
6. 文档校验：`pwsh -File scripts/validate-frontmatter.ps1 -DocsRoot docs -FailOnError`（本仓副本，已修 skill 原版两处 bug）
