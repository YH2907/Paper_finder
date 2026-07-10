#!/usr/bin/env python3
"""添加用户推送设置字段到 SQLite 数据库"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "paperfinder.db")
if not os.path.exists(db_path):
    print("数据库文件不存在，跳过迁移（表将在启动时自动创建）")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

migrations = [
    ("push_enabled", "ALTER TABLE users ADD COLUMN push_enabled BOOLEAN DEFAULT 1 NOT NULL"),
    ("push_frequency", 'ALTER TABLE users ADD COLUMN push_frequency VARCHAR(20) DEFAULT "daily" NOT NULL'),
    ("push_time", 'ALTER TABLE users ADD COLUMN push_time VARCHAR(10) DEFAULT "09:00" NOT NULL'),
    ("push_count", "ALTER TABLE users ADD COLUMN push_count INTEGER DEFAULT 10 NOT NULL"),
]

for col_name, sql in migrations:
    if col_name not in columns:
        cursor.execute(sql)
        print(f"✅ 添加字段: {col_name}")
    else:
        print(f"⏭️  字段已存在: {col_name}")

conn.commit()
conn.close()
print("🎉 迁移完成")
