from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.room import Room
    from app.models.unit import BookableUnit
    from app.models.user import User


class BookingSeries(Base):
    __tablename__ = "booking_series"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("bookable_units.id", ondelete="CASCADE"))
    start_time: Mapped[time] = mapped_column()
    end_time: Mapped[time] = mapped_column()
    frequency: Mapped[str] = mapped_column(String(16))
    interval: Mapped[int] = mapped_column(Integer, default=1)
    weekday: Mapped[int] = mapped_column(Integer)
    series_start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    room: Mapped["Room"] = relationship()
    unit: Mapped["BookableUnit"] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(back_populates="series")
