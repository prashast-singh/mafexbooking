from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.booking_series import BookingSeries
    from app.models.room import Room
    from app.models.unit import BookableUnit
    from app.models.user import User


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("bookable_units.id", ondelete="CASCADE"))
    booking_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time(timezone=False))
    end_time: Mapped[time] = mapped_column(Time(timezone=False))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="confirmed")
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    series_id: Mapped[int | None] = mapped_column(ForeignKey("booking_series.id", ondelete="SET NULL"), nullable=True)
    occurrence_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="bookings", foreign_keys=[user_id])
    decided_by: Mapped["User | None"] = relationship(foreign_keys=[decided_by_id])
    cancelled_by: Mapped["User | None"] = relationship(foreign_keys=[cancelled_by_id])
    room: Mapped["Room"] = relationship(back_populates="bookings")
    unit: Mapped["BookableUnit"] = relationship(back_populates="bookings")
    series: Mapped["BookingSeries | None"] = relationship(back_populates="bookings")
