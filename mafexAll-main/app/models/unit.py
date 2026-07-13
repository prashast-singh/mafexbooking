from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.room import Room


class BookableUnit(Base):
    __tablename__ = "bookable_units"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    parent_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookable_units.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(32))
    booking_mode: Mapped[str] = mapped_column(String(16), default="direct")
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    room: Mapped["Room"] = relationship(back_populates="bookable_units")
    parent: Mapped[BookableUnit | None] = relationship(
        "BookableUnit",
        remote_side=[id],
        foreign_keys=[parent_unit_id],
        back_populates="children",
    )
    children: Mapped[list[BookableUnit]] = relationship(
        "BookableUnit",
        back_populates="parent",
        foreign_keys=[parent_unit_id],
        cascade="all, delete-orphan",
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="unit")


class UnitConflict(Base):
    __tablename__ = "unit_conflicts"
    __table_args__ = (
        UniqueConstraint("unit_id", "conflict_with_unit_id", name="uq_unit_conflict_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("bookable_units.id", ondelete="CASCADE"))
    conflict_with_unit_id: Mapped[int] = mapped_column(
        ForeignKey("bookable_units.id", ondelete="CASCADE")
    )

    unit: Mapped[BookableUnit] = relationship(foreign_keys=[unit_id])
    conflicts_with_unit: Mapped[BookableUnit] = relationship(foreign_keys=[conflict_with_unit_id])
