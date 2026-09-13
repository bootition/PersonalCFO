#Requires -Version 5.1
<#
    PersonalCFO 启动器（真实逻辑）

    由根目录 启动PersonalCFO.bat 调用。做五件事：
      1. 校验环境（paisa.exe / venv / hledger）
      2. 自愈 paisa_test\paisa.yaml（Paisa 首次运行会重写它、丢掉我们加的键）
      3. 补齐语言与币种设置（上游默认 en-IN / INR，会让中文界面显示 ₹ 与 lakh 分位）
      4. paisa update：把 journals/ 同步进 SQLite
      5. paisa serve：起界面并打开浏览器

    参数：
      -Port <n>    HTTP 端口，默认 6500
      环境变量 PCFO_ROOT / PCFO_PORT 也可覆盖。
#>
[CmdletBinding()]
param(
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot
if (-not $Port -or $Port -le 0) {
    $Port = if ($env:PCFO_PORT) { [int]$env:PCFO_PORT } else { 6500 }
}

Write-Host ""
Write-Host "PersonalCFO 启动器" -ForegroundColor Cyan
Write-Host "  仓库根目录 : $Root"
Write-Host "  界面端口   : $Port"
Write-Host ""

# ── 1. 环境校验 ──────────────────────────────────────────────────────────
$paisaExe = Join-Path $Root "vendor\paisa\paisa.exe"
$python   = Join-Path $Root "venv\Scripts\python.exe"
$hledger  = Join-Path $Root "tools\hledger-bin\hledger.exe"

$fatal = $false
if (-not (Test-Path $paisaExe)) {
    Write-Host "  [错误] 找不到界面程序：$paisaExe" -ForegroundColor Red
    Write-Host "         请从 Release 页下载 paisa.exe 放到该目录，或按 docs/troubleshooting.md 自行构建。"
    $fatal = $true
}
if (-not (Test-Path $python)) {
    Write-Host "  [错误] 找不到 Python 虚拟环境：$python" -ForegroundColor Red
    Write-Host "         请先运行：powershell -File scripts\bootstrap.ps1"
    $fatal = $true
}
if (-not (Test-Path $hledger)) {
    Write-Host "  [警告] 找不到 hledger：$hledger" -ForegroundColor Yellow
    Write-Host "         账本命令会失败；下载地址与版本见 tools\README.md"
}
if ($fatal) {
    Write-Host ""
    exit 1
}

# ── 2. 自愈 Paisa 配置 ───────────────────────────────────────────────────
# Paisa 首次运行会重写 paisa.yaml 并丢掉自定义键，所以每次启动都校验并补齐。
# 路径必须用正斜杠：Paisa 的 yaml 解析对 Windows 反斜杠会 FATAL。
$paisaDir = Join-Path $Root "paisa_test"
$paisaCfg = Join-Path $paisaDir "paisa.yaml"
if (-not (Test-Path $paisaDir)) { New-Item -ItemType Directory -Path $paisaDir | Out-Null }

$journalPath = (Join-Path $paisaDir "all.journal") -replace '\\', '/'
$dbPath      = (Join-Path $paisaDir "paisa.db")     -replace '\\', '/'

$needRebuild = $true
if (Test-Path $paisaCfg) {
    $cfgText = Get-Content -Raw -Encoding UTF8 $paisaCfg
    if ($cfgText -match "ledger_cli:\s*hledger") { $needRebuild = $false }
}
if ($needRebuild) {
    Write-Host "  [配置] 重建 paisa_test\paisa.yaml"
    @(
        "journal_path: $journalPath",
        "db_path: $dbPath",
        "ledger_cli: hledger"
    ) | Set-Content -Encoding UTF8 $paisaCfg
}

# ── 3. 语言 / 币种 / 财年 ────────────────────────────────────────────────
# 上游 Paisa 默认 locale=en-IN、default_currency=INR（印度财年 4 月起），
# 不覆盖的话中文界面会出现 ₹ 符号、lakh 分位（1,31,850）与 K/L 缩写坐标轴，
# 且「财年」口径会与 finance.py report 的日历期次错位。
$cfgText = Get-Content -Raw -Encoding UTF8 $paisaCfg
$patch = @()
if ($cfgText -notmatch "(?m)^\s*locale:")                          { $patch += "locale: zh-CN" }
if ($cfgText -notmatch "(?m)^\s*default_currency:")                { $patch += "default_currency: CNY" }
if ($cfgText -notmatch "(?m)^\s*financial_year_starting_month:")   { $patch += "financial_year_starting_month: 1" }
if ($patch.Count -gt 0) {
    Write-Host ("  [配置] 补齐 " + ($patch -join ", "))
    Add-Content -Encoding UTF8 -Path $paisaCfg -Value $patch
}

# ── 4. 同步账本 ──────────────────────────────────────────────────────────
Write-Host "[1/2] 同步账本到界面数据库 ..." -ForegroundColor Cyan
$env:PCFO_ROOT = $Root
& $paisaExe update --config $paisaCfg
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [错误] paisa update 失败。常见原因：" -ForegroundColor Red
    Write-Host "         - paisa_test\paisa.yaml 路径写错（必须正斜杠 /）"
    Write-Host "         - tools\hledger-bin\hledger.exe 缺失"
    Write-Host "         - journals\ 下 journal 有语法错误（跑 venv\Scripts\python.exe src\finance.py check 看详情）"
    Write-Host "         （若只是还没导入账单，journals\ 为空属正常，可继续）"
    Write-Host ""
    exit 1
}

# ── 5. 起界面 ────────────────────────────────────────────────────────────
$url = "http://localhost:$Port"
Write-Host "[2/2] 启动界面：$url" -ForegroundColor Cyan
Write-Host "      关闭本窗口即停止服务。"
Write-Host ""
Start-Process $url
& $paisaExe serve --config $paisaCfg -p $Port
