"""SQLite 审计表的最小读写封装。"""

import sqlite3
from pathlib import Path

DB = Path("greenhouse.db")


def init_db():
    """确保审计表存在。"""
    c = sqlite3.connect(DB)
    c.execute(
        "create table if not exists audit (id integer primary key, event text, payload text, created_at text default current_timestamp)"
    )
    c.commit()
    c.close()


def save_audit(event, payload):
    """将一条审计事件序列化后写入数据库。"""
    import json

    c = sqlite3.connect(DB)
    c.execute(
        "insert into audit(event,payload) values (?,?)",
        (event, json.dumps(payload, default=str)),
    )
    c.commit()
    c.close()
