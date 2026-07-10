import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID


class UserPaper(Base):
    __tablename__ = "user_papers"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="user_papers")
    paper = relationship("Paper", back_populates="user_papers")

    __table_args__ = (
        UniqueConstraint("user_id", "paper_id", name="uq_user_paper"),
    )
