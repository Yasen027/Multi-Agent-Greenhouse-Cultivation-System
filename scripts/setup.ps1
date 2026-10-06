# 一键初始化后端环境（在项目根目录创建 .venv 并安装固定依赖）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Get-Command 'py' -ErrorAction SilentlyContinue
$pythonCmd = if ($py) { "py -3.12" } else { 'python' }
Write-Host "[setup] 使用解释器: $pythonCmd"

Invoke-Expression "$pythonCmd -m venv .venv"
if ($LASTEXITCODE -ne 0) { throw '创建 .venv 失败' }

& "$root\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'pip install 失败' }
Write-Host '[setup] 完成。后续命令见 docs/setup.md（或直接使用 scripts\test.ps1 / scripts\dev-backend.ps1）'
