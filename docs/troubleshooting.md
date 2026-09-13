---
title: 故障排查
status: approved
last_reviewed: 2026-09-13
---

# 故障排查

按"症状 → 原因 → 解决"组织。先跑一遍自检能省很多时间：

```powershell
venv\Scripts\python.exe src\finance.py check     # 账本平衡
venv\Scripts\python.exe src\finance.py status    # 初始化状态（JSON）
python scripts\reconcile-check.py                # 报表自洽 + 跨源核对
```

---

## 启动与界面

### 双击 bat 一闪而过 / 提示找不到 PowerShell

`启动PersonalCFO.bat` 只是外壳，真正逻辑在 `scripts\start.ps1`。
手动运行可以看到完整报错：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

### 提示「找不到 vendor\paisa\paisa.exe」

界面程序不随仓库分发（体积大）。获取方式见
[`tools/README.md`](../tools/README.md#paisaexe-从哪来)。

### 浏览器打开是空白 / 连不上

1. 看启动窗口有没有报错 —— **窗口不能关**，关掉服务就停了。
2. 端口被占用：

   ```powershell
   netstat -ano | findstr :6500
   taskkill /PID <上面查到的PID> /F
   ```

   或换端口启动：`powershell -File scripts\start.ps1 -Port 6600`

### 界面里的「初始化 / CFO 工具」点不动或报「未找到仓库根目录」

这两个功能靠 `PCFO_ROOT` 找到 `src/finance.py` 与 `venv`。
正常从 `启动PersonalCFO.bat` 启动会自动设置；如果你是手动起 `paisa.exe`：

```powershell
$env:PCFO_ROOT = "<你的仓库路径>"
.\vendor\paisa\paisa.exe serve --config paisa_test\paisa.yaml -p 6500
```

### `paisa update` 报 `unknown time zone Asia/Shanghai`

缺时区库。检查并重建：

```powershell
venv\Scripts\python.exe scripts\gen-zoneinfo.py --check
venv\Scripts\python.exe scripts\gen-zoneinfo.py        # 缺了就重建
```

启动器会自动把 `tools\zoneinfo.zip` 通过 `ZONEINFO` 环境变量传给 deg。

### `paisa update` 报 `Invalid configuration`

`paisa_test\paisa.yaml` 里有不被允许的键（Paisa 用的是严格 schema）。
删掉重建即可，**不会影响账本**：

```powershell
del paisa_test\paisa.yaml
powershell -File scripts\start.ps1
```

### 界面数字带 ₹ 符号 / 出现 `1,31,850` / 坐标轴是 `K`、`L`

上游 Paisa 默认 locale 是印度（`en-IN` / `INR`）。启动器会自动补上：

```yaml
locale: zh-CN
default_currency: CNY
financial_year_starting_month: 1
```

如果 `paisa_test\paisa.yaml` 里没有这三行，删掉文件重启一次。

---

## 导入

### 支付宝账单导入后"少了第一笔"

已修复。deg v2.15.1 会静默吞掉表头后的第一行数据，本项目用"献祭行"对策处理。
如果仍见少笔，跑：

```powershell
venv\Scripts\python.exe src\finance.py import
```

导入日志会打印 `行数归因：源 N 行 → journal M 笔；剔除 X 行` 与 `未解释 0 行 ✅`。
**"未解释"必须是 0**，否则说明有笔数被静默丢弃，请提 issue 并附上那行日志。

### 微信 XLSX 导入失败

确认导出的是「用于个人对账」的 XLSX（不是 CSV、不是 PDF）。
微信 CSV 与 XLSX 列结构不同，本项目按 XLSX 处理。

### 银行账单没被识别

文件名里必须带银行关键字：

| 银行 | 文件名需含 |
|---|---|
| 建设银行 | `建行` 或 `ccb` |
| 招商银行 | `招行` / `招商银行` / `cmb` |
| 工商银行 | `工行` / `工商银行` / `icbc` |

光大银行（`ceb`）暂无 provider，需要手工转换成 CSV 后走通用导入。

### 银行账单导入后全是 `FIXME`

**这是设计如此**：程序不猜科目。按 FIXME 报告补 `config\<bank>.local.yaml` 规则，
见 [import-rules.md](import-rules.md)。

---

## FIXME 太多

`FIXME` 不是错误，是**待定性队列**。查看规模：

```powershell
venv\Scripts\python.exe src\journal_stats.py journals\import-*.journal
```

按对手方聚合，找出最高频的几个，写进 `config\<平台>.local.yaml`，重新导入。

> 注意：**对方是真实人名的规则必须写在 `*.local.yaml`**（不入库）。
> 写进公共模板会被 `scripts\scan-pii.py` 拦下。

---

## 报表

### 提示「已跳过 Q1/H1（期末早于建账日）」

这是**正确行为**。时点报表在"期末早于建账日"时算的是未建账的净流量余额，数字无意义
（实测会出现"净资产 -4.6 万"这种）。
要么接受跳过，要么加 `--allow-pre-opening` 明确表示"我只要流水口径"。

### 没有生成 PDF

需要系统装有 Edge 或 Chrome。程序会按顺序探测：

```
C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
C:\Program Files\Microsoft\Edge\Application\msedge.exe
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
```

都没有就会在 PATH 里找 `msedge` / `chrome`。装一个即可。
CSV / HTML / TXT 不受影响。

### 报表数字看着不对

跑自洽复核，它会直读 hledger（不经过任何中间层）重新算一遍：

```powershell
python scripts\reconcile-check.py --allow-no-api
```

会校验：账本平衡、每个月末的借贷恒等式、期初分录自洽、FIXME 规模。

---

## 初始化向导

### 提示「有 N 处其他科目填写有误」

按行内提示改。科目名必须是 `Assets:xxx` 或 `Liabilities:xxx` 这种**冒号分层**的路径，
例如 `Assets:现金:纸币`。**本次不会提交任何数据，你的输入都还在。**

### 填了数字但没生效 / 数字变少了

已修复：非法行现在会标红并阻止提交，不再静默丢弃。
如果你的版本仍会"报成功但数字少"，请升级。

### 中途关掉了页面

第 ② 步有草稿，重新打开会自动恢复。第 ③ 步没有草稿，重新填一次即可。

---

## 账本

### `finance.py check` 报不平衡

```powershell
tools\hledger-bin\hledger.exe -f journals\<可疑文件>.journal check
```

如果怀疑是花呗拆分导致的，拆分脚本会在写回后自校验，失败会自动从
`journals\bak\` 回滚并报错。

### 手工改过 `journals\import-*.journal`，重导后改动没了

**这是预期行为**：`import-*.journal` 是 deg 的生成物，每次导入都会覆盖重建。
要修正就改规则（或写 `adjust-*.journal` 冲销分录）。

### 想恢复到某个历史状态

账本是 git 仓库：

```powershell
cd journals
git log --oneline
git checkout <commit> -- 某个文件.journal
```

---

## 备份与恢复

```powershell
python scripts\backup.py backup     # 生成加密归档
python scripts\backup.py list       # 列出归档
python scripts\backup.py verify <归档>   # 逐文件 sha256 校验 + 恢复演练
python scripts\backup.py restore <归档> <目标目录>
```

**口令丢了归档就打不开**——没有后门。口令默认在 `config\backup_secret.txt`，
请另存到密码管理器。

详见 [runbooks/03_备份与恢复.md](runbooks/03_备份与恢复.md)。

---

## 其它

### `finance.py` 报 `[缺失] 未找到 hledger`

正文里有下载地址；或一键：

```powershell
powershell -File scripts\bootstrap.ps1
```

### 想彻底重来

**先备份**（`reset_init.py` 会删掉期初配置与花呗密码）：

```powershell
python scripts\backup.py backup
venv\Scripts\python.exe src\reset_init.py
```

### 界面卡顿 / 页面空白

先看 `more → 诊断`（doctor）页；再看 `more → 日志`。
用控制台看有没有 JS 报错。

### 我要在自己的机器上重新构建界面

见 [`tools/README.md`](../tools/README.md#paisaexe-从哪来)。
注意 `npm run build` 的 `prebuild` 会先清空 `web/static`。

---

## 提 issue 之前

1. 跑一遍上面三个自检命令，把输出贴上。
2. **不要粘贴真实账单、账本、金额、姓名、卡号截图**——
   用文字描述或把敏感值替换掉。见 [privacy.md](privacy.md)。
3. 说明系统版本、Python 版本、`paisa.exe` 版本（`more → 关于`）。
