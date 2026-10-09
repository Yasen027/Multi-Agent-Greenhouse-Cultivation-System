"""SQLite 数据库会话与审计持久化。"""

import json
import sqlite3
from pathlib import Path

# 数据库文件路径
DB = Path('greenhouse.db')


def init_db():
    """初始化数据库并创建审计表。"""
    conn = sqlite3.connect(DB)
    conn.execute(
        'create table if not exists audit '
        '(id integer primary key, event text, payload text, '
        'created_at text default current_timestamp)'
    )
    conn.commit()
    conn.close()


def save_audit(event, payload):
    """持久化一条审计事件。"""
    conn = sqlite3.connect(DB)
    conn.execute(
        'insert into audit(event, payload) values (?, ?)',
        (event, json.dumps(payload, default=str)),
    )
    conn.commit()
    conn.close()
