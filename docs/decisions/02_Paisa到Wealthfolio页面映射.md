---
title: Paisa → Wealthfolio 页面映射与验收标准
status: approved
last_reviewed: 2026-09-12
---

# Paisa → Wealthfolio 页面映射与验收标准

> 背景：P7.7 复盘发现，UI 反复返工的根因是"只搬了 Wealthfolio 的色板，没搬它的页面结构"，
> 且没有逐页对照表与验收标准。本文档把 Paisa fork 的每个路由钉到一个参照物上，
> 并规定"做到什么算完成"。**新增/改版任何页面前先查此表；表中没有的页面必须先补一行再动手。**

## 1. 参照物优先级

1. `reference/wealthfolio/apps/frontend/src/pages/**`（Dashboard / net-worth / holdings / income / performance / settings / onboarding）
2. `reference/wealthfolio/apps/frontend/src/components/**`（history-chart、卡片、表格、空状态）
3. Paisa 上游已有实现（组件/机制，如 `setAllowedDateRange`、`SyncRequest`、`ZeroState`、Tabulator locale）——**先复用，不要自写**
4. 都没有时：明确标注「原创设计」，并在红队审查中作为独立风险项

## 2. 页面映射表

| Paisa 路由 | Wealthfolio 参照 | 决策 | 验收标准 |
|---|---|---|---|
| `/` 总览 | `pages/dashboard/dashboard-content.tsx` | ✅ 已重做（P7.7/P7.8） | 大数字摘要 + 净值走势大图（区间切换 1年/3年/全部）+ 账户/支出摘要；**不得出现交易明细**；数值可点入明细页 |
| `/init` 初始化 | `pages/onboarding/**` | ✅ 自研（需标注原创） | 四步中文向导；①上传支持多文件/拖拽/自动跳②；②科目从账单推导 + 分批草稿合并；③工资/房租；④状态总览 + 同步后直接进首页 |
| `/assets/networth` | `pages/net-worth/**` | 🔄 待重做（P2-4） | 大数字 + 走势图 + 区间选择器；日期范围取真实数据 |
| `/assets/investment` `/assets/gain` | `pages/holdings`、`pages/performance` | 🔄 待重做（P2-4） | 数值卡片 + 持仓/收益列表；图例中文；空状态可操作 |
| `/assets/balance` | `pages/dashboard/accounts-summary.tsx` | 🔄 待重做（P2-4） | 账户分组 + 金额 + 占比；无英文表头 |
| `/assets/allocation` | `pages/allocation-targets`（Wealthfolio 承担） | ✅ 隐藏 + 中文说明页（P7.8） | 导航不出现；直达时显示中文迁移说明 |
| `/assets/analysis` | 无（Paisa 印度共同基金功能） | ✅ 隐藏 + 中文说明页 | 同上 |
| `/cash_flow/*` 利润表/月度/年度/周期账单 | `pages/income` | ✅ 中文化完成 | 图表/表头/tooltip 全中文；空状态说明下一步操作 |
| `/expense/*` | `pages/income` 支出维度 | ✅ 中文化完成 | 同上 |
| `/liabilities/*` | `pages/health` 负债视角 | ✅ 中文化完成；信用卡配置页隐藏说明 | 余额/还款/利息可用；数字与账本一致 |
| `/income` | `pages/income` | ✅ 中文化完成 | 收入/净税数值 + 明细入口 |
| `/ledger/posting` `/transaction` `/editor` `/price` | `settings`/数据管理（无直接对照） | ✅ 保留（账本工具） | 中文表头/空状态；编辑器保存提示中文 |
| `/ledger/import` | 无（Paisa CSV 模板） | ✅ 隐藏 + 中文说明（指向 /init） | 导航不出现；直达显示说明 |
| `/more/sheets` | 无直接对照 | ⏳ 待评审（P2-7） | 中文或隐藏 |
| `/more/config` | `pages/settings` | ✅ 中文化（含 schema 标题映射） | 配置项标题中文；核心项（货币/路径/只读）可读 |
| `/more/doctor` `/more/logs` | `pages/health` | ⏳ 待中文化后端文本（P2-2/2-3） | 问题描述与日志级别中文或双语 |
| `/more/goals*` | `pages/dashboard/goals.tsx`（Wealthfolio 承担） | ✅ 隐藏 + 中文说明 | 导航不出现；直达显示迁移说明 |
| `/more/tax/*` `/more/about` | 无 | ⏳ 待评审（P2-7） | tax 仅 INR 入口，保留或隐藏 |
| `/cfo` CFO 工具 | 无对照（自研入口） | ✅ 保留 | 四工具卡中文；执行结果中文/可读 |
| `/login` `/error` | 无 | ✅ 中文化（P7.8） | 全中文，无上游品牌名 |

## 3. 每页通用验收标准（红队必查）

1. **语言**：页面可见文本无英文残留（账户名/对方/商品等用户数据除外）。
2. **不空白**：无数据时必须有中文空状态 + 下一步操作指引；不允许出现 `Oops!/Hurray!/No Data`。
3. **数据真实**：图表 x 轴不早于真实最早记录（deg 的 1970 Open Balance 与 forecast posting 不能进范围）。
4. **数值优先**：列表页/首页先展示聚合数值，明细通过链接展开。
5. **可达性**：导航可见的路由必须能打开且不报错；已隐藏路由直达也不能白屏/报错（中文说明页兜底）。
6. **主题**：默认纸面浅色；深色可切换且对比度可读。
7. **移动端**：375px 宽下导航可开合、主要内容不溢出。

## 4. 机制复用清单（不要再自写）

| 需求 | 应复用 | 备注 |
|---|---|---|
| 日期范围 | Paisa `store.setAllowedDateRange()` + `/api/config` 的真实 date_min/max | 两套已统一为 config 初始化 + 页面按需覆盖 |
| 同步调用 | `SyncRequest{Journal:true}`（editor 同款） | 禁止再发 `{}` |
| 表格本地化 | Tabulator `locale` 选项 | 待补（P2-1） |
| 时间显示 | `dayjs.locale("zh-cn")` + `YYYY-MM-DD` | 已有 |
| 空状态 | `ZeroState.svelte` + 中文文案 | 已有 |

## 5. 中文化改动的维护方式（M-4）

- 中文化是**直接改 Svelte/TS 字符串**（Paisa 无 UI i18n 机制），集中在 fork 提交 `ce7b802`。
- 上游升级时：`git -C vendor/paisa log --oneline --grep i18n` 找到该提交，冲突按文件逐个处理；不要在升级时丢弃中文化。
- 替换记录（old→new、文件清单）在本地 `.planning/l10n/`（不入库）；如需可再生成。
- 后端文本（doctor/模板/日志）尚未中文化，见 P2-2/P2-3。
