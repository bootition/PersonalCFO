---
title: 隐私与数据安全说明
status: approved
last_reviewed: 2026-09-13
---

# 隐私与数据安全说明

> 面向所有使用者（不只是作者）。如果你要使用 PersonalCFO 记录自己的财务，
> 这一页解释了**你的数据存在哪、什么会被上传、什么绝对不会**。

## 一句话

**PersonalCFO 是纯本机软件。账本、账单、财报、备份都只存在你自己的电脑上；
没有账号、没有云端、没有遥测、没有联网同步。**

## 数据在哪

| 数据 | 位置 | 是否入库 | 说明 |
|---|---|---|---|
| 账本（唯一真相） | `journals/` | ❌ 已排除 | 独立本地 git 仓库，可自行建私有远程 |
| 原始账单 | `raw/` | ❌ 已排除 | 支付宝/微信/银行/花呗原件，**含姓名、账号、交易明细** |
| 财报产物 | `reports/` | ❌ 已排除 | 四期 PDF/CSV/HTML |
| 结账快照 | `close/` | ❌ 已排除 | — |
| 加密备份 | `backups/` | ❌ 已排除 | AES-256-GCM |
| 花呗 PDF 密码 | `config/local.yaml` | ❌ 已排除 | — |
| 备份主密钥 | `config/backup_secret.txt` | ❌ 已排除 | — |
| 私人导入规则 | `config/*.local.yaml` | ❌ 已排除 | 含真实对手方名称 |
| 私人账户映射 | `config/wealthfolio-accounts.local.json` | ❌ 已排除 | 含你的账户命名 |
| PII 词表 | `config/pii-rules.local.txt` | ❌ 已排除 | 门禁用 |
| 初始化草稿/期初/定期规则 | `config/opening_*.json`、`config/*_balances.yaml`、`config/recurring_rules.yaml` | ❌ 已排除 | — |

完整规则见根目录 `.gitignore`。

## 唯一会联网的地方

| 场景 | 请求 | 影响 |
|---|---|---|
| `paisa update` | 拉取**印度**税务用通胀指数（上游 Paisa 默认行为） | 断网时打一条 ERROR 日志然后继续，**账本数据零影响**（已实测：postings 数量与内容完全一致） |

其余全部离线：导入、拆分、对账、报表、备份、UI 均不联网，前端不加载任何 CDN。
若你想彻底禁掉它：删除 `paisa_test/paisa.yaml` 里的相关配置或断网运行即可。

## 备份加密

`python scripts/backup.py backup` 生成 `.pcfobak` 归档：

- **AES-256-GCM** 认证加密；每个归档独立 16 字节 salt、12 字节 nonce；
- **PBKDF2-HMAC-SHA256，600,000 次迭代**，派生 32 字节密钥；
- 文件头 MAGIC 作为 AAD，防止头部被篡改；
- 主密钥默认存放在 `config/backup_secret.txt`（已 gitignore），**请另行离线保管**。
  **密钥丢了归档就打不开**，没有后门。

恢复流程见 `docs/runbooks/03_备份与恢复.md`。

## 公开仓库的 PII 门禁

本项目有一个**可执行**的隐私门禁，而不是只写在文档里的口号：

```bash
python scripts/scan-pii.py            # 扫描全部被跟踪文件
python scripts/scan-pii.py --history  # 扫描全部历史提交（发布前跑一次）
```

它做两层检查：

1. **通用模式**（硬编码在脚本里）：真实金额、身份证号、银行卡号、手机号、邮箱、
   本机绝对路径、密钥特征。
2. **专属词表**（从 `config/pii-rules.local.txt` 读取，**该文件不入库**）：
   真实人名、家属称谓、用户自创账户别名等。

> 为什么分层：门禁脚本本身会提交到公开仓库。如果把真实人名写进脚本，
> 门禁就成了新的泄漏源。所以专属词表放在 gitignored 的本地文件里，
> 仓库内只提供 `config/pii-rules.example.txt` 占位示例。

CI 与 pre-commit 都会跑它；命中即拒绝提交/发布。

## 如果你要对外发布自己的 fork

1. **先改默认值**：`paisa_test/paisa.yaml` 的 `locale` / `default_currency`
   （上游默认是印度 `en-IN` / `INR`，见 `docs/troubleshooting.md`）。
2. **跑一次历史扫描**：`python scripts/scan-pii.py --history`。
3. **检查历史而非只看 HEAD**：`git log -S "<你的真名>"` ——
   敏感值一旦进过提交，改代码删掉是没用的，必须重写历史
   （`git filter-repo --replace-text`，见 `docs/privacy.md` 附录）。
4. **不要把 `journals/` 推到公开远程**。

### 附录：历史重写速查

```bash
# 0. 先备份！（.git 目录 + 全引用 bundle）
cp -r .git ../repo-git-backup
git bundle create ../all-refs.bundle --all

# 1. 把替换规则整理成 old==>new 形式（一行一条）
#    可复用 config/pii-rules.local.txt 的 `==>` 右侧
# 2. 重写
pip install git-filter-repo
git filter-repo --replace-text replacements.txt
# 3. 邮箱也要换（commit author 同样会暴露）
git filter-repo --mailmap mailmap.txt
# 4. 强推（会改变所有 SHA；确认无协作者）
git remote add origin <url>
git push --force --all && git push --force --tags
```

**注意**：force-push **不会立刻清除 GitHub 上的不可达对象**，已被 fork / 镜像 /
搜索引擎快照收录的内容无法收回。最彻底的做法是删除远程仓库后重建。
