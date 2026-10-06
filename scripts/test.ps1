# 统一测试入口：任意目录下执行
# 用法：powershell -ExecutionPolicy Bypass -File scripts\test.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& "$root\.venv\Scripts\python.exe" -m pytest -q
exit $LASTEXITCODE
