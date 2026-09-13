---
title: 架构与设计取舍
status: approved
last_reviewed: 2026-09-13
---

# 架构与设计取舍

## 一、总体架构

```
支付宝/微信/花呗/银行账单（raw/）
        │
        │  deg（规则化账单翻译器，YAML 规则）
        ▼
   journals/*.journal  ←── 唯一真相：纯文本、UTF-8、git 可版本化
        │
        ├─ finance.py ──► 四期财报（CSV / HTML / PDF）+ 结账/反结账/预测/对账
        │
        └─ Paisa fork ──► 日常 UI（本地 Web）
                │
                └◄── 季度 holdings CSV ── Wealthfolio（投资与目标）
```

**设计原则：账本是纯文本，脚本只是胶水，不实现任何会计引擎。**

## 二、组件职责

| 组件 | 职责 | 为什么用它（而不是自建） |
|---|---|---|
| **hledger** | 会计引擎：复式校验、四大报表、`close --retain`、`~ monthly` 定期规则、`--forecast`、价格库 | 成熟、快、纯文本、可审计；自建会计引擎是重复造轮子且极难正确 |
| **double-entry-generator** | 账单 → journal 的规则化翻译 | 原生支持支付宝/微信/多家银行；规则是 YAML，改规则即改行为 |
| **Paisa（fork）** | 日常界面 | 本地 Web UI、SQLite 缓存、图表完善；深改成本低于自建 30 个页面 |
| **Wealthfolio** | 投资子账本 | 持仓/净值/再平衡/FIRE 是独立领域，专业工具做得更好 |
| **finance.py** | 编排 + 自研第五表（权益变动表）+ PDF | hledger 没有权益变动表；其余全是"拼参数 + 解析输出" |

## 三、关键取舍

### 3.1 为什么原始账单是"唯一事实源"，journal 是可再生成的

`journals/import-*.journal` 由 deg 从 `raw/` 生成，**每次导入覆盖重建**。

好处：改规则 → 重导 → 立刻看到结果；出错随时回滚（改回规则重跑）。
代价：**不要手改 `import-*.journal`**，会被覆盖。要修正就写 `adjust-*.journal` 冲销分录。

这是 `full-fledged-hledger` / `hledger-flow` 的工作流模式。

### 3.2 为什么把"待确认"做成科目（`FIXME`）而不是弹窗队列

未命中规则的交易落到 `Expenses:FIXME` / `Assets:FIXME`。于是：

- 它是**账本内**的、可被任何工具查询的状态（`hledger register FIXME`）；
- 它的余额就是"还有多少钱没定性"，可以直接进报表；
- 不需要额外的队列存储与状态机。

### 3.3 为什么规则要分两层（公共模板 + 私人覆盖）

deg 的 `--config` 只接受单个文件，而"可公开的模板"与"含真实对手方名称的私人规则"
必须分离。因此 `src/import_rules.py` 在导入时把
`config/<平台>.local.yaml` 的规则**追加**到 `config/<平台>.yaml` 之后。

deg 的语义是"顺序评估、命中即赋值、**后命中覆盖先命中**"，所以：
行为与"直接把私人规则写在公共文件末尾"**完全一致**，而公共文件可以安全地进公开仓库。

→ 详见 [import-rules.md](import-rules.md)。

### 3.4 为什么报表期次会"跳过"

`finance.py report` 的期次是**日历期**（Q1 到 04-01、H1 到 07-01…）。
**时点报表（资产负债表 / 含权益表 / 权益变动表）在"期末早于建账日"时算的是
未建账的净流量余额，数字没有意义。**

实测：建账日 2026-09-10，却照样出"2026 半年报"，净资产为负数万。

更隐蔽的是：权益变动表的内部恒等式（期末 = 期初 + 净利润 + 其他变动）
**在任意时点都恒等于 0.00** —— 它是算术自洽校验，不是正确性校验，
所以任何自检都发现不了。**因此只能在入口显式拦截**（`--allow-pre-opening` 可强制）。

### 3.5 为什么界面是 fork 上游而不是另建前端

- Paisa **没有稳定 API**（`docs/reference/` 没有 API 文档，CLI 只有 4 个子命令、无 JSON 导出）；
  另建前端唯一稳定接口是 hledger journal + `hledger -O json`，重建 30 个页面是数月量级。
- 代价是**升级冲突**：本项目 91% 的改动量落在上游文件里。
  缓解措施：新增功能尽量放新文件（`internal/server/pcfo.go`、`routes/(app)/init/`、`routes/(app)/cfo/`）；
  中文化应收敛进 i18n 目录（上游无 i18n 框架，属已知技术债）。

→ 详见 [decisions/01_架构总纲_v3定稿.md](decisions/01_架构总纲_v3定稿.md)。

## 四、文件契约

| 契约 | 位置 | 说明 |
|---|---|---|
| C1 | deg → journal | 见 [contracts/01_文件契约.md](contracts/01_文件契约.md) |
| C2 | 规则配置 | `config/<平台>.yaml`（公共）+ `config/<平台>.local.yaml`（私人） |
| C3 | 花呗 PDF 密码 | `config/local.yaml` 的 `huabei_pdf_password`（不入库） |
| C4 | Wealthfolio holdings CSV | 必填字段 `account_name` / `symbol_name` / `market_value` / `cost_basis`；账户映射在 `config/wealthfolio-accounts.local.json` |
| C5 | 初始化表单 | `/init` → `config/opening_init.json` → `opening_entry.py --json` |
| C6 | 定期规则 | `config/recurring_rules.yaml` → `journals/recurring.journal` |

## 五、目录职责

| 路径 | 内容 | 入 git？ |
|---|---|---|
| `src/` | Python 编排层 | ✅ |
| `scripts/` | 备份 / 回归 / 门禁 / 安装 | ✅ |
| `tests/` | 单元测试 | ✅ |
| `config/` | 规则模板（`*.local.*` 不入库） | ✅ |
| `docs/` | 文档（`docs/evidence/` 不入库） | ✅ |
| `tools/` | 第三方二进制（仅 `zoneinfo.zip` 与三份说明入库） | 部分 |
| `vendor/paisa/` | 界面 fork（独立仓库） | ❌ |
| `journals/` | **账本（唯一真相）** | ❌ |
| `raw/` `reports/` `close/` `backups/` | 账单 / 财报 / 结账快照 / 加密备份 | ❌ |
| `paisa_test/` | Paisa 的配置与 SQLite 缓存 | ❌ |
| `.planning/` | AI 会话产物与机器证据 | ❌ |

## 六、已知技术债

1. **UI 中文化是就地改 Svelte 字符串**（上游无 i18n 框架）→ 升级冲突大。
   收敛方向：抽出 `src/lib/i18n/zh-CN.json` + `$_()` 薄封装。
2. **10 个上游页面被替换为 10 行空壳**（功能交由 Wealthfolio 或明确不需要）。
   更省的做法是恢复上游原文、只在导航隐藏。
3. **金额用 `float`**（不是 `Decimal`）→ 容差常量散落在多处。当前规模下无可见误差。
4. **部分逻辑重复实现**（CSV 余额解析 5 份、journal 解析 3 套正则）。
5. **仅支持 Windows**（`.exe` 二进制 + Edge/Chrome 渲染 PDF）。
6. **`vendor/paisa` 的构建产物与源码对应关系**依赖"干净树构建"；
   发布流程见 [RELEASING.md](RELEASING.md)。
