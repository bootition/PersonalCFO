---
title: 研究报告 · 第二阶段补全（Wealthfolio 与需求补全）
status: superseded
superseded_by: docs/decisions/01_架构总纲_v3定稿.md
last_reviewed: 2026-09-06
---

# 研究报告 · 第二阶段补全：Wealthfolio 深潜 + 需求补全 + 修订架构

- 日期：2026-09-06
- 触发：用户指出 wealthfolio.app 与其需求存在大量重合，要求跳出既有需求、更广地普查 GitHub 财务工具
- 本文件是对 `研究报告_选型结论.md` 的补充与修订；两者冲突时以本文件为准

## 1. Wealthfolio 深潜结论

**结论先行：Wealthfolio 值得引入，但它不能替代复式记账/财报核心；正确位置是"投资仪表盘 + 目标规划层"，与 hledger 分工协作。**

### 1.1 基本事实（2026-09-06 核实）

| 项 | 值 |
|---|---|
| 仓库 | `wealthfolio/wealthfolio`（https://github.com/wealthfolio/wealthfolio） |
| stars / 语言 / license | 8,807 / Rust / AGPL-3.0 |
| 活跃度 | 非常活跃（当日仍有 push；v3.7，桌面+iOS+Docker/web 全平台） |
| 定位 | "The open-source, private portfolio tracker — investments, net worth, spending, and simulations"，local-first，SQLite |
| 商业模式 | 免费；可选付费 Connect（30+ 券商只读同步 + E2EE 多设备同步），不订阅也可用 |

### 1.2 能力清单（从 README/ROADMAP/源码/docs 核实）

- ✅ 投资组合追踪：多账户、多资产类型（股票/ETF/基金/加密/期权/另类资产：房产、车辆、收藏品）
- ✅ 绩效分析：时间加权/资金加权收益、基准对比、历史分析、成本基与税务批次（lots）、拆股
- ✅ 活动管理：BUY/SELL/DIVIDEND/INTEREST/DEPOSIT/WITHDRAWAL/TRANSFER/FEE/TAX/SPLIT/CREDIT/ADJUSTMENT
- ✅ 两种追踪模式：**Transactions 模式**（逐笔交易→精确绩效）与 **Holdings 模式**（只维护当前持仓→净值/配置/浮盈；适合"不想记每笔交易"）
- ✅ 目标规划：目标分配（allocation targets）、再平衡、Save-up 储蓄模拟、退休/FIRE 模拟
- ✅ 负债与净资产：liabilities/debt tracking，net worth 曲线
- ✅ 多币种与汇率、多种市场数据源（Yahoo/Alpha Vantage/MarketData）
- ✅ CSV 导入：通用解析器（分隔符/编码/跳过行/字段映射全可配），**没有支付宝/微信预设模板**
- ✅ 导出：accounts / activities / holdings / goals / portfolio-history（CSV/JSON/SQLite），字段含市值、成本、已实现/未实现盈亏、收益率
- ✅ 插件系统（TypeScript SDK）+ REST API（Axum）+ Docker 自托管 + iOS
- 🟡 Spending/Budgeting：源码已含 `crates/spending`（budget、activity classification、splits、analytics），但 ROADMAP Phase 7 尚未打勾 → **消费/预算模块处于半成品状态，不可作为主预算工具**
- ❌ 不是复式记账：无 journal/voucher、无借贷平衡约束、无 GAAP 三张财报、无结账/结转、无折旧摊销、无应收账款/预付科目
- ❌ 无支付宝/微信账单原生解析（需要自己把 deg 输出转成它的 CSV 模板）

### 1.3 与"访谈 25 条决策"的重合点

重合的是这些（原以为是"财报需求"，实际是"资产视图需求"）：

| 访谈决策 | Wealthfolio 覆盖 | hledger 侧仍需 |
|---|---|---|
| 投资成本+公允价值双列 | ✅ 持仓成本/市值/浮盈/总收益 | 作为财报分录的来源 |
| 资产配置质量（原被划掉） | ✅ 分配目标+再平衡 | 报表披露口径 |
| 目标对照（原被划掉） | ✅ Goals / Save-up / FIRE | 财报 KPI 可选 |
| 现金及等价物/净资产 | ✅ 净值曲线 | 现金流量表 |
| 月度账实核对 | ⚠️ 只覆盖投资账户 | 支付宝/微信/银行卡 |

### 1.4 数据桥设计（避免两本账打架）

原则：**hledger journal 是唯一会计真相；Wealthfolio 是投资分析视图。**

- **hledger → Wealthfolio**：每季度用 `finance.py export-investments` 把 hledger 投资科目余额/持仓生成 Wealthfolio CSV（Holdings 模式），覆盖导入；净值/配置/浮盈自动更新。
- **Wealthfolio → hledger**：季末导出 Wealthfolio `holdings.csv`（含 market_value/cost_basis/unrealized_gain），`finance.py sync-fair-value` 对比 hledger 账上投资成本，生成公允价值调整分录（借/贷 投资科目、贷/借 投资损益:公允价值），保证财报利润表与仪表盘数字一致。
- 若某账户想用 Wealthfolio Transactions 模式做精确绩效（如基金定投），则把交易活动从券商/平台导出后先在 Wealthfolio 录入，再季度汇总回写 hledger 成本与损益；日常流水仍只进 hledger。

## 2. 需求补全清单（此前未讨论、但很可能需要）

### 2.1 新发现的需求与建议

| # | 新需求 | 为什么可能需要 | 工具承接 | 建议 |
|---|---|---|---|---|
| N1 | **银行卡账单自动导入**（建行/工行/招行/光大等） | deg 原生支持 10+ 家中资银行 CSV/XLS；此前"银行卡消费需手工补账"的痛点可被消除，银行余额也能自动对账 | deg（providers: ccb/icbc/cmb/bocom/abc…） | ✅ v1 纳入（把银行卡账单加入导入流水线） |
| N2 | **证券/基金对账单与组合绩效**（时间/资金加权收益、分红、费用、基准对比） | 用户有哈利布朗/攒股收息等投资；此前只记"调拨"，无绩效 | Wealthfolio（Transactions 模式）或 Portfolio Performance；hledger `roi` 做基础版 | ✅ v1 引入 Wealthfolio 作为投资仪表盘 |
| N3 | **资产配置目标与再平衡提醒** | 哈利布朗等策略本就有比例纪律（股票/长债/黄金/现金各 25%） | Wealthfolio allocation targets & rebalancing | ✅ v1（在 Wealthfolio 设目标，偏离提醒） |
| N4 | **市场数据自动更新（价格/汇率）** | 公允价值调整需要可靠市价 | Wealthfolio market-data；Paisa price providers；hledger `P` 记录由脚本抓取 | ✅ v1（Wealthfolio 取价→导出→回写 hledger） |
| N5 | **预算管理（分类预算+滚动结转）** | 控制消费是"财政部"文章的核心动机之一；此前未讨论 | hledger `budget`；Paisa envelope budget（可结转）；Actual Budget | 🟡 二期（先让 hledger 财报跑顺；Paisa 已内置） |
| N6 | **定期账单/订阅/还款日历** | 房租、话费、花呗还款日、订阅容易漏 | Paisa recurring + calendar；hledger `~` periodic | ✅ v1 用 hledger 定期规则生成计提；UI 日历二期 |
| N7 | **现金流预测（未来 6-12 个月）与应急金覆盖月数** | 权责发生制报表是"过去"，现金流预测是"未来" | hledger `--forecast` + balance assertions；Paisa recurring | ✅ v1（finance.py 加 forecast 报表） |
| N8 | **大额目标与退休/FIRE 模拟** | 攒钱目标、提前退休测算 | Wealthfolio goals / save-up / FIRE；Paisa goals+retirement | 🟡 二期（目标储蓄此前被用户"暂不纳入"，保留开口） |
| N9 | **房贷/车贷/分期摊还计算与提前还款模拟** | 学生阶段可能暂无，但毕业后高频 | full-fledged-hledger mortgage 章节；Paisa sheets（EMI 计算） | 🟡 按需（真发生负债时启用，科目已预留） |
| N10 | **税务参考（个税、经营所得、资本利得）** | 闲鱼副业收入、基金赎回、年终奖个税 | full-fledged-hledger tax 章节；fava_investor TLH（美股税损收割，国内不适用） | 🟡 年度汇算时启用 |
| N11 | **日常 Web UI（无需天天敲命令行）** | 现有工具是 Web；纯 CLI 体验倒退 | Paisa（ledger_cli: hledger，Web UI，编辑器/图表/预算/目标）⚠️ v0.7.6 有一个 commodity-style 参数 bug，补丁 1 行，需重编译 web 资产；或等上游修复 | ✅ v1 用 Paisa 做日常界面（先修 bug 或改用英文 commodity style 绕开） |
| N12 | **Obsidian 集成** | 用户主力 Obsidian；此前未选 Markdown 导出 | ledger-obsidian 插件；或 finance.py 直接生成 Markdown 财报 | 🟡 二期（比 PDF 更易归档；建议重新考虑） |
| N13 | **手机查看/录入** | 对账时可能在手机上查余额 | Wealthfolio iOS；Paisa Web（手机浏览器）；hledger-web | 🟡 二期（本地 tailscale 访问） |
| N14 | **AI 辅助分类（本地模型，不上云）** | 现有 73 条规则 + FIXME 队列仍需人工；BERT 本地模型可预分类 | Beancount-Trans 的 BERT/模板体系（MIT，可抄）；Wealthfolio AI addon（Ollama 本地） | 🟡 二期（先收敛规则；隐私优先） |
| N15 | **加密备份/多设备同步** | 账本含敏感信息 | git 私库；Wealthfolio Connect E2EE（可选付费）；或 age/gpg 加密后同步 | 🟡 按需（本地为主，至少 git 私库） |
| N16 | **数据可视化（净值曲线/配置饼图/桑基图）** | 财报是表格；看图更有感觉 | Wealthfolio（投资）、Paisa（图表）、hledger-web | ✅ v1 由 Wealthfolio+Paisa 免费获得 |

### 2.2 明确"仍不做"的项（防止范围膨胀）

- 多人/家庭共享账本、云 SaaS、银行卡 API 自动抓取（保持本地+导出文件导入）、AI 全自动记账（只做预分类建议）、企业级模块（发票/应收应付/库存，来自 Akaunting/django-ledger 的那部分）。

## 3. 修订后的目标架构（分层）

```
原始账单（支付宝/微信/银行/券商，本地）
        │ deg translate（YAML 规则）
        ▼
hledger journals（UTF-8 纯文本，git 版本化 = 唯一会计真相）
        │
        ├── finance.py（薄壳）
        │     ├─ 五张财报：BS / IS / CF / 含权益BS / 权益变动（季度累计，Q1/H1/Q3/AN）
        │     ├─ 结账/反结账（close --retain + 快照）
        │     ├─ 预测报表（--forecast：工资计提、折旧、摊销、现金流预测）
        │     ├─ HTML→Edge PDF / CSV / （二期 Markdown→Obsidian）
        │     └─ 月度账实核对清单（账面余额 vs 手工录入实际余额）
        │
        ├── Paisa Web（ledger_cli: hledger，日常 UI）
        │     └─ 预算、目标、账单日历、编辑器、图表、查询
        │
        └── Wealthfolio（投资仪表盘，Holdings 模式起步）
              ├─ 组合绩效、资产配置与再平衡、净值曲线、目标/退休模拟
              └─ 季度 holdings.csv ⇄ finance.py 公允价值回写 hledger
```

**分工铁律**：现金/消费/负债/计提/折旧/摊销 → 只记 hledger；投资市值/绩效/配置 → 看 Wealthfolio；预算/目标/账单 → Paisa；三张财报 → hledger 唯一出数。

## 4. 新增候选对比（补齐 GitHub 普查）

| 工具 | 定位 | stars | 与我们的关系 |
|---|---|---|---|
| Wealthfolio | 投资组合+净值+目标/模拟 | 8,807 | **引入：投资仪表盘** |
| Ghostfolio | 自托管财富管理（web） | 9,247 | 备选：不想装桌面应用时替代 Wealthfolio；无消费/预算 |
| Portfolio Performance | Java 桌面组合绩效（TTWROR/IRR 最专业） | 4,060 | 备选：极致绩效分析时用 |
| Paisa | ledger/hledger/beancount 的 Web UI（预算/目标/账单/图表） | 3,206 | **引入：日常 UI 层**（hledger 后端） |
| fava_investor | beancount/fava 投资分析插件（配置/税损/现金拖累） | 182 | 抄素材（若走 beancount 线） |
| ledger-obsidian | Obsidian 内的 PTA | 558 | 二期集成参考 |
| balance-budget | 现代双记 Web（.NET+React，银行导入+inbox） | 4 | 抄"inbox 工作流"参考，不主用 |
| Beancount-Trans | 账单→beancount+BERT 分类+fava | 77 | 抄解析/映射/模板素材（MIT） |
| Sossoldi / Picsou / Finanze | 净值追踪仪表盘 | 1391/505/51 | 不选（与 Wealthfolio 重复且更弱） |
| Actual Budget | 本地预算（envelope） | 28,577 | 不选（预算二期若 Paisa 不够再看） |

## 5. 修订后的总体结论

1. **会计核心不变**：hledger + deg + full-fledged-hledger 工作流（第一阶段的全部实测仍有效）。
2. **新增投资层**：Wealthfolio（Holdings 模式起步，季度与 hledger 双向对账；需要精确绩效的账户再开 Transactions 模式）。你的直觉是对的——它重合的是"资产/投资视图"，不是"会计/财报"。
3. **新增日常 UI 层**：Paisa（hledger 后端）——预算、目标、账单日历、图表几乎免费获得；v0.7.6 有 1 行 commodity-style bug（已定位：`internal/ledger/ledger.go:205`），需重建 web 资产后自编译，或等上游修复。
4. **v1 范围更新**：把"银行卡账单自动导入（deg 银行 providers）"和"投资市值季度回写"提级为 v1；预算/目标/退休模拟为二期。
5. **旧 finance-catch 依然不迁移代码**：它提供的 Web 体验由 Paisa 替代，其需求语义（FIXME=待确认、规则=deg YAML、撤销=重跑导入）已在第一阶段设计里保留。

## 6. 下一步（修订版）

1. 真实账单导入：支付宝 + 微信 + **建设银行/工商银行等银行卡账单**（如能导出）→ deg 规则迭代。
2. 期初建账 + hledger 定期规则（工资/折旧/摊销）+ `--forecast` 现金流预测。
3. 安装 Wealthfolio（Windows），用 Holdings 模式建 4 个投资账户（哈利布朗/攒股收息/虚拟货币/CS饰品），跑通 holdings.csv ↔ finance.py 回写。
4. Paisa：跟踪上游 bug；能跑起来后作为日常 UI（预算二期启用）。
5. 四期财报在真实数据上首跑（2025 与 2026 两年对比），PDF 归档。
