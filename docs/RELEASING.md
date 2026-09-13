---
title: 发布流程
status: approved
last_reviewed: 2026-09-13
---

# 发布流程

本项目涉及**两个仓库**：主仓（代码/文档）与界面 fork 仓（Paisa 改造）。
两者都有 AGPL/GPL 相关的分发义务，不能只发一边。

## 0. 发布前检查（每次必做）

```powershell
# 隐私门禁：被跟踪文件 + 全部历史提交
python scripts\scan-pii.py
python scripts\scan-pii.py --history

# 单元测试
venv\Scripts\python.exe -m pytest tests -q

# 账本与报表自洽
venv\Scripts\python.exe src\finance.py check
python scripts\reconcile-check.py

# UI 回归（需先起服务）
scripts\e2e-sweep.py --base-url http://localhost:7500
```

**任一项失败即停止发布。**

## 1. 主仓

```bash
git status                     # 确认工作区干净、没有误入 journals/ raw/ reports/
git tag -a v0.1.0 -m "PersonalCFO v0.1.0"
git push origin main --tags
```

GitHub Release 说明里写：**改变、已知限制、升级注意**。
主仓 Release **不放二进制**（hledger/deg 是第三方，Paisa 是 AGPL 分支，
单独分发会把 GPL/AGPL 的源码提供义务引到主仓）。

## 2. 界面 fork 仓（`PersonalCFO-paisa`）

**这个仓库必须公开**（AGPL-3.0 §6 要求提供 Corresponding Source 且不得限制再分发）。

### 2.1 干净树构建

```bash
cd vendor/paisa
git status                     # 必须干净！否则 vcs.modified=true，源码与二进制对不上
npm run build
go build -o paisa.exe .
go version -m paisa.exe | Select-String vcs.modified    # 必须是 false
```

> `vcs.modified=true` 的二进制**没有对应的源码版本**，直接违反 AGPL 的对应源码要求。
> 本项目历史上三个 exe 全都是 `+dirty`，已纠正。

### 2.2 打 tag 并发布

```bash
git tag -a fork-v0.1.0 -m "PersonalCFO fork v0.1.0"
git push origin master --tags
```

Release 附件至少要有：

| 附件 | 为什么 |
|---|---|
| `paisa.exe` | 用户要的东西 |
| `COPYING` | AGPL-3.0 全文 |
| `NOTICE.md` | §5(a) 修改声明 + 上游 URL + 基点 commit |
| `SHA256SUMS` | 校验下载完整性 |
| 源码（tag 或对应 commit 的 tarball） | §6 Corresponding Source |

### 2.3 更新主仓指引

把新版本的下载地址同步到 `tools/README.md`，并在 `CHANGELOG.md` 记一笔。

## 3. 版本号

- 主仓：语义化版本，`vMAJOR.MINOR.PATCH`
- fork 仓：`fork-vX.Y.Z`，同时标注所基于的上游基点（如 `based-on ananthakumaran/paisa@0c8301e`）

## 4. 关于第三方二进制（hledger / deg）

**不要**把 `hledger.exe` / `double-entry-generator.exe` 打包进任何 Release ——
那会触发 GPL-3.0 §6 / Apache-2.0 的分发义务。
让用户按 `tools/README.md` 的官方地址自行下载，义务就不会落到你头上。

如果将来确实要打包（例如做一键安装包），必须同时提供：

- hledger：GPL-3.0 全文 + 与二进制**完全同版本**的 Corresponding Source（源码 tarball URL 或三年有效书面 offer）+ 未修改声明
- deg：Apache-2.0 全文 + 保留其 NOTICE（`tools/LICENSE`、`tools/README.deg*.md`）+ 未修改声明

详见 [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)。

## 5. 出事时（隐私事故响应）

如果发现敏感数据进了公开仓库：

1. **先止血**：`git push --force` 清掉 HEAD 不够 —— 历史仍在。
2. **评估暴露面**：`git log -S "<敏感值>"` 看首次引入的提交与传播范围；
   检查仓库有没有被 fork。
3. **重写历史**：`git filter-repo --replace-text`（步骤见 [privacy.md](privacy.md) 附录）。
4. **假设已泄露**：force-push 不会立刻清除 GitHub 的不可达对象，
   已被 fork / 镜像 / 搜索快照收录的内容收不回。
   涉及密钥/证件号时**必须更换**，不能只是删除。
5. **加门禁防回退**：把该值的特征加进 `config/pii-rules.local.txt` 与
   `scripts/scan-pii.py` 的通用模式，并接进 CI 与 pre-commit。
