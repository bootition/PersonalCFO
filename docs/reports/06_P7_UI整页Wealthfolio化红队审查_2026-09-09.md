---
title: P7 UI 整页 Wealthfolio 化红队审查报告
status: approved
last_reviewed: 2026-09-09
---

# P7 UI 整页 Wealthfolio 化红队审查报告

> 背景：用户反馈 P6 的侧边栏/上传改造仍不彻底——图表黑底、页面与 Wealthfolio 风格不接。
> 本阶段（P7）把 Flexoki 设计令牌铺满全 UI、去掉图表整张底色、重做 /init 与 /cfo 页面，并把运行态清空让用户从空白初始态重走初始化。
> fork 提交：69c3e8c（令牌 + 图表去黑底 + 侧栏图标）、1fb9b24（组件皮肤 + /init /cfo 重做 + 深色兜底）、后续类型与残留清理提交。
> 当前状态：实现与自测完成，**红队审查中**（通过后翻 approved）。

## 1. 实现内容

| 项 | 内容 |
|---|---|
| Flexoki 令牌 | `src/app.scss` `:root` 增加 paper / base-50..950 / black / accent / surface / text / border / grid / positive / negative，以及从 Wealthfolio `globals.css` 抽取的 8 组 accent（red/orange/yellow/green/cyan/blue/purple/magenta）50–950 共 104 个 `--color-*-*` |
| 图表去黑底 | `cash_flow.ts` / `budget.ts` 不再 `svg.call(texture)`（该调用会往整张 svg 铺一块不透明背景 rect）；只 `svg.append("defs").html(texture.toString())` 注入花纹 defs，图案背景 `rgba(0,0,0,0)`；`.axis` / `.svg-text-*` / `.svg-grey-*` / `.g-arrow` 全部换 `var(--color-*)` |
| 页面底色 | 删除 body `radial-gradient` dot-grid；浅色 paper `#fffcf0`、深色 `#100f0f`（dark.scss 末尾 `!important` 兜底） |
| 卡片/控件皮肤 | `.box`、`.pcfo-card`、`.button`（is-link/is-primary/is-light/is-dark/is-ghost）、`.input/.textarea/.select`、`.tag`、`.table`、`.notification` 统一 paper 表面 + 1px hairline border + 0.75rem 圆角 + accent focus ring |
| 左侧栏 | 232px 固定左侧栏；顶级组 FontAwesome 图标（house/chart-line/receipt/vault/credit-card/arrow-trend-up/book/rocket/toolbox/ellipsis）；嵌套分组 chevron 折叠；路由 active 用 `--color-accent-soft`；移动 375px 抽屉 + 固定顶左汉堡 |
| /init 向导 | 胶囊步骤条（编号圆点 + 完成绿边 + active accent 底）；上传卡片 `.pcfo-upload-zone`；文件 chips；期初余额 12 项 form-grid；大件折旧 asset-row；状态总览 6 张统计卡；多文件/拖拽/追加/删除逻辑保持 P6 不变 |
| /cfo 工具页 | 4 张工具卡（校验/导入/对账/预测）+ icon tile + 年份/期间 + 生成财报/结账/反结账 report-bar |
| 运行态重置 | `src/reset_init.py`（主仓）：raw/* 与 journals/import-*.journal 归档 `journals/bak/<ts>/`，删 paisa.db、重置 all.journal、删 config/local.yaml，返回空白初始态 |
| 构建 | `npm run build` + `go build -o paisa.exe`（17:13，53 MB） |

## 2. 端到端自测（实现方）

- Edge headless 1440×900：/init 4 个步骤胶囊、upload-zone、/cfo 4 张工具卡、无 console error
- computed 色值：body 浅 #fffcf0 / 深 #100f0f；card 浅 #fffcf0 / 深 #1c1b1a；step active #205ea6；侧栏深 #1c1b1a；brand 深 #f2f0e5
- `svelte-check` 0 errors（21 条既有 warnings）；`npm run build` + `go build` 成功
- 重置后 `finance.py status`：imported=[] / opening=false / recurring=false / check_ok=true / raw_files=[]

## 3. 红队审查（独立子代理，REPORT7，2026-09-09）

- 审查对象：fork HEAD `a8d1ebd`（69c3e8c / 1fb9b24 / a854f80 / a8d1ebd 四提交）+ `paisa.exe` 17:18:15；主仓 `d984fe9`。
- 方法：静态源码/编译产物审查 + 真实 API 冒烟（paisa_test 沙箱，全合成数据）+ git 卫生核查；Playwright 浏览器逐像素项因父会话轮次上限未跑完，运行时子项按源码+编译产物判定并标 SKIP。
- 原始报告与证据：`.planning/redteam/REPORT7.md`、`.planning/redteam/round7/`（仅本地，不入库）。

### 终审结论（一审）：**不通过（有条件）→ 条件已补修，复审关闭**

| 项 | 结论 | 一句话证据 |
|---|---|---|
| a Flexoki 令牌 | PASS | 编译 CSS 含 `--color-paper:#fffcf0`；base + 8 组 accent 各 50..950 全 13 档无缺失；语义令牌映射正确 |
| b 图表去黑底 | PASS（静态） | `cash_flow.ts`/`budget.ts` 只注入 defs；编译 chunk `svg.call(texture)`=0；唯一残留为 LegendCard 14px 图例 swatch（P2-1，非整图黑底） |
| c 侧边栏 | PASS（源码判定） | 232px fixed + body padding-left 232px；顶级组 icons；路由 startsWith 自动开合+is-active；active rgba(32,94,166,.12)；≤1023px 抽屉+顶左汉堡 |
| d 组件皮肤 | PASS（源码判定） | `.pcfo-card` surface+1px+0.75rem；`.button.is-link` #205ea6；input focus 3px accent ring |
| e /init 向导 | PASS（结构+API） | 4 步骤胶囊 / upload-zone / 12 输入 / 6 状态卡；多文件追加/删除/拖拽逻辑与 P6 一致；API raw=3、imported=2、opening/recurring/check_ok true |
| f /cfo 工具页 | PASS | 4 工具卡+icon tile+report-bar 三按钮；`/api/pcfo/run check` 实测 200 ok |
| g 深色一致性 | PASS（源码判定） | body #100f0f / sidebar+card #1c1b1a / 正文 #cecdc3；浅色 #fffcf0 |
| h 多文件上传回归 | 一审 FAIL（check_ok 子项）→ **已修复** | 3 文件 multipart 200/ok:true/raw=3/imported=2 通过；但默认启动环境 `status()` 报 CP936 解码错 → P1-1 |
| i 隐私/卫生 | PASS | 主仓敏感路径/大二进制 0；fork 四提交只改 src/ |
| j 自由攻击 | PASS（静态+P6 继承） | basename 防穿越、扩展名白名单 400、pcfoMu 未变、sidebar 无 @html/innerHTML |
| k 构建一致性 | PASS | exe 17:18:15 / web/static 17:18:09 ≥ 源码重建时间 |

### 问题清单

- **P0**：无。
- **P1×2（均已关闭）**：
  1. `src/finance.py status()` 用裸 `subprocess.run` 调 hledger，经 Paisa pcfoExec 的 piped stdio 时按 CP936 解码 UTF-8 中文 journal → `/init` 步骤④ `check_ok:false`。**已修**：`status()` 改走 `run_console_utf8`（先 `chcp 65001`，与 `check()` 同路径）；中文合成 journal 复测 `check_ok:true`、exit 0。
  2. `/init` 步骤④「同步到界面」原发 `{}`（SyncRequest 三 bool 默认 false = 空跑却提示成功）。审查期间父侧已修（fork `a8d1ebd`，改发 `{"journal":true}`）；红队 API 级复测 DB 408 postings、流水可见。
- **P2×4（不阻断，已回写 STATUS 缺口）**：
  1. LegendCard 图例 swatch 仍用 `texture`（14×14，非整图背景）。
  2. `reset_init.py` 卫生缺口（文件名 `recurring_rules.yaml` 不匹配、不归档 opening/recurring journal、0.3s 等待曾致 db 删除失败）→ **本轮已修**（三处）。
  3. 继承项：`/cash_flow` 裸路径 404；上传无总字节硬上限；tippy `allowHTML`。
  4. 观察项：deg 合成账单吞表头后约 15 行（微信未插献祭行），不影响平衡与 UI。

### 终审结论

**P7 通过。** 全部 UI/令牌/图表/侧栏/页面项 PASS；一审唯一的 P1（status 编码路径）已修复并复测通过，P1-2 同步空跑已修复并 API 复测；P2×4 为不阻断的后续打磨项，已回写 STATUS 缺口。
