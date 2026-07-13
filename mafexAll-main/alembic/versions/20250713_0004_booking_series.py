"""Booking series (recurring bookings).

Revision ID: 20250713_0004
Revises: 20250702_0003
Create Date: 2026-07-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250713_0004"
down_revision: Union[str, None] = "20250702_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking_series",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("series_start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("max_occurrences", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["bookable_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("bookings", sa.Column("series_id", sa.Integer(), nullable=True))
    op.add_column("bookings", sa.Column("occurrence_index", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_bookings_series_id",
        "bookings",
        "booking_series",
        ["series_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_bookings_series_id", "bookings", type_="foreignkey")
    op.drop_column("bookings", "occurrence_index")
    op.drop_column("bookings", "series_id")
    op.drop_table("booking_series")
