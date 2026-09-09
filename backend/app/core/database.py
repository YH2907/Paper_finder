"""数据库连接配置

开发环境使用 SQLite，生产环境使用 PostgreSQL
"""
import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine, TypeDecorator, String, Text, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings, BACKEND_DIR

def _normalize_database_url(database_url: str) -> str:
    """规范化数据库 URL，避免因启动目录变化导致连接到不同 SQLite 文件。"""
    if not database_url.startswith("sqlite:///"):
        return database_url

    sqlite_path = database_url.replace("sqlite:///", "", 1)
    if sqlite_path == ":memory:" or Path(sqlite_path).is_absolute():
        return database_url

    absolute_path = (BACKEND_DIR / sqlite_path).resolve()
    return f"sqlite:///{absolute_path.as_posix()}"


# 数据库 URL
# 开发: sqlite:///./paperfinder.db
# 生产: postgresql://user:***@localhost/paperfinder
DATABASE_URL = settings.get_database_url()
print(f"[Database] 使用路径: {DATABASE_URL}")

# 创建引擎
if DATABASE_URL.startswith("sqlite"):
    # SQLite 不支持某些参数
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL, echo=False)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 模型基类
class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise stores as string.
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value) if not isinstance(value, uuid.UUID) else value
        return value


class JSONEncodedList(TypeDecorator):
    """Platform-independent JSON list type.

    Stores as JSON text, works with both SQLite and PostgreSQL.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            import json
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            import json
            return json.loads(value)
        return value


# 依赖注入：获取数据库会话
def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建表）"""
    # 导入所有模型以确保它们被注册
    from app.models import user, topic, paper, chat, message, user_paper, notification  # noqa

    Base.metadata.create_all(bind=engine)

    # 兼容历史 SQLite 数据库：缺失推送字段时自动补齐。
    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as conn:
            # 检查 users 表的列
            user_columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(users)"))
            }

            if "push_enabled" not in user_columns:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN push_enabled BOOLEAN NOT NULL DEFAULT 1"
                    )
                )
            if "push_frequency" not in user_columns:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN push_frequency VARCHAR(20) NOT NULL DEFAULT 'daily'"
                    )
                )
            if "push_time" not in user_columns:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN push_time VARCHAR(10) NOT NULL DEFAULT '09:00'"
                    )
                )
            if "push_count" not in user_columns:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN push_count INTEGER NOT NULL DEFAULT 10"
                    )
                )

            # 检查 topics 表的列（新增的问题描述字段）
            topic_columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(topics)"))
            }

            if "description" not in topic_columns:
                conn.execute(
                    text(
                        "ALTER TABLE topics ADD COLUMN description TEXT"
                    )
                )
            if "problem_statement" not in topic_columns:
                conn.execute(
                    text(
                        "ALTER TABLE topics ADD COLUMN problem_statement TEXT"
                    )
                )

    print("✅ 数据库表创建完成")
