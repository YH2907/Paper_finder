"""添加主题的问题描述字段

Revision ID: 002_topic_problem_fields
Revises: 001_notifications
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "002_topic_problem_fields"
down_revision = "001_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加 description 和 problem_statement 字段到 topics 表"""
    op.add_column(
        "topics",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "topics",
        sa.Column("problem_statement", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """删除 description 和 problem_statement 字段"""
    op.drop_column("topics", "problem_statement")
    op.drop_column("topics", "description")
