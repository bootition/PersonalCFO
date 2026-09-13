@echo off
rem ==========================================================================
rem  PersonalCFO 一键启动器（Windows）
rem
rem  本文件刻意保持纯 ASCII，只做一件事：把控制权交给 PowerShell 主体。
rem  原因：cmd.exe 按当前代码页解析 .bat 内的字节，中文字面量在不同系统区域
rem        设置下会乱码甚至导致命令解析失败。PowerShell 对 UTF-8 处理可靠得多。
rem
rem  实际逻辑见 scripts\start.ps1
rem ==========================================================================
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

where powershell >nul 2>&1
if errorlevel 1 (
  echo [ERROR] PowerShell not found. Windows 10/11 should have it built in.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\start.ps1" %*
if errorlevel 1 pause
