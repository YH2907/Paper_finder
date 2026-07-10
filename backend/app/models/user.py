import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_frequency: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)  # daily, weekly, monthly
    push_time: Mapped[str] = mapped_column(String(10), default="09:00", nullable=False)  # HH:MM
    push_count: Mapped[int] = mapped_column(default=10, nullable=False)  # 每次推送论文数量
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    topics = relationship("Topic", back_populates="user", cascade="all, delete-orphan")
    user_papers = relationship("UserPaper", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
