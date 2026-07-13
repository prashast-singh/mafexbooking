"""User email history.

Revision ID: 20250713_0005
Revises: 20250713_0004
Create Date: 2026-07-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250713_0005"
down_revision: Union[str, None] = "20250713_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_email_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email_history_user_id"), "user_email_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_email_history_user_id"), table_name="user_email_history")
    op.drop_table("user_email_history")
