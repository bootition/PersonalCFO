---
title: 月度记账 SOP（目标 30 分钟闭环）
status: approved
last_reviewed: 2026-09-07
---

# 月度记账 SOP

> 流程：导出账单 → 导入（F1/F3）→ FIXME 清零 → 对账（F8）→（季末）投资回写+结账+财报（F5/F6）。
> 所有命令在仓库根执行，一律用 `venv/Scripts/python`（hledger 只经 finance.py，自动 chcp 65001）。

## 0. 日常入口（每月 1 号后）

- [ ] 双击 **`启动PersonalCFO.bat`**（仓库根目录）→ 浏览器打开 http://localhost:6500
- [ ] 顶部「**初始化**」→「**① 上传账单**」→ 一次选中各 App 导出的 csv/xlsx + 花呗 PDF
  （花呗 PDF 打开密码填上）→ 「上传并导入」

> 全部由软件完成：保存到 raw/ → 自动 deg 导入 → 自动花呗拆分 → 自动维护 Paisa 合并入口。
>
> **不需要打开任何终端，不需要写任何 yaml。**

## 2. FIXME 清零（人工定性，约 15 分钟）

```bash
tools/hledger-bin/hledger.exe -f journals/import-*.journal register FIXME
```

- [ ] 逐条定性：人情转账（借出→`Assets:借出款项`/还款→冲销）、自转账（对应账户）、
  课程首付分期（`Expenses:书籍学习`）、校园卡充值（`Expenses:日常三餐`）等
- [ ] 高频同类先在 Paisa 编辑器改 journal，再把规律补进 `config/alipay.yaml` / `wechat.yaml`（防下月复发）
- [ ] 花呗拆分补录的"还款来源待人工指定"（`Assets:FIXME` 侧）：改为实际还款账户

## 3. 账实核对（约 5 分钟）

- [ ] 打开各 App 记录真实余额，填写 `config/actual_balances.yaml`（仅本地）
- [ ] 银行卡半追踪：以银行 App 真实余额为准（无银行明细期间）

```bash
venv/Scripts/python src/finance.py reconcile          # 先看差异
venv/Scripts/python src/finance.py reconcile --write  # 确认后生成调账分录
venv/Scripts/python src/finance.py check
```

## 4. Paisa 同步（约 1 分钟）

- [ ] **所有新产生的 journal 都要加 include 到 `paisa_test/all.journal`**：
  `import-*.journal`（步骤 1）、`reconcile-*.journal`（步骤 3）、`fair-value-*.journal`（步骤 6 季末）、
  `*-opening.journal`（期初建账后）、`recurring.journal`（P1.6 后）——漏加会导致 Paisa 与 CLI 口径分裂
- [ ] 快速自查：`ls journals/*.journal` 的文件数 == `paisa_test/all.journal` 的 include 行数

```bash
vendor/paisa/paisa.exe update --config paisa_test/paisa.yaml
vendor/paisa/paisa.exe serve --config paisa_test/paisa.yaml   # 日常查账入口
```

## 5. 账本仓提交（约 1 分钟）

```bash
cd journals && git add -A && git commit -m "monthly: YYYY-MM 导入+对账" && cd ..
```

## 6. 季末加做（约 10 分钟）

- [ ] Wealthfolio 导出 holdings CSV → `raw/`，执行 `venv/Scripts/python src/sync_fair_value.py raw/<holdings>.csv --date <季末日> --write`（F5；脚本对账户缺失/空市值只打印警告不拦截，**务必先看警告人工确认 CSV 完整后再 --write**）
- [ ] `venv/Scripts/python src/finance.py report <年>` 生成四期五表 PDF/CSV（F6）
- [ ] `venv/Scripts/python src/finance.py forecast` 看应急金覆盖月数
- [ ] `venv/Scripts/python src/finance.py close <年> <Q1|H1|Q3|AN>` 结账（快照+留存收益结转）
- [ ] 核对：财报投资科目 = Wealthfolio 期末市值；资产=负债+权益
- [ ] 把 `fair-value-*.journal` 加入 `paisa_test/all.journal` 并重跑 `paisa update`
- [ ] **季末产物再提交一次账本仓**：`cd journals && git add -A && git commit -m "quarterly: YYYY QN 回写+结账" && cd ..`

## 排错速查

| 症状 | 处置 |
|---|---|
| import 后 check 失衡 | 先查是否手动跑过 split_huabei 二次拆分（幂等护栏会拒绝；必须经 import 重跑） |
| deg 吞行疑虑 | 看冒烟"行数归因"，未解释≠0 即上报排查（献祭行机制见 STATUS 缺口 4） |
| 花呗匹配率 <95% | 看 reports/huabei-split-*.txt 的 FIXME 明细，多为代付/退款孤儿，人工定性 |
| paisa update FATAL | 确认 `paisa_test/paisa.yaml` 路径正斜杠、hledger 在 PATH；构建问题见任务计划红线 2 |
| paisa 端口被占/页面不更新 | Git Bash 的 `pkill` 杀不了 Windows 进程：用 `taskkill //IM paisa.exe //F` 再重启；Edge 截图/浏览器看到的可能是旧进程 |
| paisa.exe 异常虚胖（>60MB） | Node 24 在**中文路径**下 `fs.rmSync` 静默失效 → 陈旧 chunk 累积进 embed；已用 cmd rmdir 双清（prebuild）。重建前也可手动 `cmd /c "rmdir /s /q web\static & rmdir /s /q .svelte-kit\output"` |
| hledger 读 UTF-8 journal 报 hGetContents | 控制台代码页不是 65001（hledger 文件编码跟随控制台代码页）；一律经 finance.py（自动 chcp）；paisa 侧已修 CREATE_NO_WINDOW+GHC_CHARENC 双保险 |
