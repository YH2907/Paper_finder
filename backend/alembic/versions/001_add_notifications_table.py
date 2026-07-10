"""添加通知表

Revision ID: 001_notifications
Revises: 
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "001_notifications"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建通知表"""
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "type",
            sa.String(50),
            nullable=False,
            server_default="info",
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # 创建索引以优化查询性能
    op.create_index(
        "ix_notifications_user_id_is_read",
        "notifications",
        ["user_id", "is_read"],
    )
    op.create_index(
        "ix_notifications_created_at",
        "notifications",
        ["created_at"],
    )


def downgrade() -> None:
    """删除通知表"""
    op.drop_index("ix_notifications_created_at")
    op.drop_index("ix_notifications_user_id_is_read")
    op.drop_table("notifications")
