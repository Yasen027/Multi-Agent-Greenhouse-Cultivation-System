"""边缘端模拟传感器数据发布器。

周期生成模拟读数并通过 HTTP 发送到后端。
"""

import json
import random
import time
import urllib.request


def sample():
    """生成一条模拟传感器读数。"""
    return {
        'temperature': round(random.uniform(20, 35), 1),
        'humidity': round(random.uniform(50, 85), 1),
        'soil_moisture': round(random.uniform(25, 60), 1),
        'ph': 6.2,
    }


if __name__ == '__main__':
    # 每 5 秒发送一条读数
    while True:
        data = json.dumps(sample()).encode()
        req = urllib.request.Request(
            'http://localhost:8000/api/sensors/readings',
            data=data,
            headers={'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req)
        time.sleep(5)
