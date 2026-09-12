---
title: 项目当前状态（单一真相源）
status: approved
last_reviewed: 2026-09-09
---

# 项目当前状态（Single Source of Truth）

> **本文件是项目当前状态的唯一权威来源。** 任何建议、结论、验收判断必须以此为准；
> `archive/` 中的历史报告只作追溯证据，不构成当前结论。
> 修改任何代码/数据/文档后，如影响状态，必须同步更新本文件。

- **最后更新**：2026-09-09
- **更新人**：P6（多文件上传 + Wealthfolio 侧边栏）红队终审 PASS，阶段收官

## 当前裁决（Verdict）

| 层面 | 状态 | 依据 |
|---|---|---|
| 架构总纲 | ✅ 已定稿：hledger 管账、deg 管导入、Wealthfolio 管投资与目标、Paisa Fork 管日常 UI；咬合点是文件契约 | `docs/decisions/01_架构总纲_v3定稿.md`（approved） |
| P0 仓库与环境 | ✅ 完成：主仓干净并与 origin/main 同步；.gitignore 抽查全部命中；venv 重建（pypdf 6.17.0 + pdfplumber 0.11.10）；`finance.py check` exit 0 | `任务计划.md` 执行日志 2026-09-06 |
| 文档/Git 治理基线 | ✅ 建立：Diátaxis 布局 + front-matter 生命周期 + 本文件 + `AGENTS.md`（含红队审查制度与 Git 纪律） | `AGENTS.md`、`docs/README.md` |
| P1 会计核心 | ✅ 1.1/1.2/1.3 完成（红队复审通过：献祭行防吞行、精确归因未解释=0、收益发放方向矫正、花呗匹配率 97.36%、FIXME 双口径）；1.7 历史重导+四期五件套首跑完成（2025/2026 跨年衔接，权益变动表恒等式=0.00）——1.4 暂缓；1.5/1.6 生成器就绪待用户填数 | `docs/reports/01_P1.1-1.3_红队审查_2026-09-06.md`、`docs/contracts/01_文件契约.md` |

（✅=已通过 🔄=进行中 ⏳=待执行 ⏸=暂缓）

## 各阶段一览

| 阶段 | 状态 | 红队审查报告 |
|---|---|---|
| P0 仓库与环境 | ✅ 完成（2026-09-06） | 随 P1 首份报告追溯复核 |
| P1 会计核心上线 | ✅ 1.1-1.6 完成（1.4 暂缓；1.7 重导+五件套完成；全自洽复核待 1.5 期初建账；2026-09-08 软件自引导改造后 P1.5/1.6 改由 UI 完成） | `docs/reports/01_P1.1-1.3_红队审查_2026-09-06.md` |
| P2 Wealthfolio 接入 | 🔄 2.3 ✅（红队终审通过，报告 03）；2.1/2.2 待用户安装录入 | `docs/reports/03_P2.3+P4_红队审查_2026-09-07.md` |
| P3 Paisa Fork | ✅ 完成（红队三轮审查终验通过：构建/编码修复/中文化 36 标签/Flexoki 浅深主题/CFO 入口/预算占位/prebuild 双清 50.5MB；两轮"假验证"教训已记录） | `docs/reports/02_P3_PaisaFork_红队审查_2026-09-07.md` |
| P4 打磨 | ✅ 4.1/4.2/4.3 完成（红队终审通过，报告 03）；4.4 待观察期 | `docs/reports/03_P2.3+P4_红队审查_2026-09-07.md` |
| **P5 软件自引导改造**（2026-09-08） | ✅ 完成：数据清空+初始化向导四步+月度同入口；红队一审（P1×1/P2×7）→ 修复 → 终审**通过（有条件，条件已补修）**，审查关闭 | `docs/reports/04_P5_自引导改造红队审查_2026-09-08.md` |
| **P6 多文件上传 + Wealthfolio 侧边栏**（2026-09-09） | ✅ 完成：/init 拖拽+多选追加+chips+一次多文件上传；232px 左侧栏（桌面/移动抽屉/深浅主题）；paisa.yaml 绝对路径+bat 自愈。红队终审 **PASS**（P1×1 审查期间已修复复测：移动端汉堡移出 aside；P2×3 不阻断已回写缺口） | `docs/reports/05_P6_多文件上传_Wealthfolio侧边栏红队审查_2026-09-09.md` |
| **P7 UI 整页 Wealthfolio 化**（2026-09-09） | ✅ 完成：Flexoki 完整 8 色 accent 50–950 令牌；图表去整张 svg 黑底（只注入 defs）；/init 四步向导与 /cfo 工具页重做；组件皮肤 paper+0.75rem+hairline；深浅色兜底实测正确。红队一审**不通过（有条件：status() 编码路径 P1）→ 已补修复测 → 复审关闭，P7 通过**（P1×2 关闭；P2×4 不阻断已回写缺口） | `docs/reports/06_P7_UI整页Wealthfolio化红队审查_2026-09-09.md`（approved） |
| **P7.1 用户反馈修复**（2026-09-09） | ✅ 完成：默认纸面浅色（不再跟随系统深色，旧偏好一次性重置）；空账本首页删英文/Setup Demo，改单一「开始初始化」CTA；/init 四步改横向分段控件（去掉平行圆点）。Edge headless 实测 body #fffcf0、无 console 错、svelte-check 0 错 | fork `4401bc2`（本地） |
| **P7.2 期初统计重做**（2026-09-09） | ✅ 完成：①上传成功后自动跳第②步；②货币科目从账单自动推导（只列现金/银行/负债，不再写死用户特有科目）；③投资逐项+逐笔买入（日期+数量+单价算成本，可填市值自动把差额进期初调整）；④固定资产逐件追溯历史折旧（期初记净值，自动生成 fixed-assets-recurring.journal 继续按月折）；⑤opening 端点改 JSON 模式（严格校验）。单元+UI 复测通过 | 本轮提交 |
| **P7.3 初始化守卫 + 清空重测**（2026-09-09） | ✅ 完成：主页检查 `/api/pcfo/init/status`——已导入账单但期初未建时**自动跳回 /init**（修复 bat `paisa update` 同步 DB 后误放行主页面）；第④步加「去总览」。运行态已清空（raw/import journal 归档到 journals/bak、paisa.db 删除、all.journal 复位），`finance.py status` 全空。Playwright 验证：空白态留欢迎页、模拟未完成自动跳 /init、去总览按钮存在 | fork `895ac98`（本地） |
| **P7.4 期初表单体验修复**（2026-09-09） | ✅ 完成：科目标签按末段具体化（建行/工行/招行/光大银行卡、支付宝/余额宝余额，不再四个都叫“银行存款”）；建账日期默认今天且可编辑（记不清就填现在的余额，文案说明历史期间口径）；新增「其他科目」自定义行（纸币等电子账单没有的资产）；直接跳第②步也会先拉状态再显示推导科目 | fork `87ba6c2`（本地） |
| **P7.5 守卫跳转崩页修复**（2026-09-10） | ✅ 完成：双击 bat 报 `TypeError: Cannot read properties of null (reading 'parentElement')`——根因是 P7.3 守卫 `await goto("/init")` 后没 `return`，页面卸载后继续跑 d3 图表渲染，`document.getElementById` 得到 null。加 `return` 后实测：真实数据（已导入+期初未建）→ `/` 自动跳 `/init`，0 console/page error；`/init` 亦 0 错。`paisa.exe` 20:58 重建 | fork `0409d2b`（本地） |
| **P7.6 期初录入体验（6 项）**（2026-09-10） | ✅ 完成：①**分批录入**：草稿接口 + 「保存草稿」，下次打开自动恢复；**重新生成时自动合并已有期初**（只填新增项即可，同名科目新值覆盖，折旧规则按资产名合并保留），跨批次不重复记账；②**资产类型自定义**：投资/固定资产类别改输入框 + datalist 建议（含健身器械），不再限死种类；③**信用卡溢缴款**：不再自动转负，欠款填负数、溢缴款填正数（前后端一致）；④**折旧去重**：第③步移除「大件资产」，固定资产统一在第②步登记并自动追溯+续折，建账后购买的不计入期初；⑤**同步直接跳界面**：成功后整页跳转 `/`（该 fork 的 SPA 导航到 `/` 会卡，改整页跳转），「去总览」/logo 加 `data-sveltekit-reload`；⑥草稿 UTF-8 校验。Playwright 六项实测 + 合并单测通过 | fork `af20aa7`（本地） |
| **P7.7 中文化 + 首页仪表盘 + 日期范围 + 空白页治理**（2026-09-10） | ✅ 完成：①**全站中文化约 520 处**（41 个页面 + 25 个组件 + 22 个 `lib/*.ts` 图表/tooltip/图例；dayjs zh-cn + 日期统一 `YYYY-MM-DD`；配置页 schema 标题映射；盈亏图例 key→中文）；②**首页对齐 Wealthfolio**：4 张数值摘要卡（净资产/本月收入/本月支出/本月结余），**彻底移除交易明细**，明细一律进对应页面；③**日期范围**：`/api/config` 返回真实数据最早/最晚日期（过滤 deg 的 1970 Open Balance 献祭交易与 file_name 为空的 forecast posting），图表不再从 1980 年画起（实测 2025-08-03~2026-09-10）；④**空白页治理**：非适用页从导航隐藏（分析/配置/信用卡/目标/导入），周期账单等空状态中文化。残留英文仅为后端 doctor/模板/日志字段与账户名（数据） | fork `8eee3a7` + `ce7b802`（本地） |
| **P7.8 未解决清单 P1 + 机制 + 部分 P2**（2026-09-12） | ✅ 完成：①**P1 硬伤**：全局错误页/登录页中文化；首页新增**净值走势主图**（近1年/近3年/全部区间切换，对齐 Wealthfolio HistoryChart）；8 个不适用页替换为中文说明页（资产配置/分析/信用卡×2/目标×3/导入/表格×2）；②**防再犯机制**：`docs/decisions/02_Paisa到Wealthfolio页面映射.md`（逐页参照物+7 条通用验收标准）、`scripts/e2e-sweep.py`（31 路由真实数据走查，当前 **0 失败**）、`AGENTS.md` 红队必过项加"参照物对比+用户旅程+真实数据回归+移动端"、中文化维护方式沉淀；③**顺带修复**：导航面包屑在隐藏路由崩页（`selectedSubLink` undefined）、d3 默认英文月份（September→中文，d3.timeFormatDefaultLocale）、1970 献祭交易从全部查询过滤（query.Init）、expense/gain 负值 d3 负宽报错、doctor 6 条诊断+详情中文化、日志级别/字段中文、搜索示例改用中文场景。剩余未解决：P2-1 Tabulator locale、P2-4 资产线页面重做、P2-5 财报卡片化、P2-6 移动端复测、P3 用户阻塞项 | fork 待提交（本地） |
| **P7.9 P2-1/P2-6：表格 locale + 移动端复测**（2026-09-12） | ✅ 完成：①Tabulator 内置中文 locale（暂无数据/分页/加载/列筛选）+ placeholder；②移动端 375px 复测：汉堡可见/抽屉开合/body padding 0、向导步骤 2×2 正常；**发现并修复首页横向溢出 828px**（`renderNetworth` 强制最小宽 800，移动端改为自适应 + 首页图表容器 overflow-x-auto），复测首页/净值/向导 scrollWidth 均 375 无溢出；③e2e-sweep 31 路由仍 0 失败 | fork `e0cced2`（本地） |
| **P7.10-P7.11 资产线重做（P2-4 完成）**（2026-09-12） | ✅ 三页全部对齐 Wealthfolio「数值优先」结构：①`/assets/networth`：净资产大数字 hero + 净投资/盈亏/XIRR 指标卡 + 走势图卡片；②`/assets/investment`：最新财年净投资/净收入/净支出/储蓄率 4 卡 + 月度投资卡片 + 财年时间线/年度概览卡片；③`/assets/gain`：总盈亏（带色）/累计投入/累计转出/当前市值 4 卡 + 账户盈亏总览卡片 + 盈亏明细卡片。移除旧 LevelItem/BoxLabel 行；实测三页指标卡/图表/无报错，e2e-sweep 31 路由 0 失败 | fork `811801e` + `e9d20bf`（本地） |
| **P7.12 财报页卡片化（P2-5 完成）**（2026-09-12） | ✅ ①利润表：顶部 4 张数值卡（收入/支出/税务·利息/净利润带色，按所选财年聚合），期初·期末·变动条与图表改 `.pcfo-card`，科目矩阵表容器卡片化；②资产余额页：4 张数值卡（持仓市值/累计投入/累计转出/总盈亏）+ 表格卡片；③负债余额页：4 张数值卡（负债余额带色/累计提取/累计已还/累计利息）+ 表格卡片，空状态保留。实测三页各 4 卡、无报错；e2e-sweep 31 路由 0 失败 | fork `4897759`（本地） |
| **P7.13 deg 微信吞行 + 退款 23 元修正（P3-4 完成）**（2026-09-12） | ✅ ①**微信吞行根因**：deg v2.15.1 微信 XLSX 读取器硬编码跳过前 18 行（16 行元信息 + 第 17 行表头），第一条数据必被吞。修复：`finance.py` 新增 `preprocess_wechat`（openpyxl 在表头后插入献祭行）+ `config/wechat.yaml` L0 `交易关闭 → ignore`；合成 20 行账单实测 **19/20 → 20/20**，献祭行无残留。②**部分退款修正**：2025-10-18 微信「孔夫子旧书网」原单 239.96、状态"已退款(¥23.00)"按全额入账 → 新增 `journals/adjust-wechat-refund-20251018.journal`（Expenses:书籍学习 −23 / Assets:现金:微信 +23）；`finance.py check` 平衡、includes 已刷新、`paisa update` 已入 DB、账本仓提交 `2163e6f` | main `ab9b5ad` |
| **P7.14 花呗拆分残余治理（P3-5 完成）**（2026-09-12） | ✅ ①脚本改进：`split_huabei.py` 新增"退款已入账"识别（4 笔不再待人工）、亲情卡/代付 11 笔归类为子账正常、还款交易不再误进"账单无对"、期外还款不再算补录；②从原始账单**重新导入+重跑拆分**（微信首行修复随重导生效：微信 journal 320 → **321 笔**，献祭行无残留）；③残余从 **6+17+4 收敛到 6+5+0**（PDF 侧 6 笔 17.41 元；账单侧 4 美团 70.69 + 0.01）；用户决定先不手工处理（支付宝账单截止日早于花呗账单，待导入最新账单自然匹配）；④账本 `check OK`、`paisa update` 已同步 | main `1db927c`（本地待推） |
| **P7.15 报表自洽复核（P3-6 完成）**（2026-09-12） | ✅ 新增 `scripts/reconcile-check.py`（直读 hledger，不经过 Paisa DB）：①`check balanced ordereddates` 通过；②**14 个月末借贷恒等最大偏差 0.00**；③财年 2025-26 / 2026-27 收入与支出对 `/api/income_statement` 差 **0.00**；④期初分录平衡且 `Equity:期初调整` = −(资产+负债)；⑤FIXME 2 科目、占绝对余额 6.93%（明细在本地 `.planning/reconcile-report.json`）。报告 `docs/reports/07_P7.15报表自洽复核_2026-09-12.md`；本次未改账本数据 | main `73b38f5`（本地待推） |
| **P7.16 月度 SOP 实操（P3-7 完成）**（2026-09-12） | ✅ 按 `runbooks/01` 全链路实操：导入（支付宝 1957/微信 321、未解释 0、花呗 97.36%）→ 自检（reconcile-check 全过）→ 账实核对（**首次运行自动生成 17 科目模板**；以账面当实盘验证 13 科目差异全 +0.00、"无需调账"，随后还原模板）→ include 5==5 + `paisa update` → 账本仓提交 → 财报 4 份 PDF → forecast → **close 2026 H1**（快照+结转分录；结账后 `check balanced` rc=0、恒等 delta −0.0）→ `reopen` 清理（期初在 9/10，Apr-Jun 结账为时过早，验证后回滚）。**修复 `close` 提示命令 bug**（原指向不存在的 `journals/2026.journal`，改为按实际文件列表打印）；SOP 手册更新（章节编号/导入后自检/对账模板/结账自验/首个结账期须晚于期初）。用户阻塞：FIXME 定性、真实余额盘点、Wealthfolio 回写 | main `eb21a50`（本地待推） |
| **P7.17 账本备份方案（P3-8 完成）**（2026-09-12） | ✅ 新增 `scripts/backup.py`：AES-256-GCM 加密归档（PBKDF2 600k）覆盖 journals/raw/reports/close/config/paisa.db/敏感信息文件 + `MANIFEST.json`（逐文件 sha256 + 双仓 git 哈希）；子命令 `backup / verify / restore / list`，默认保留 10 份、自动排除密码文件。**实测**：325 文件 22.2MB → 归档 5.9MB；`verify` 清单与 sha256 全部一致 + 恢复演练 `hledger check balanced` rc=0；错误密码被拒绝；`restore` 成功解出 5 个 journal 与 db/raw；归档不含 `backup_secret.txt`（含 raw 与 db）。新增 `runbooks/03_备份与恢复.md`（三层策略/密码管理/RTO≈5min/恢复流程/演练证据），并接入月度 SOP 步骤 5（提交后 backup+verify；破坏性操作前必须先备份）；`.gitignore` 排除 `backups/` 与 `config/backup_secret.txt` | main `96ece7a` |
| **P7.18 Paisa fork 远程仓库（P3-9 完成）**（2026-09-12） | ✅ 私有仓 `bootition/PersonalCFO-paisa` 建立：①快照分支 `master`（`a7515c4`，对应本地 `vendor/paisa@4897759`，`git archive` 干净树，无构建产物）；②Release `fork-2026-09-12` 上传完整历史 bundle `paisa-fork-20260912.bundle`（6.18MB、31 个提交、`git bundle verify` 通过）；③本地 `upstream` 指向 ananthakumaran/paisa 供升级 diff。**限制披露**：`vendor/paisa/.git` 是浅克隆且 gc 后存在缺失对象，直接 push 会 `index-pack failed`（远端收不到完整包），故走"快照 + bundle"；恢复方法已写入 `runbooks/03` 第 7 节 | main `a34db70` |
| **P7.19 P6 红队三个小缺口收口**（2026-09-12） | ✅ ①**组级裸路径不再 404**：`/cash_flow`→利润表、`/assets`→余额、`/liabilities`→余额、`/expense`→月度、`/ledger`→流水、`/more`→设置（各 `+page.ts` redirect；实测 6/6 跳转正确，隔离端口 7600 验证）；②**上传 200MB 上限**：`http.MaxBytesReader` + 413 中文提示（实测 210MB → HTTP 413，`raw/` 无污染）；③**注释 HTML 转义**：`formatTextAsHtml` 先 `escapeHtml` 再转 `<br/>`，账本注释进 tippy 不再解析 HTML；④`scripts/e2e-sweep.py` 动态忽略编辑器接口返回的账本数据词（文件名/科目/对方），**31 路由 0 失败**；STATUS 缺口 #10–#12 标记已修复 | fork `905b4da`、main 待提交 |
| **P7.20 红队复核整改（P7.8–P7.18）**（2026-09-12） | ✅ 独立红队 7 项：4 PASS、2 FAIL、1 部分 FAIL。**整改**：①`e2e-sweep` 结构化降噪（剔文件名/路径 token、新增大小写敏感 `UI_STRICT` 50 个常用 UI 词不受数据白名单影响、可见路由命中错误页即失败、报告写入 git HEAD+时间戳）；②`reconcile-check` 新增**跨源账户核对**（Paisa API 的 DB 口径 vs hledger 直读 9 个叶子现金/银行/负债科目，0 不一致）+ API 不可用默认判失败（`--allow-no-api` 显式跳过）+ 覆盖度断言；③**fork bundle 修复**：原 bundle `git clone` rc=128（浅克隆缺对象、文档恢复路径不可用）→ 把浅边界变新根、`format-patch`/`am` 重放 31 提交生成 **32 提交合法 bundle**，`bundle verify` + `git clone` 双验收通过，上传 Release `fork-2026-09-12-valid`，**私有仓 `master` 已推送同源历史 `05e9d06`**（并删除含坏 bundle 的旧 Release），runbook 03 §7 改写并写入重建配方；④`backup.py` `--keep` 清理前先提示。报告 `docs/reports/09_P7红队复核_2026-09-12.md`；残余边界已如实披露 | main 待提交（本地） |
| P1.4 银行全自动导入 | ⏸ 暂缓（用户决定，先半追踪模式） | — |
| 账本私仓 PersonalCFO-ledger | ⏸ 暂缓（本地 git 先用） | — |

**P1.7 自洽性说明**：复式记账恒等式 资产=负债+权益+(收入-费用) 对任意时刻成立；报表内 `Net:` 行=累计净利润（未结账前正常现象，非错误）。五件套之权益变动表已显式校验 期末-(期初+净利润+其他变动)=0.00（2025/2026 各期均成立）。计划验收语"资产=负债+权益"将在 1.5 期初建账（权益:期初调整 吸收期初轧差）+ 季末结账后以该形式直接成立。

## 已知剩余缺口（诚实披露）

1. **FIXME 残余 = 用户定性队列**（规则已无能为力，须用户一次性定性）：支付宝金额占比 4.06%/笔数 15.07%，集中在**课程类首付分期、固定充值、家人转账、小额往来**；微信 16.71%/13.75%，集中在**自有账户互转、家人转账收入、红包、AA 小额**。逐笔明细只在本地 `docs/本地待办_DO_NOT_COMMIT.md`（不入库），按组定性后批量处理。
2. 支付宝"蚂蚁财富买入"支付方式缺失行按余额宝扣款入账（L4 猜测层）；闲鱼收入到账方式按余额——两处为推断口径，待用户复核。
3. deg 二进制（d93c79d）与 reference 源码快照（639ea22）版本不一致：analyser 层语义已实测核实，provider 层以二进制实测为准；**deg 吞首行 bug 支付宝 + 微信均已用献祭行止血**（微信 XLSX 读取器硬编码跳过前 18 行 = 16 行元信息 + 第 17 行表头，第一条数据必被吞；已在表头后插献祭行 + L0 `交易关闭` 丢弃，合成账单实测 19/20 → 20/20）。
4. **历史微信首行缺失已通过重新导入修复**（P7.14：`finance.py import` 重跑，微信 journal 320 → 321 笔，献祭行无残留）。
5. 期初建账（P1.5）需用户盘点真实余额：在 Paisa「初始化」第 ② 步填写，自动生成期初分录（暂未开始）。
6. 银行卡明细未导出，银行卡处于半追踪模式。
7. **花呗拆分残余（P7.14 后）**：脚本已自动分类——退款已入账 4/亲情卡·代付 11/期外还款 1 不再误报；剩余 **PDF 侧 6 笔（合计 17.41 元）+ 账单侧 5 笔（4 笔美团 70.69 元 + 0.01 元）**。用户决定：因支付宝账单截止日早于花呗账单，先不手工处理，待导入最新账单后自然匹配（清单在本地 `reports/huabei-split-*.txt`）。
8. forecast 应急金覆盖月数在期初建账（P1.5）前为净流量口径（可能为负），仅作流程演示。
9. Paisa 无 UI 语言 i18n 机制（localization.md 仅数字格式），中文化需直改 Svelte 字符串（已用提交 `ce7b802` 沉淀，上游升级时按文件处理冲突）。
10. ✅ **已修复（P7.19）**（P6 红队 P2-1）组级裸路径 404：`/cash_flow`、`/assets`、`/liabilities`、`/expense`、`/ledger`、`/more` 现在重定向到各自首页（`+page.ts` redirect，实测 6/6）。
11. ✅ **已修复（P7.19）**（P6 红队 P2-2）上传端点加 200MB 上限（`http.MaxBytesReader` + 413 中文提示；实测 210MB 被拒且 raw/ 无污染）。
12. ✅ **已修复（P7.19）**（P6 红队 P2-3）账本注释进 tippy 前先 `escapeHtml`（`formatTextAsHtml`），不再解析用户数据里的 HTML。
13. （P7 红队 P2-1）LegendCard 图例 swatch 仍用 `texture`（14px 色块，非图表整底，无黑底风险）；建议随下一次图表迭代清理。
14. （P7 红队 P2-4，观察项）deg 合成账单吞表头后约 15 行（支付宝已插献祭行、微信未插）；不影响平衡与 UI，上游修复后回归探针。

## 进行中的工作

- 无（P7 已于 2026-09-09 红队终审关闭：一审不通过（status 编码 P1）→ 补修复测通过）。用户下一步：双击 `启动PersonalCFO.bat` 从空白初始态走 `/init` ①②③④；需要人工的待办见 `docs/runbooks/02_用户决策清单.md`。

## 当前有效文档（Current Truth）

| 文档 | 用途 | 注意 |
|---|---|---|
| `docs/STATUS.md` | 本文件：当前状态唯一权威 | 每次状态变化必须更新 |
| `任务计划.md`（根目录） | 分阶段实施计划与执行日志 | 每完成一条勾一条 |
| `docs/decisions/01_架构总纲_v3定稿.md` | 架构与全部决策（approved） | 变更架构先改此文档 |
| `docs/contracts/01_文件契约.md` | journal/YAML/CSV/PDF 咬合点格式契约 | 实测为准，改动需同步 |
| `config/科目表草案.md` | 科目表与期初建账模板 | 随真实建账迭代 |
| `docs/runbooks/01_月度SOP.md` | 月度记账 30 分钟闭环流程 | 流程变更时更新 |
| `docs/runbooks/02_用户决策清单.md` | 需人工参与事项（数据/定性）汇总 | 事项清完后核销 |
| `AGENTS.md`（根目录） | AI 工作规则：文档引用、红队审查、Git 纪律、隐私红线 | 强制 |

## 维护规则（写文档的人必须遵守）

1. 状态变化时：更新本文件 → 相关报告写 `docs/reports/NN_主题_YYYY-MM-DD.md` → 被取代文档 front-matter 标 `superseded` + `superseded_by`。
2. 报告类文档一律放 `docs/reports/`，命名 `NN_主题_YYYY-MM-DD.md`，带 front-matter（`status: approved`）。
3. 会话产物（中间分析、草稿）只放 `.planning/`（不入 git）；机器证据（JSON/命令输出）只放 `docs/evidence/`（不入 git）。
4. **报告与证据只含聚合指标（计数、比率、匹配率），禁止写入账户余额、交易明细、卡号、身份证等敏感数据**。
5. 给 AI 的建议/结论必须附带依据文档路径与 `last_reviewed` 日期。
6. 文档校验：`pwsh -File scripts/validate-frontmatter.ps1 -DocsRoot docs -FailOnError`（本仓副本，已修 skill 原版两处 bug）
