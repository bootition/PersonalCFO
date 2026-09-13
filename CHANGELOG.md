# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- `scripts/scan-pii.py`：隐私门禁（通用模式 + 本地专属词表），接入 CI
- `scripts/bootstrap.ps1` / `scripts/start.ps1`：一键环境准备与启动
- `scripts/gen-zoneinfo.py`：生成 Windows 时区库 `tools/zoneinfo.zip`
- `tests/`：核心纯函数单元测试（金额解析 / journal 解析 / 规则合成 / 备份加密 / 门禁自身）
- `docs/getting-started.md`、`docs/troubleshooting.md`、`docs/import-rules.md`、`docs/privacy.md`
- `LICENSE`（AGPL-3.0-or-later）、`THIRD-PARTY-NOTICES.md`、`SECURITY.md`、`CONTRIBUTING.md`
- **导入规则分层**：`config/<平台>.yaml`（公共模板）+ `config/<平台>.local.yaml`（私人，不入库），
  由 `src/import_rules.py` 合成；导入结果与单文件写法逐字节一致

### 修复
- **报表期次门禁**：期末早于建账日的期次不再静默产出无意义数字（此前 2026 一季报/半年报
  会把未建账的净流量当成资产负债表，出现"净资产为负"）；新增 `--allow-pre-opening` 显式放行
- **`backup --keep 0`** 不再删掉刚生成的备份（此前会全部删光还打印"✅ 备份完成"）
- **`backup verify/restore`** 缺密钥时不再凭空生成新密钥（会把"密钥丢失"伪装成"密码错误"）
- **控制台编码**：全部入口脚本统一 UTF-8 兜底；修复管道/重定向下
  `backup verify`、`e2e-sweep`、`reconcile-check`、`import_bank` 抛 `UnicodeEncodeError`
- **全角数字**：Python 与 Go 两层统一归一化，不再出现"Go 拒绝、Python 接受"
- **`/init` 静默丢数据**：非法自定义科目改为逐行标红 + 中文原因 + 阻止提交
- **`import_bank`**：不再用 `all(生成器)` 短路导致其余文件被静默跳过；写后校验失败会回滚
- **`split_huabei`**：改写账本后立即自校验，失败自动从备份回滚
- **`reset_init`**：修正"lossless"的错误声明（它会真删本地配置）；修正 `taskkill //IM` →
  `/IM`（原写法在原生 Python 下必然失败且被静默吞掉）
- **换机可用性**：`PCFO_ROOT` 改为自动探测（此前硬编码作者本机路径，换机器 `/init` 与 `/cfo` 全废）
- **界面**：修复上游印度默认值（`en-IN`/`INR`/4 月财年 → `zh-CN`/`CNY`/1 月）；
  侧栏恢复「总览」入口、移除点进去被告知"不适用"的死链与 INR 专属税务组
- **PDF**：浏览器路径改为多候选探测（此前只写 32 位 Edge 路径，64 位机器静默跳过 PDF）
- **数据隔离**：`journals/` 补 `.gitignore`（`bak/` 不入账本仓）；
  raw 账单快照改到 `backups/raw-bak/`，不再放进账本仓
- **字段级错误样式**：`/init` 表单错误输入框描红

### 安全
- **历史重写**：清除全部提交中的个人数据（人名/机构名/账户别名/本机路径/真实金额/真实邮箱）
- **许可证**：主仓从"无许可证"改为 AGPL-3.0-or-later；补第三方组件声明
- `PersonalCFO-paisa`（fork 源码）必须公开以满足 AGPL §6；界面二进制改为**干净树**构建
  （`vcs.modified=false`），对应源码可复现

## [0.1.0] - 待发布

首个公开版本。在此之前项目处于私有开发阶段（62 个提交，2026-09-06 ~ 2026-09-13）。
