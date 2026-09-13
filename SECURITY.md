# 安全与隐私

## 报告问题

**请不要在公开 Issue 里粘贴**：真实账单、账本内容、金额、姓名、卡号、身份证号、
界面截图（含账户名或余额）。

请改用 GitHub 的 **Private vulnerability reporting**（仓库 → Security → Report a vulnerability），
或在仓库主页找到维护者联系方式。我们会在 7 天内回复。

## 本项目处理的数据

PersonalCFO 是**纯本机软件**：

- 账本、账单、财报、备份只存在你的硬盘上（`journals/` `raw/` `reports/` `close/` `backups/`）
- 无账号、无云端、无遥测
- 唯一联网行为是 `paisa update` 拉取上游税务指数（断网可正常使用）

详见 [docs/privacy.md](docs/privacy.md)。

## 加密备份

- AES-256-GCM 认证加密，每档独立 16 字节 salt / 12 字节 nonce
- PBKDF2-HMAC-SHA256，**600,000 次迭代**，32 字节密钥
- 文件头 MAGIC 作为 AAD，防头部篡改
- 主密钥默认在 `config/backup_secret.txt`（已 gitignore）；
  **密钥丢失则归档不可恢复，没有后门**

## 仓库层面的防线

| 机制 | 作用 |
|---|---|
| `.gitignore` | 排除 `journals/` `raw/` `reports/` `close/` `backups/` `config/*.local.*` 与所有密钥文件 |
| `scripts/scan-pii.py` | CI + pre-commit 门禁：拦真实金额/身份证/卡号/邮箱/本机路径/密钥，以及本地专属词表 |
| `scripts/scan-pii.py --history` | 扫全部历史提交（发布前必跑） |
| `journals/.gitignore` | 账本仓独立排除 `bak/`（账单不影响账本仓） |

## 已知边界（如实披露）

- **提交历史**：2026-09 之前的提交曾包含作者个人数据；已在某次历史重写中清除，
  但 **force-push 无法收回已被 fork / 镜像 / 搜索引擎快照收录的内容**。
- **第三方二进制**：`tools/` 下的 hledger / deg 与 `vendor/paisa/paisa.exe` 不随仓库分发，
  由使用者自行下载。分发义务见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
- **无鉴权**：Paisa 默认监听 `localhost`。**不要把它暴露到公网**
  （局域网/公网使用请自行加反向代理 + 认证，并注意 AGPL §13 义务）。
