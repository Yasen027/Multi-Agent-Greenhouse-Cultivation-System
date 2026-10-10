"""向本地 API 发送普通异常数据，再发送一组需要人工审批的极端高温数据。"""

import json
import time
import urllib.request

# 构造 4 组读数：前 3 组为 35℃ 异常数据，最后 1 组为 45℃ 危险高温（应触发人工审批）。
readings = [
    {
        "temperature": 35,
        "humidity": 85,
        "soil_moisture": 25,
        "ph": 6.2,
    }
] * 3 + [
    {
        "temperature": 45,
        "humidity": 85,
        "soil_moisture": 25,
        "ph": 6.2,
    }
]

# 逐组上报读数，并在每次上报后请求一次完整决策。
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
    # 每组上报间隔 2 秒，避免请求过于密集。
    time.sleep(2)

# 最后查询人工审批队列，验证极端高温数据是否被拦截等待人工处理。
print("待人工审批：")
print(urllib.request.urlopen("http://localhost:8000/api/hitl/pending").read().decode())
