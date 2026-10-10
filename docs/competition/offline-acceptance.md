# 比赛离线冷启动验收

## 赛前制包

在联网电脑、最终代码版本上运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_offline.ps1
```

保存整个项目目录，确认其中包含：

- `deploy/offline/greenhouse-images.tar`
- `deploy/offline/greenhouse-images.tar.sha256`
- `start-offline.cmd`

## 全新电脑验收

1. 安装 Docker Desktop，之后断开网络。
2. 复制项目目录，双击 `start-offline.cmd`。
3. 确认脚本显示四项健康检查均通过，并打开 <http://localhost:5173>。
4. 切换“高温干旱”场景，确认出现决策、MQTT 命令、ACK 和环境变化。
5. 切换“风机故障”场景，确认连续失败后熔断并出现 HITL；点击“解除熔断”后只允许下一轮新命令，不重放旧命令。
6. 切换“传感器固定值”和“数据超时”，确认“已注入故障”与“系统诊断”分别显示。
7. 重启电脑并重复第 2～3 步，确认无需网络和软件源。

验收失败时保存：

```powershell
docker compose ps
docker compose logs --no-color > competition-startup.log
```

## 兜底录屏

冷启动验收通过后立即录制一遍第 2～6 步，画面同时包含系统时间、Docker 容器健康状态和浏览器操作。保留原始视频与一份 U 盘副本；录屏仅作现场环境故障兜底，不替代实时演示。
