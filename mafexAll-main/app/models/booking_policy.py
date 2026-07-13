from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BookingPolicy(Base):
    __tablename__ = "booking_policy"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_booking_hours_per_day: Mapped[int] = mapped_column(Integer, default=8)
    max_advance_days: Mapped[int] = mapped_column(Integer, default=30)
    cancellation_cutoff_minutes: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
