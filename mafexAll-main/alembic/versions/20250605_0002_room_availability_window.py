"""Add per-room availability window (daily bookable hours).

Revision ID: 20250605_0002
Revises: 20250320_0001
Create Date: 2025-06-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250605_0002"
down_revision: Union[str, None] = "20250320_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rooms",
        sa.Column(
            "availability_window_start",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'08:00:00'"),
        ),
    )
    op.add_column(
        "rooms",
        sa.Column(
            "availability_window_end",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'20:00:00'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("rooms", "availability_window_end")
    op.drop_column("rooms", "availability_window_start")
