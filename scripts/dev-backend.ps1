# 启动后端开发服务器（任意目录下执行；Ctrl+C 停止）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\dev-backend.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& "$root\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload --port 8000
