"""数据库连接配置

开发环境使用 SQLite，生产环境使用 Supabase PostgreSQL
"""
import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine, TypeDecorator, String, Text, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings, BACKEND_DIR


# ── Check if Supabase is configured ──────────────────────
USE_SUPABASE = bool(settings.SUPABASE_URL and settings.SUPABASE_SECRET_KEY)

if USE_SUPABASE:
    print(f"[Database] Using Supabase: {settings.SUPABASE_URL}")
    # Import Supabase adapter
    from app.core.supabase_db import get_db, init_db, SupabaseSession, SupabaseModel, QueryBuilder
    
    # Keep SQLAlchemy for local development fallback
    DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'paperfinder.db').as_posix()}"
    engine = None
    SessionLocal = None
else:
    print("[Database] Supabase not configured, using SQLite")
    
    def _normalize_database_url(database_url: str) -> str:
        """规范化数据库 URL，避免因启动目录变化导致连接到不同 SQLite 文件。"""
        if not database_url.startswith("sqlite:///"):
            return database_url
        sqlite_path = database_url.replace("sqlite:///", "", 1)
        if sqlite_path == ":memory:" or Path(sqlite_path).is_absolute():
            return database_url
        absolute_path = (BACKEND_DIR / sqlite_path).resolve()
        return f"sqlite:///{absolute_path.as_posix()}"

    DATABASE_URL = settings.get_database_url()
    print(f"[Database] 使用路径: {DATABASE_URL}")

    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False, "timeout": 30},
            echo=False,
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.close()
    else:
        engine = create_engine(DATABASE_URL, echo=False)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        """获取数据库 session

        - Supabase 模式：返回 SupabaseSession
        - SQLite 模式：返回 SQLAlchemy Session
        """
        if USE_SUPABASE:
            from app.core.supabase_db import SupabaseSession
            db = SupabaseSession()
            try:
                yield db
            finally:
                pass  # SupabaseSession is stateless
        else:
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

    def init_db():
        """初始化数据库（创建表）"""
        from app.models import user, topic, paper, chat, message, user_paper, notification
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建完成")


# ── Model base class (always needed for model definitions) ──
class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """Platform-independent GUID type."""
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
    """Platform-independent JSON list type."""
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
