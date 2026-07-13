"""Booking requests + room admins.

Revision ID: 20250702_0003
Revises: 20250605_0002
Create Date: 2026-07-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_0003"
down_revision: Union[str, None] = "20250605_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-unit booking mode: direct vs request
    op.add_column(
        "bookable_units",
        sa.Column(
            "booking_mode",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'direct'"),
        ),
    )

    # Room admins mapping (per-room)
    op.create_table(
        "room_admins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "user_id", name="uq_room_admin"),
    )
    op.create_index(op.f("ix_room_admins_room_id"), "room_admins", ["room_id"], unique=False)
    op.create_index(op.f("ix_room_admins_user_id"), "room_admins", ["user_id"], unique=False)

    # Booking decision audit fields (approve/deny)
    op.add_column("bookings", sa.Column("decided_by_id", sa.Integer(), nullable=True))
    op.add_column("bookings", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("decision_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_bookings_decided_by_id_users",
        "bookings",
        "users",
        ["decided_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_bookings_decided_by_id_users", "bookings", type_="foreignkey")
    op.drop_column("bookings", "decision_reason")
    op.drop_column("bookings", "decided_at")
    op.drop_column("bookings", "decided_by_id")

    op.drop_index(op.f("ix_room_admins_user_id"), table_name="room_admins")
    op.drop_index(op.f("ix_room_admins_room_id"), table_name="room_admins")
    op.drop_table("room_admins")

    op.drop_column("bookable_units", "booking_mode")

