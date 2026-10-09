"""简单仿真脚本：向本地后端推送读数并触发决策。"""

import json
import time
import urllib.request

# 连续发送 3 轮读数并触发一次决策
for _ in range(3):
    data = json.dumps({
        'temperature': 35,
        'humidity': 85,
        'soil_moisture': 25,
        'ph': 6.2,
    }).encode()
    # 推送传感器读数
    urllib.request.urlopen(urllib.request.Request(
        'http://localhost:8000/api/sensors/readings',
        data=data,
        headers={'Content-Type': 'application/json'},
    ))
    # 触发一次决策并打印结果
    response = urllib.request.urlopen('http://localhost:8000/api/agents/run').read().decode()
    print(response)
    time.sleep(2)
