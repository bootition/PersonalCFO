# 第三方组件声明（THIRD-PARTY NOTICES）

本仓库（PersonalCFO）以 **AGPL-3.0-or-later** 发布，见根目录 `LICENSE`。
本项目在运行时调用若干第三方组件。以下声明随仓库分发，用于履行各组件许可证的署名与声明义务。

> **重要**：`tools/` 下的第三方可执行文件**不随本仓库分发**（`.gitignore` 已排除），
> 由使用者按 `tools/README.md` 的官方地址自行下载，因此当前**不构成对它们的再分发**。
> 一旦你把这些二进制随 Release、网盘、Docker 镜像等任何形式转手，
> **再分发义务即落到你身上** —— 下方"再分发时必须做"一列写明了该做什么。

## 组件清单

| 组件 | 版本 | 许可证 | 在本项目中的用法 | 再分发时必须做 |
|---|---|---|---|---|
| [hledger](https://github.com/simonmichael/hledger) | 1.52.3 | **GPL-3.0** | 以**独立进程**调用（`tools/hledger-bin/hledger.exe`），通过命令行参数与 stdout（`-O csv/html/txt`）交互 | 附 GPL-3.0 全文；提供与该二进制**完全同版本**的 Corresponding Source（源码 tarball URL 或三年有效书面 offer）；声明是否修改（本项目**未修改** hledger） |
| [double-entry-generator](https://github.com/deb-sig/double-entry-generator) | v2.15.1 | **Apache-2.0** | 以**独立进程**调用（`tools/double-entry-generator.exe`），输入账单、输出 hledger journal | 附 Apache-2.0 全文（即 `tools/LICENSE`）；保留其 NOTICE（`tools/README.deg.md`、`tools/README.deg.en.md`）；声明是否修改（本项目**未修改** deg）；**不得**使用其商标做背书 |
| [Paisa](https://github.com/ananthakumaran/paisa)（本项目的 UI 基础，已深度改造） | v0.7.6 派生 | **AGPL-3.0-or-later** | `vendor/paisa` → 构建为 `paisa.exe`，通过 HTTP（`localhost`）与文件（journal）交互 | 附 AGPL-3.0 全文；**逐文件显著标注修改**；提供完整 Corresponding Source（含前端构建方式）；**源码不得放在私有仓**；不得对再分发附加限制 |
| [Wealthfolio](https://github.com/afadil/wealthfolio) | — | **AGPL-3.0** | **由用户自行安装**，本项目只读其导出的 holdings CSV | 未随本仓库分发，无分发义务；文档中注明其许可证即可 |
| [tzdata](https://pypi.org/project/tzdata/) → `tools/zoneinfo.zip` | 2026.3 | **Apache-2.0**（底层 IANA tzdata 为 public domain） | **随本仓库分发**（`tools/zoneinfo.zip`，Windows 无 tzdata 时供 deg 解析时区；用 `ZIP_STORED` 打包，因 Go 的 zoneinfo 不支持 deflate） | 附 Apache-2.0 文本；注明来源："generated from pip tzdata 2026.3；IANA tzdata is public domain" |

## 运行时可选的 Python 依赖（不随仓库分发）

| 包 | 许可证 | 用途 |
|---|---|---|
| [PyYAML](https://pyyaml.org/) | MIT | 读取 deg 规则 / 定期规则配置 |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause | 花呗 PDF 解析 |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | MIT | 花呗 PDF 表格提取 |
| [openpyxl](https://foss.heptapod.net/openpyxl/openpyxl) | MIT | 微信 XLSX 预处理 |
| [cryptography](https://github.com/pyca/cryptography) | Apache-2.0 / BSD-3-Clause | 账本加密备份 |
| [playwright](https://github.com/microsoft/playwright-python) | Apache-2.0 | 端到端 UI 回归（`scripts/e2e-sweep.py`） |
| [tzdata](https://pypi.org/project/tzdata/) | Apache-2.0 | Windows 时区数据（已预打包为 `tools/zoneinfo.zip`） |
| [Microsoft Edge](https://www.microsoft.com/edge) | 专有 | HTML → PDF 渲染（**仅调用系统已安装程序，不随仓库分发**） |

## 关于"本项目代码 + GPL/AGPL 二进制"的许可关系（判断依据）

`src/*.py`、`scripts/*.py` 对 hledger / deg 的调用属于**进程间互操作**，不构成衍生作品：

1. **GPLv3 §0** 明文："The act of running the Program is not restricted." 传染范围是 §5 定义的 "works based on the Program"，而非"调用了它的程序"。
2. **独立进程 = exec/管道边界**。GPLv3 §5 与 AGPLv3 §5 末段均规定：把受覆盖作品与其他作品放在同一介质上（mere aggregation）不使其他作品受传染。
3. **接口层完全自写**：本仓库没有复制 hledger 的 Haskell 源码、没有 deg 的 Go 源码，也没有 FFI / cgo / 链接。

**会使判断反转的三种情况**（务必避免）：
- 把 hledger / deg 改成库链接（FFI、Go plugin、编译进自家二进制）；
- 把上游源码片段 copy 进 `src/`（例如把 deg 的 provider 逻辑翻译成 Python 后内联）；
- 把这些二进制随任何形式的产物一起分发（此时触发 §4/§6 的分发义务，与自己的代码是否衍生无关）。

## 本项目对 Paisa 的修改摘要（AGPL-3.0 §5(a) 要求）

- **修改时间**：2026-09 起
- **上游基点**：`ananthakumaran/paisa` v0.7.6（commit `0c8301e`）
- **修改内容**：UI 中文化与 Wealthfolio 化改造、Flexoki 主题令牌、侧边栏重构、首页仪表盘、
  `/init` 初始化向导、`/cfo` 工具入口、多文件上传、组级路径重定向、若干 Windows 兼容修复。
- **修改版源码**：见独立仓库 `PersonalCFO-paisa`（**必须公开**，AGPL-3.0 §6 要求；
  若仍为私有则本项目的二进制分发不合规）。
- **许可证未变更**：`vendor/paisa/COPYING` 原样保留。

---

若你是本项目的使用者而非作者：**你自己的账本、账单、备份属于你的个人数据**，
本项目不上传、不遥测、不联网同步；`journals/`、`raw/`、`reports/`、`close/`、`backups/`
与所有 `*.local.*` 配置默认已被 `.gitignore` 排除。详见 `docs/privacy.md`。
