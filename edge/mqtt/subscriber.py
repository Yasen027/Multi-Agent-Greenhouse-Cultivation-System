# 边缘端 MQTT 命令订阅入口：直接运行本文件时启动订阅循环，broker 与主题均可由环境变量覆盖。
import os

# 包内相对导入失败时回退到同目录模块导入，便于以脚本方式独立运行。
try:
    from .command_handler import subscribe
except ImportError:
    from command_handler import subscribe


# 作为脚本运行时进入阻塞订阅循环；未配置环境变量时使用本机 broker 与默认执行器命令主题。
if __name__ == "__main__":
    subscribe(
        os.getenv("MQTT_BROKER", "localhost"),
        os.getenv("MQTT_ACTUATOR_TOPIC", "greenhouse/actuators/commands"),
    )
