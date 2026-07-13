from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.room import Room


class Amenity(Base):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    room_links: Mapped[list["RoomAmenity"]] = relationship(back_populates="amenity")


class RoomAmenity(Base):
    __tablename__ = "room_amenities"
    __table_args__ = (UniqueConstraint("room_id", "amenity_id", name="uq_room_amenity"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    amenity_id: Mapped[int] = mapped_column(ForeignKey("amenities.id", ondelete="CASCADE"))

    room: Mapped["Room"] = relationship(back_populates="amenity_links")
    amenity: Mapped[Amenity] = relationship(back_populates="room_links")
