# 启动前端开发服务器（任意目录下执行；Ctrl+C 停止）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\dev-frontend.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\frontend"
pnpm dev
