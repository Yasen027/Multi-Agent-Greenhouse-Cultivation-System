"""通过 HTTP 模拟器周期性上报随机传感器读数。"""

import json
import random
import time
import urllib.request


def sample():
    """生成一组用于联调的随机温室读数。"""
    # 温度/湿度/土壤湿度在给定区间随机取值，pH 固定为 6.2 以简化联调比对。
    return {
        "temperature": round(random.uniform(20, 35), 1),
        "humidity": round(random.uniform(50, 85), 1),
        "soil_moisture": round(random.uniform(25, 60), 1),
        "ph": 6.2,
    }


if __name__ == "__main__":
    # 持续生成随机读数并 POST 到本地 API，模拟边缘传感器周期上报。
    while True:
        # 当前模拟器通过 HTTP 上报，便于未配置 MQTT 时进行本地测试。
        data = json.dumps(sample()).encode()
        req = urllib.request.Request(
            "http://localhost:8000/api/sensors/readings",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)
        # 每 5 秒上报一次。
        time.sleep(5)
