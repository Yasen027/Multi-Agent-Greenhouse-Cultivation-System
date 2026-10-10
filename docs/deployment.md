# 部署指南

## 联网构建

依赖只在镜像构建阶段安装，比赛启动阶段不挂载源码、不访问软件源：

```powershell
docker compose up --build --wait
powershell -ExecutionPolicy Bypass -File scripts/package_offline.ps1
```

前端统一使用 `pnpm@11.7.0` 和已提交的 `frontend/pnpm-lock.yaml`；Python 顶层依赖均在 `requirements.txt` 中使用 `==` 固定版本。

## 离线启动

把项目目录和 `deploy/offline/greenhouse-images.tar` 一起复制到比赛电脑，安装并启动 Docker Desktop 后双击 `start-offline.cmd`。脚本会校验镜像包、执行 `docker load`，并以 `--no-build --pull never` 启动服务。

启动成功必须同时满足：

- Mosquitto 能响应本机订阅探针；
- API `/api/health` 返回 `status=ok`；
- 数字孪生主循环心跳持续更新；
- 前端 Nginx 可以正常返回首页。
