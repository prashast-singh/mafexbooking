from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.amenity import RoomAmenity
    from app.models.booking import Booking
    from app.models.tag import RoomTag
    from app.models.unit import BookableUnit


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    booking_mode: Mapped[str] = mapped_column(String(32))
    availability_window_start: Mapped[time] = mapped_column(Time(), default=time(8, 0))
    availability_window_end: Mapped[time] = mapped_column(Time(), default=time(20, 0))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    images: Mapped[list["RoomImage"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    amenity_links: Mapped[list["RoomAmenity"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    tag_links: Mapped[list["RoomTag"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    bookable_units: Mapped[list["BookableUnit"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="room")


class RoomImage(Base):
    __tablename__ = "room_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    file_url: Mapped[str] = mapped_column(String(1024))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    room: Mapped[Room] = relationship(back_populates="images")
