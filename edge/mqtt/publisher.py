"""通过 HTTP 模拟器周期性上报随机传感器读数。"""

import json
import random
import time
import urllib.request


def sample():
    """生成一组用于联调的随机温室读数。"""
    return {
        "temperature": round(random.uniform(20, 35), 1),
        "humidity": round(random.uniform(50, 85), 1),
        "soil_moisture": round(random.uniform(25, 60), 1),
        "ph": 6.2,
    }


if __name__ == "__main__":
    while True:
        # 当前模拟器通过 HTTP 上报，便于未配置 MQTT 时进行本地测试。
        data = json.dumps(sample()).encode()
        req = urllib.request.Request(
            "http://localhost:8000/api/sensors/readings",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)
        time.sleep(5)
