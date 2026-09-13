# 贡献指南

感谢你有兴趣参与。这个项目的目标是让普通人也能像公司一样看清自己的财务状况。

## 最重要的一条

> **提交前必须运行 `python scripts/scan-pii.py`，必须通过。**

个人财务项目最容易犯的错误，就是把真实账单、金额、姓名、卡号写进仓库。
本项目已经吃过一次教训（见下），现在用**可执行的门禁**而不是口号来防。

```powershell
python scripts/scan-pii.py            # 扫描被跟踪文件
python scripts/scan-pii.py --history  # 发布前额外跑一次（扫全部历史提交）
```

门禁会拦下：真实金额、身份证号、银行卡号、手机号、邮箱、本机绝对路径、密钥特征，
以及你自己在 `config/pii-rules.local.txt` 里定义的词条（真实姓名等，该文件不入库）。

**为什么专属词表要单独放一个不入库的文件**：门禁脚本本身会提交到公开仓库。
如果把真实人名写进脚本，门禁就成了新的泄漏源。

### 那次的教训

早期版本把人名/金额写进了 `docs/STATUS.md`、`docs/dev/任务计划.md` 和 `config/*.yaml`，
并被推送到了 GitHub。`.gitignore` 从来没有失效——`journals/`、`raw/`、`reports/`、
密钥、备份**一次都没进过 git**。泄漏发生在**内容层**：为了"把工作交代清楚"，
把具体数字和姓名写进了会被跟踪的文档。

三条可迁移的结论：

1. **写聚合指标，不写数据**：写"归类了 8 笔"（计数）或"FIXME 占比降到 0.6%"（比率），
   而不是"归类了 8 笔共 <金额> 元"（绝对金额）。
2. **规则文件不是安全的**：`config/*.yaml` 从真实账单里提取的 `peer: <对手方>`
   就是个人数据。所以本项目把规则分成公共模板 + `*.local.yaml`（不入库）。
3. **一次成功的清理不等于持续安全**：那次清理后又回归过一次。
   只有**门禁**能防回归，人工"我已经扫描过了"是会错的。

## 开发环境

```powershell
git clone <repo>
cd PersonalCFO
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
venv\Scripts\python.exe -m pytest tests -q
```

## 提交前自检

```powershell
# 1. 隐私门禁（必须过）
python scripts\scan-pii.py

# 2. 语法
venv\Scripts\python.exe -m compileall -q src scripts tests

# 3. 单元测试
venv\Scripts\python.exe -m pytest tests -q

# 4. 文档 front-matter
pwsh -File scripts\validate-frontmatter.ps1 -DocsRoot docs -FailOnError

# 5. 如果你动了导入规则或账本相关代码，务必确认导入结果不变：
#    在沙箱副本里跑一次 import，并跟现有 journals/ 逐字节对比
```

## 提交信息

用 [Conventional Commits](https://www.conventionalcommits.org/)，中文摘要：

```
feat(bank): 银行账单按文件名自动路由
fix(init): 非法自定义科目不再静默丢数据
docs: 补隐私说明与历史重写速查
```

## 代码约定

| 项 | 约定 |
|---|---|
| 编码 | 所有文本文件 UTF-8；Python 源文件带 `# -*- coding: utf-8 -*-` |
| 控制台输出 | 入口脚本必须调用 `from _console import setup_console; setup_console()`——否则输出被管道捕获时会按 CP936 崩 |
| 外部程序调用 | 一律走 `src/finance.py` 的 `hledger()` / 显式 `subprocess.run`，并**检查 returncode** |
| 写账本 | 任何改写 `journals/*.journal` 的代码，写后必须 `hledger check`，失败必须回滚（参考 `sync_fair_value.py`、`split_huabei.py`） |
| 新依赖 | 加到 `requirements.txt`（运行时）或 `requirements-dev.txt`（开发/测试） |
| 敏感值 | 写进 `config/*.local.*`，并在 `.gitignore` 里排除 |

## 报告问题

- **不要**在公开 Issue 里粘贴真实账单、账本、金额、姓名或截图。
- 附上 `finance.py check` / `status` 与 `scripts/reconcile-check.py` 的输出（脱敏后）。
- 安全或隐私问题请走私密渠道，见 [SECURITY.md](SECURITY.md)。

## 文档规则（本项目的既有约定）

- `docs/STATUS.md` 是内部状态唯一真相；对外读者请从 `README.md` 进入。
- `docs/decisions/` 记决策；`docs/contracts/` 记文件契约；`docs/runbooks/` 记操作手册。
- 新文档要带 front-matter（`title` / `status` / `last_reviewed`）。
- 报告只写聚合指标，不写金额明细。

## 许可证

贡献即表示你同意以 **AGPL-3.0-or-later** 授权你的贡献。
