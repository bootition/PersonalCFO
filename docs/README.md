---
title: 文档地图与生命周期规则
status: approved
last_reviewed: 2026-09-06
---

# docs/ 文档地图

> 读法：任何任务开始 → 先读 `STATUS.md`（当前状态唯一权威）→ 本文件（找文档）→ 任务相关文档。

## 布局（Diátaxis 四象限 + 归档）

| 目录 | 干什么 | 谁写 | 生命周期 |
|---|---|---|---|
| `STATUS.md` | 当前状态唯一权威（裁决/缺口/进行中） | 每次状态变化必更新 | 永不过期，持续重写 |
| `decisions/` | 决策记录（ADR）：架构与规格的唯一有效结论 | 决策变更时 | `approved` ↔ `superseded` |
| `contracts/` | 文件契约：journal/YAML/CSV/PDF 咬合点格式 | 实测后更新 | `approved`，随实测修订 |
| `reports/` | 红队审查、阶段验收、专题分析报告（`NN_主题_YYYY-MM-DD.md`） | 每阶段红队审查必出 | 只增不改；被取代标 `superseded` |
| `runbooks/` | 操作手册（月度 SOP、环境重建等可执行步骤） | 流程固化时 | `approved`，随流程修订 |
| `evidence/` | 机器证据（JSON/hash/命令输出），**仅本地，不入 git** | 审查/验收时 | 只增不改 |
| `archive/` | 历史文档（调研档案等），仅追溯 | 归档时 | `historical`/`archived`，禁改正文 |

## 不进 docs/ 的东西

- 会话产物（findings/progress/草稿）→ 根目录 `.planning/<date>-<topic>/`（不入 git）
- 敏感信息（账单路径、PDF 密码）→ `docs/本地敏感信息_DO_NOT_COMMIT.md`（.gitignore 排除，仅本地）
- 账本/账单/财报输出 → `journals/` `raw/` `reports/`（项目根，均不入主仓）

## 生命周期状态（front-matter）

```yaml
---
title: 文档标题
status: draft | approved | superseded | historical | archived
last_reviewed: YYYY-MM-DD
superseded_by: <仅 superseded 时必填，指向新文档>
---
```

- 引用任何 docs/ 文档前，先确认其 `status`：`superseded`/`historical`/`archived` 仅作追溯，**禁止**作为当前结论依据。
- 修改归档/历史文档正文是禁止的；只允许改 front-matter 状态字段。
- 校验：`pwsh -File scripts/validate-frontmatter.ps1 -DocsRoot docs -FailOnError`

## 敏感内容红线

写入 git 的文档只含**聚合指标**（计数、比率、匹配率）；账户余额、交易明细、卡号、身份证号等一律不得出现在 `docs/` 任何入库文件中（含 reports/、contracts/）。
