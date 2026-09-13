#Requires -Version 5.1
<#
    个人财务系统 PersonalCFO —— 一键环境准备（Windows）

    做四件事：
      1. 检查 Python（3.11+）
      2. 建立虚拟环境 venv 并安装 requirements.txt
      3. 下载外部二进制（hledger / double-entry-generator）到 tools\
      4. 生成 paisa_test\paisa.yaml 初始配置（含中文与人民币设置）

    用法：
      powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
      powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1 -SkipDownload
#>
[CmdletBinding()]
param(
    [switch]$SkipDownload,      # 只装 Python 依赖，不下载二进制
    [switch]$Force              # 已存在的文件也重新下载
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($n, $total, $text) {
    Write-Host ""
    Write-Host "[$n/$total] $text" -ForegroundColor Cyan
}
function Ok($text)   { Write-Host "      OK  $text" -ForegroundColor Green }
function Warn($text) { Write-Host "      警告  $text" -ForegroundColor Yellow }
function Fail($text) { Write-Host "      错误  $text" -ForegroundColor Red }

Write-Host ""
Write-Host "PersonalCFO 环境准备" -ForegroundColor Cyan
Write-Host "  仓库根目录：$Root"

# ── 1. Python ────────────────────────────────────────────────────────────
Step 1 4 "检查 Python"

$py = $null
foreach ($cand in @("py -3", "python", "python3")) {
    $exe = $cand.Split(" ")[0]
    if (Get-Command $exe -ErrorAction SilentlyContinue) {
        try {
            $verText = & cmd /c "$cand -c ""import sys;print('%d.%d'%sys.version_info[:2])""" 2>$null
            if ($verText) {
                $parts = $verText.Trim().Split(".")
                if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11) {
                    $py = $cand
                    Ok "找到 Python $verText（$cand）"
                    break
                }
                Warn "$cand 是 Python $verText，需要 3.11+"
            }
        } catch { }
    }
}
if (-not $py) {
    Fail "未找到 Python 3.11 或更高版本。"
    Write-Host "      请到 https://www.python.org/downloads/windows/ 安装，"
    Write-Host "      安装时务必勾选 'Add python.exe to PATH'。"
    exit 1
}

# ── 2. venv + 依赖 ───────────────────────────────────────────────────────
Step 2 4 "建立虚拟环境并安装依赖"

$venvPy = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "      创建 venv ..."
    & cmd /c "$py -m venv venv"
    if ($LASTEXITCODE -ne 0) { Fail "创建 venv 失败"; exit 1 }
}
Ok "venv 就绪：$venvPy"

& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "安装 requirements.txt 失败"; exit 1 }
Ok "运行时依赖已安装"

# 开发/回归依赖（playwright 较大，失败不阻断）
$devReq = Join-Path $Root "requirements-dev.txt"
if (Test-Path $devReq) {
    Write-Host "      安装开发依赖（playwright / pytest，可跳过）..."
    & $venvPy -m pip install --quiet -r $devReq
    if ($LASTEXITCODE -eq 0) { Ok "开发依赖已安装" } else { Warn "开发依赖安装失败（不影响运行）" }
}

# ── 3. 外部二进制 ────────────────────────────────────────────────────────
Step 3 4 "检查外部二进制"

$tools = @(
    @{ Name = "hledger";                  Path = "tools\hledger-bin\hledger.exe";        Url = "https://github.com/plaintextaccounting/hledger/releases/download/1.52.3/hledger-windows-x64.zip"; Kind = "zip"; Into = "tools" },
    @{ Name = "double-entry-generator";   Path = "tools\double-entry-generator.exe";     Url = "https://github.com/deb-sig/double-entry-generator/releases/download/v2.15.1/double-entry-generator_Windows_x86_64.tar.gz"; Kind = "targz"; Into = "tools" }
)

foreach ($t in $tools) {
    $target = Join-Path $Root $t.Path
    if ((Test-Path $target) -and -not $Force) {
        $mb = [math]::Round((Get-Item $target).Length / 1MB, 1)
        Ok "$($t.Name) 已存在（$mb MB）"
        continue
    }
    if ($SkipDownload) {
        Warn "$($t.Name) 缺失，且指定了 -SkipDownload；请按 tools\README.md 手动下载"
        continue
    }
    Write-Host "      下载 $($t.Name) ..."
    $tmp = Join-Path $env:TEMP ("pcfo-" + [guid]::NewGuid().ToString("N") + "." + $t.Kind)
    try {
        Invoke-WebRequest -Uri $t.Url -OutFile $tmp -UseBasicParsing
        if ($t.Kind -eq "zip") {
            Expand-Archive -Path $tmp -DestinationPath (Join-Path $Root $t.Into) -Force
        } else {
            # tar.gz：Windows 10 1803+ 自带 tar.exe
            & tar -xzf $tmp -C (Join-Path $Root $t.Into)
            if ($LASTEXITCODE -ne 0) { throw "tar 解压失败（需要 Windows 10 1803+ 自带的 tar.exe）" }
        }
        Ok "$($t.Name) 已就位"
    } catch {
        Warn "下载/解压 $($t.Name) 失败：$($_.Exception.Message)"
        Warn "请按 tools\README.md 的地址手动下载后放到 $($t.Path)"
    } finally {
        Remove-Item -Force -ErrorAction SilentlyContinue $tmp
    }
}

# paisa.exe 无法自动下载（体积大、来源是 fork 仓库的 Release）
$paisaExe = Join-Path $Root "vendor\paisa\paisa.exe"
if (Test-Path $paisaExe) {
    Ok "paisa 界面程序已存在"
} else {
    Warn "缺少 vendor\paisa\paisa.exe（界面程序）"
    Write-Host "      获取方式见 tools\README.md「paisa.exe 从哪来」："
    Write-Host "        - 从 PersonalCFO-paisa 的 Releases 下载，或"
    Write-Host "        - 自行构建：cd vendor\paisa; npm ci; npm run build; go build -o paisa.exe ."
}

# ── 4. Paisa 配置 ────────────────────────────────────────────────────────
Step 4 4 "生成 paisa_test\paisa.yaml"

$paisaDir = Join-Path $Root "paisa_test"
New-Item -ItemType Directory -Force -Path $paisaDir | Out-Null
$cfg = Join-Path $paisaDir "paisa.yaml"
if (Test-Path $cfg) {
    Ok "已存在，跳过（如需重建请先删除它）"
} else {
    $journalPath = (Join-Path $paisaDir "all.journal") -replace '\\', '/'
    $dbPath      = (Join-Path $paisaDir "paisa.db")     -replace '\\', '/'
    @(
        "journal_path: $journalPath",
        "db_path: $dbPath",
        "ledger_cli: hledger",
        "locale: zh-CN",
        "default_currency: CNY",
        "financial_year_starting_month: 1"
    ) | Set-Content -Encoding UTF8 $cfg
    Ok "已写入 $cfg（含中文 / 人民币 / 日历财年设置）"
}

# ── 完成 ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "完成。" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  1. 校验账本：  venv\Scripts\python.exe src\finance.py check"
Write-Host "  2. 启动界面：  双击 启动PersonalCFO.bat"
Write-Host "  3. 首次使用：  浏览器里按「初始化」向导走 ①②③④"
Write-Host ""
Write-Host "首次使用请先读：docs\getting-started.md" -ForegroundColor Cyan
Write-Host ""
