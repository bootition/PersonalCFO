<div align="center">

# PersonalCFO

**把你自己当一家公司来经营**

复式记账 · 权责发生制 · 按上市公司节奏出四期个人财报

[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)
![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D4.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)

**所有数据只存在你自己的电脑上：没有账号、没有云端、没有遥测。**

</div>

---

## 这个软件解决什么问题

会记账的人很多，但大多数人记的只是"流水"——这个月花了多少、还剩多少。
**PersonalCFO 换了一个问法：如果我是自己这家公司的 CFO，我会怎么看？**

| 普通记账 App | PersonalCFO |
|---|---|
| 本月收入 / 支出 / 结余 | **资产负债表**：我有多少资产、欠多少、净资产多少 |
| 看流水列表 | **利润表**：钱从哪来、花到哪去、净赚多少 |
| 想知道"钱去哪了" | **现金流量表**：经营 / 投资 / 筹资三口径 |
| 全年一个总账 | **一季报 / 半年报 / 三季报 / 年报**，随便切换 |
| 数据在别人服务器 | **账本是一个纯文本文件，在你自己的硬盘上** |
| 无法自定义 | 收入 / 费用 / 资产 / 负债科目**完全自定义** |

**它不替你理财，它替你把话说清楚。**

## 核心特性

- 🧾 **账单自动导入**：支付宝 CSV、微信 XLSX、花呗加密 PDF、银行明细（建行/招行/工行）→ 复式分录
- 📊 **五张表**：资产负债表 / 利润表 / 现金流量表 / 含权益资产负债表 / 权益变动表，导出 CSV + HTML + **PDF**
- 📅 **定期规则**：工资计提、房租摊销、固定资产按月折旧，自动进预测报表
- 💹 **投资子账本**：与 [Wealthfolio](https://github.com/afadil/wealthfolio) 咬合，季度公允价值回写
- 🔍 **待确认队列**：规则没覆盖的交易自动落到 `FIXME` 科目，规模一目了然，逐步收敛
- 🖥️ **图形界面**：基于 [Paisa](https://github.com/ananthakumaran/paisa) 深度改造的中文界面（本地 Web UI）
- 🔐 **加密备份**：AES-256-GCM，一条命令备份 / 校验 / 恢复
- ✅ **可审计**：账本是纯文本 + git，每次改动都有 commit 可查

## 工作原理

```
支付宝/微信/花呗/银行账单
        │
        │  deg（规则化账单翻译器）
        ▼
   hledger journals  ←── 唯一真相：纯文本、UTF-8、可 git 版本管理
        │
        ├──────────────► finance.py          四期财报（CSV / HTML / PDF）
        │                结账 / 反结账 / 预测 / 账实对账
        │
        └──────────────► Paisa（本项目 fork）  日常查账 / 编辑 / 初始化向导
                          │
                          └◄── 季度 holdings CSV ── Wealthfolio（投资与目标）
```

| 组件 | 角色 | 为什么用它 |
|---|---|---|
| [hledger](https://github.com/simonmichael/hledger) | 会计引擎 | 成熟、快、纯文本，不重复造会计轮子 |
| [double-entry-generator](https://github.com/deb-sig/double-entry-generator) | 账单翻译 | 原生支持支付宝/微信/多家银行 |
| [Paisa](https://github.com/ananthakumaran/paisa) | 日常界面 | 本地 Web UI，已深度中文化 |
| [Wealthfolio](https://github.com/afadil/wealthfolio) | 投资子账本 | 持仓 / 净值 / 再平衡 / FIRE |

## 快速开始（Windows）

### 1. 准备环境（约 5 分钟，只需做一次）

需要先装 [Python 3.11+](https://www.python.org/downloads/windows/)
（安装时**务必勾选 "Add python.exe to PATH"**），然后：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

它会建立虚拟环境、装依赖、下载 hledger 与 deg、生成配置。

> 还需要 `vendor\paisa\paisa.exe`（本项目的界面程序）。获取方式见
> [`tools/README.md`](tools/README.md#paisaexe-从哪来)（Release 下载或自行构建）。

### 2. 启动

双击根目录的 **`启动PersonalCFO.bat`** → 浏览器自动打开 `http://localhost:6500`

### 3. 首次使用：跟着界面走

空账本会显示一个四步向导：

| 步骤 | 做什么 |
|---|---|
| ① 上传账单 | 把支付宝 / 微信 / 花呗 PDF / 银行明细拖进来（可多选） |
| ② 期初余额 | 照手机 App 抄一下各账户当前余额（投资和固定资产可逐项填） |
| ③ 定期规则 | 有工资 / 房租 / 大件就填，没有就跳过 |
| ④ 同步到界面 | 点一下，首页就有数字了 |

> 具体每一步填什么、常见坑，见 **[docs/getting-started.md](docs/getting-started.md)**。

### 4. 出财报

界面里点「CFO 工具 → 生成财报」，或者命令行：

```powershell
venv\Scripts\python.exe src\finance.py report 2026
```

产物在 `reports\2026\`：每期 5 张表 × (CSV + HTML + TXT) + 一份汇总 PDF。

## 常用命令

```powershell
venv\Scripts\python.exe src\finance.py check      # 账本平衡校验
venv\Scripts\python.exe src\finance.py import     # 导入 raw\ 下的账单
venv\Scripts\python.exe src\finance.py status     # 初始化状态总览（JSON）
venv\Scripts\python.exe src\finance.py report 2026             # 生成四期财报
venv\Scripts\python.exe src\finance.py forecast --months 12    # 现金流预测
venv\Scripts\python.exe src\finance.py close 2026 Q3           # 结账
venv\Scripts\python.exe src\finance.py reopen 2026 Q3          # 反结账
python scripts\backup.py backup                    # 加密备份
python scripts\scan-pii.py                         # 提交前隐私门禁
```

## 隐私

| 数据 | 位置 | 会进 git 吗 |
|---|---|---|
| 账本 | `journals/` | ❌ |
| 原始账单（含姓名、账号） | `raw/` | ❌ |
| 财报 | `reports/` `close/` | ❌ |
| 加密备份 | `backups/` | ❌ |
| 花呗 PDF 密码、备份密钥 | `config/local.yaml` `config/backup_secret.txt` | ❌ |
| 私人导入规则、账户映射 | `config/*.local.*` | ❌ |

软件唯一会联网的地方是 `paisa update` 拉取上游的税务指数（断网也能正常用）。
详见 **[docs/privacy.md](docs/privacy.md)**。

> ⚠️ **发到 GitHub 前务必读 `docs/privacy.md`**：改配置、跑历史扫描、
> 确认账本没被推到公开远程。本项目内置 `scripts/scan-pii.py` 门禁来拦这件事。

## 已知限制

- **仅支持 Windows**（`src/finance.py` 依赖 `.exe` 二进制与 Edge/Chrome 做 PDF 渲染）。
- **光大银行**暂无 provider，需手工转换明细。
- **花呗拆分**匹配率约 97%，剩余少量需人工确认（会列成清单，不会静默丢）。
- **UI 中文化**是就地改造 Svelte 字符串（上游 Paisa 没有 i18n 框架），
  升级上游时会有冲突，见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
- 首次导入后 `FIXME` 占比可能偏高——那是**待定性队列**不是 bug，
  按 [docs/import-rules.md](docs/import-rules.md) 逐步补规则即可。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | 从零到第一份财报 |
| [docs/import-rules.md](docs/import-rules.md) | 导入规则怎么写、怎么分层 |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 常见故障与排错 |
| [docs/privacy.md](docs/privacy.md) | 隐私、备份加密、发布前检查 |
| [docs/architecture.md](docs/architecture.md) | 架构、文件契约、设计取舍 |
| [docs/runbooks/](docs/runbooks/) | 月度 SOP、备份恢复、接入手册 |
| [docs/decisions/](docs/decisions/) | 关键决策记录 |

## 许可证

本项目以 **[AGPL-3.0-or-later](LICENSE)** 发布。

第三方组件（hledger / double-entry-generator / Paisa / tzdata 等）的许可与分发义务
见 **[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)**。

> 简单说：你可以自由使用、修改、自建服务；但如果你把它改造成对外提供的服务，
> 你必须公开你的修改。这也是为了确保这类"管自己钱"的工具不会被做成闭源 SaaS。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。**提交前请务必运行 `python scripts/scan-pii.py`** ——
个人财务项目最容易犯的错就是把真实账单/金额/姓名写进仓库。
