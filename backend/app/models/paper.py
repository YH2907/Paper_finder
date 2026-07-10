import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, JSONEncodedList


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    authors: Mapped[list[str]] = mapped_column(JSONEncodedList, nullable=False, default=list)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # arxiv, semantic_scholar, openalex
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_problem_solved: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user_papers = relationship("UserPaper", back_populates="paper")
    chats = relationship("Chat", back_populates="paper")
