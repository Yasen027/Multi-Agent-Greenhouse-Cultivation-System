"""SQLite 审计表的最小读写封装。"""

import sqlite3
from pathlib import Path

# 数据库文件位于进程工作目录（相对路径），首次连接时自动创建。
DB = Path("greenhouse.db")


def init_db():
    """确保审计表存在。"""
    c = sqlite3.connect(DB)
    # audit 表：自增主键、事件名、JSON 载荷与写入时间。
    c.execute(
        "create table if not exists audit (id integer primary key, event text, payload text, created_at text default current_timestamp)"
    )
    c.commit()
    c.close()


def save_audit(event, payload):
    """将一条审计事件序列化后写入数据库。"""
    import json

    c = sqlite3.connect(DB)
    # payload 用 default=str 兜底，保证 datetime 等非 JSON 原生类型也能序列化。
    c.execute(
        "insert into audit(event,payload) values (?,?)",
        (event, json.dumps(payload, default=str)),
    )
    c.commit()
    c.close()
