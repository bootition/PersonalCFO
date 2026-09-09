---
title: P6 多文件上传 + Wealthfolio 风格侧边栏红队审查报告
status: draft
last_reviewed: 2026-09-09
---

# P6 多文件上传 + Wealthfolio 侧边栏红队审查报告

> 背景：用户对 P5 改造有反馈——上传只能传一份账单（实际可多传但交互差），UI 仍是 Paisa 方块卡片不像 Wealthfolio 风格。
> 提交 fork 49de1fe（Navbar 重写为左侧栏 + /init 上传重做拖拽/追加/chips）。
> 当前状态：实现与自测完成，**红队审查中**（通过后翻 approved）。

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

## 3. 红队审查

- 待回填：逐项结论、P0/P1/P2、终审结论。
