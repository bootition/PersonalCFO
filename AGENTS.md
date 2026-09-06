# AGENTS.md — 项目智能体规则

本文件为 AI 助手（opencode/Codex 等）在本仓库工作的强制规则。

## 项目一句话

**PersonalCFO**：把个人当公司来经营的本地财务系统——hledger 复式账本为唯一真相，deg 导入支付宝/微信/花呗/银行卡账单，Wealthfolio 承担投资子账本与目标规划，Paisa（深改 Fork）做统一日常 UI，按上市公司节奏出四期财报（PDF/CSV）。

## 文档规则（强制，防止"读到过期结论"）

### 1. 必读顺序（任何任务开始时）

1. `docs/STATUS.md` — **当前状态唯一权威**，含当前裁决、剩余缺口、进行中工作
2. `docs/README.md` — 文档地图与生命周期规则
3. `任务计划.md`（根目录）— 分阶段实施计划与执行日志
4. 任务相关代码/文档（架构结论以 `docs/decisions/01_架构总纲_v3定稿.md` 为准）

### 2. 文档状态语义（front-matter `status` 字段）

| 状态 | 含义 | 处理 |
|---|---|---|
| `approved` | 当前有效 | 可作结论依据 |
| `superseded` | 已被取代（`superseded_by` 指向新文档） | **禁止**引用为当前结论；仅追溯用 |
| `historical` | 历史决策 | 同上 |
| `archived` / `draft` | 已归档 / 未定稿 | 默认不引用 |

### 3. 禁止行为

- ❌ 引用 `docs/archive/`、`docs/evidence/` 内容作为当前结论依据（证据 ≠ 结论）
- ❌ 把会话产物（findings/progress/草稿）写入 `docs/` —— 一律放 `.planning/<date>-<topic>/`
- ❌ 修改归档/历史文档正文（只可改 front-matter 状态字段）
- ❌ 在入库文件（含 docs/reports/）中写入账户余额、交易明细、卡号、身份证号等敏感数据——只写聚合指标

### 4. 必须行为

- ✅ 给用户建议时标注依据文档路径 + `last_reviewed` 日期
- ✅ 新文档必须带 front-matter（title/status/last_reviewed）
- ✅ 状态变化时：更新 `docs/STATUS.md` → 报告写 `docs/reports/` → 旧文档标 `superseded`
- ✅ 机器证据（JSON/hash/命令输出）只放 `docs/evidence/`（仅本地）
- ✅ 架构/契约变更：先改 `docs/decisions/01` 或 `docs/contracts/01`，再改代码

## 红队审查制度（强制，防"假完成"）

1. **每个阶段（P0/P1/P2/P3/P4，P1 内大项 1.1-1.3 / 1.5-1.7 各算一次）完成后必须红队审查**，通过才算完成。
2. 审查方式：派独立子代理（无实现上下文），只做对抗验证——重跑命令、复算数字、抽查产物，专找假完成（演示数据冒充真实数据、指标口径造假、产物缺失、错误被静默吞掉）。
3. 审查结论写成报告 `docs/reports/NN_主题_YYYY-MM-DD.md`（front-matter `status: approved`），证据放 `docs/evidence/`；发现的问题回写 `docs/STATUS.md` 缺口清单，修复后再复审。
4. **审查不通过的阶段禁止勾选任务计划对应项**；勾选即声明"已通过红队审查"。
5. 报告只含聚合指标，不含敏感明细（红线见下）。

## 隐私红线（最高优先级，不可协商）

- `journals/`、`raw/`、`reports/`、`close/`、花呗 PDF、任何含身份证/卡号内容**永不进主仓库、永不外发**（含 issue/PR/聊天截图/日志贴出）。
- 敏感路径与密码只写在 `docs/本地敏感信息_DO_NOT_COMMIT.md`（.gitignore 排除，仅本地）。
- 提交前必须 `git status` 自查；对外贴输出前先检查是否含敏感字段。

## Git 纪律（强制，防止工作丢失）

### 1. 提交时机

- ✅ **会话结束前**：若工作区有未提交变更，必须提交（默认动作，不等用户明确要求）
- ✅ **里程碑完成时**：每完成一个可独立验证的阶段立即提交
- ✅ 提交前先 `git status`，确认没有误入 journals/ raw/ reports/ tools/ vendor/ reference/ archive/ docs/evidence/ 等被 ignore 的内容
- ❌ 禁止跨主题打包提交；按主题拆分（docs/ feat/ fix/ chore/）

### 2. 提交边界（哪些永不提交）

- 见 `.gitignore`；如发现遗漏，先补 `.gitignore` 而非硬提交。
- `docs/本地敏感信息_DO_NOT_COMMIT.md`、`.planning/`、`docs/evidence/`、`venv/` 永不提交。

### 3. Push 纪律

- ✅ 每个会话的提交完成后**必须 `git push`**（remote：`origin` → `github.com/bootition/PersonalCFO.git`）
- ✅ 推送前 `git fetch` 检查远程是否有新提交，有冲突先解决再推
- ⚠️ **网络失败必须如实告知**：push 失败时**禁止**说"已推送"；必须明确告知「push 失败 + 原因 + 当前状态（提交在本地未上远程）」，并重试直到 `git ls-remote origin` 确认远程已更新

### 4. 提交消息风格

`feat:` / `fix:` / `chore:` / `docs:` / `refactor:` 前缀 + 中文摘要 + 可选要点列表。

### 5. 账本仓库（journals/）

- journals/ 是**独立本地 git 仓库**（远程私库 `PersonalCFO-ledger` 暂缓）；每月度 SOP 收尾时在账本仓提交一次；账本内容永不推送到主仓 remote。

## 常用命令

```bash
venv/Scripts/python src/finance.py check            # 账本平衡校验（hledger 一律走 finance.py，自动 chcp 65001）
venv/Scripts/python src/finance.py import           # 导入 raw/ 账单
venv/Scripts/python src/finance.py report 2026      # 生成四期财报 PDF/CSV
venv/Scripts/python src/finance.py close 2026 Q1    # 结账
pwsh -File scripts/validate-frontmatter.ps1 -DocsRoot docs -FailOnError  # 文档校验（本仓副本，已修 skill 原版两处 bug）
```

## 工作区边界

- `journals/`（独立 git）— 账本唯一真相；`raw/` — 原始账单暂存（敏感）；`reports/` `close/` — 财报与结账快照（均仅本地）
- `.planning/` — 会话计划与进度（AI 私有工作区，永不提交）
- `docs/evidence/` — 证据只增不改（仅本地）
- 账单样本在项目外（`D:\Mr.Q\掌控经济\消费记录`），含敏感财务信息，只做本地分析，不得写入 git 或入库文档
