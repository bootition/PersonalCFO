---
title: P7 UI 整页 Wealthfolio 化红队审查报告
status: draft
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

## 3. 红队审查

- 待回填：独立红队 a–k 逐项结论、P0/P1/P2、终审结论（`.planning/redteam/REPORT7.md`）。
