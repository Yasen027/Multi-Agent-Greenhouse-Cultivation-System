"""向本地 API 发送普通异常数据，再发送一组需要人工审批的极端高温数据。"""

import json
import time
import urllib.request

readings = [
    {"temperature": 35,
      "humidity": 85, "soil_moisture": 25, 
      "ph": 6.2
      }
] * 3 + [
    {"temperature": 45, 
     "humidity": 85, 
     "soil_moisture": 25, 
     "ph": 6.2}
]

for reading in readings:
    # 先写入传感器读数，再请求一次完整决策。
    data = json.dumps(reading).encode()
    urllib.request.urlopen(
        urllib.request.Request(
            "http://localhost:8000/api/sensors/readings",
            data=data,
            headers={"Content-Type": "application/json"},
        )
    )
    print(
        urllib.request.urlopen(
            urllib.request.Request(
                "http://localhost:8000/api/agents/run",
                data=b"",
                method="POST",
            )
        ).read().decode()
    )
    time.sleep(2)

print("待人工审批：")
print(urllib.request.urlopen("http://localhost:8000/api/hitl/pending").read().decode())
