---
title: P6 多文件上传 + Wealthfolio 风格侧边栏红队审查报告
status: approved
last_reviewed: 2026-09-09
---

# P6 多文件上传 + Wealthfolio 侧边栏红队审查报告

> 背景：用户对 P5 改造有反馈——上传只能传一份账单（实际可多传但交互差），UI 仍是 Paisa 方块卡片不像 Wealthfolio 风格。
> 提交 fork 49de1fe（Navbar 重写为左侧栏 + /init 上传重做拖拽/追加/chips）+ bbb30ad（审查期间移动端汉堡修复）。
> 当前状态：红队终审**通过（PASS）**——P1×1 审查期间已修复并复测关闭；P2×3 不阻断，排入后续打磨。

## 1. 实现内容

| 项 | 内容 |
|---|---|
| 上传 UX | /init 步骤①：拖拽区（dashed border，hover 蓝/蓝底）+ 已选文件 tag chips（每项可单独删除）+ 隐藏的多选 file input（点选追加不覆盖已选），支持 csv/xlsx/pdf |
| 侧边栏 | Navbar.svelte 改为 `<aside class="pcfo-sidebar">`：232px 固定左栏（≥1024px）；圆角 6px 导航项、chevron 展开分组、active 态 warm muted bg；logo 头部+底部 ThemeSwitcher/Actions/readonly tag |
| 移动端 | @media (max-width: 1023px) 抽屉式（transform translateX -100%）；汉堡按钮 .pcfo-burger 显示 |
| 主题 | 浅色 #fffcf0 主面 / #f2f0e5 侧栏 + #e6e4d9 悬停；深色侧栏 #1c1b1a + 文本 #cecdc3，主题切换兼容 |
| 上下文控制栏 | 原每页 dateRange/monthPicker/financialYearPicker/maxDepthSelector/recurringIcons 模板完全保留（Navbar.svelte line 300+） |
| paisa.yaml 修复 | 改绝对路径；bat 自愈：findstr 判定 ledger_cli 行，缺失则 echo 重写（`%~dp0` 运行时展开中文字符，bat 文件保持纯 ASCII） |

## 2. 端到端自测（实现方）

- 多文件上传：3 文件（alipay csv + alipay csv + 花呗 pdf）一次 POST → HTTP 200，status.imported 全部出现 ✓
- 截图：/init 页面深色 + 浅色主题下侧边栏 232px 显示正常，拖拽区与 chips 渲染正确 ✓
- 控制栏保留（未删 markup，selectedLink/recurringIcons 模板原样存在）
- 红队测试残留已清（保留用户在 13:51 真实上传的真实账本与 journal）

## 3. 红队审查（独立子代理，无实现上下文）

- 审查对象：fork 49de1fe（基线交付）+ bbb30ad（审查期间修复）；主仓 a17abd3。
- 方法：合成数据全链路（paisa_test 独立沙箱，真实 raw/journals 零触碰）；手工 multipart 直发 upload 端点；Playwright 1.59 + Edge headless（1440×900 / 375×800）；源码静态审查。
- 原始报告与证据：`.planning/redteam/REPORT6.md`、`.planning/redteam/round6/`（仅本地，不入库）。

### 验收结论（终审）

| 项 | 结论 | 关键证据（聚合口径） |
|---|---|---|
| a 多文件上传 | PASS | 一次 multipart 3 文件（支付宝 CSV+微信 XLSX+花呗 PDF）→ HTTP 200/ok:true；3 文件落盘、output 全列、imported 2 条、check OK |
| b /init 拖拽/追加 | PASS | 源码 file-drop/multiple/addFiles 追加/removeFile/chips 齐全；浏览器实测点选 2→追加 1（3 chips）→删 1→合成 DragEvent +1 |
| c 侧边栏布局 | PASS | 桌面 aside 实测 232px、主内容右移、圆角/chevron/深浅主题截图；移动 375×800 汉堡可见、抽屉开合正常（bbb30ad 修复后二进制实测） |
| d active/自动展开 | PASS | 5 条路径（现金流/资产/负债/初始化/账本）父组自动 is-open+子项 active；手动 toggle 正常 |
| e 上下文控制栏 | PASS | recurring monthPicker+图例、yearly 2 滑杆、monthly/networth du-tabs 均在渲染 |
| f paisa.yaml 自愈 | PASS | 中文路径下两轮模拟（配置改坏 / 直接删除）bat 均重建 3 行绝对路径配置且 paisa update 成功 |
| g 隐私卫生 | PASS | 主仓敏感路径/大二进制 0 命中；fork P6 两个提交仅改 3 个源文件；真实 13:51 raw 未触碰；测试沙箱与进程已清 |
| h 自由攻击 | PASS | sidebar 无 @html/innerHTML；路径穿越被 basename 拦截；扩展名白名单 400；5 并发全 200；100MB 边界正常 |

### 问题清单

- **P0**：无。
- **P1×1（已关闭）**：49de1fe 把汉堡按钮放在移动端 `translateX(-100%)` 的 aside 内，移动端无导航入口；bbb30ad 将按钮移出 aside（fixed top-left、≤1023px 显示），重建 exe 含修复并实测通过。
- **P2×3（不阻断，排入后续打磨）**：
  1. 组级裸路径 `/cash_flow` 直接访问 404；正常 UI 不导航到裸路径，建议组首页重定向到首个子页。
  2. 上传无显式大小上限（100MB 可传）；建议服务端加 MaxBytesReader 上限 + 友好报错。
  3. 既有 tippy `allowHTML` 对账本注释的 HTML 解析（hover 触发、非 P6 引入），建议改纯文本 tooltip 或消毒。

### 终审结论

**P6 通过。** 全部验收项 PASS；1 项 P1 已在审查期间修复复测关闭；P2×3 为不阻断的后续打磨项，已回写 STATUS 缺口清单。
