"""向本地 API 发送一组高温、高湿和偏干的模拟读数。"""

import json
import time
import urllib.request

for _ in range(3):
    # 先写入传感器读数，再请求一次完整决策。
    data = json.dumps(
        {"temperature": 35, "humidity": 85, "soil_moisture": 25, "ph": 6.2}
    ).encode()
    urllib.request.urlopen(
        urllib.request.Request(
            "http://localhost:8000/api/sensors/readings",
            data=data,
            headers={"Content-Type": "application/json"},
        )
    )
    print(
        urllib.request.urlopen("http://localhost:8000/api/agents/run").read().decode()
    )
    time.sleep(2)
