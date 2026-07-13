from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.amenity import RoomAmenity
from app.models.room import Room
from app.schemas.room_frontend import RoomBrowsePage, RoomDetailPublic
from app.services.availability_service import filter_rooms_with_available_slot
from app.services.room_browse_service import (
    fetch_rooms_for_browse,
    normalize_unit_type_filter,
    room_to_browse_item,
    room_to_detail_public,
)
from app.utils.query_params import parse_comma_separated_ints

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=RoomBrowsePage)
async def list_rooms(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    capacity: int | None = Query(None, ge=1),
    amenities: str | None = Query(
        None,
        description="Comma-separated amenity ids, e.g. 1,2,3 (room must have all)",
    ),
    unit_type: str | None = Query(
        None,
        description="full_room | half_room | section | table (alias: room → full_room)",
    ),
    date: date | None = Query(None),
    start_time: time | None = Query(None),
    end_time: time | None = Query(None),
    available: bool | None = Query(
        None,
        description="If true with date, start_time, end_time: only rooms with a free unit in that range",
    ),
) -> RoomBrowsePage:
    norm = normalize_unit_type_filter(unit_type)
    if norm == "__invalid__":
        raise HTTPException(status_code=400, detail="Invalid unit_type")
    amenity_ids = parse_comma_separated_ints(amenities, param_name="amenities")
    rooms = await fetch_rooms_for_browse(
        db,
        capacity=capacity,
        amenity_ids=amenity_ids,
        unit_type=norm,
    )

    has_time_range = (
        date is not None and start_time is not None and end_time is not None
    )
    if available is True and not has_time_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date, start_time, and end_time are required when available=true",
        )
    if has_time_range:
        if end_time <= start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time must be after start_time",
            )
        rooms = await filter_rooms_with_available_slot(
            db,
            rooms,
            booking_date=date,
            start_time=start_time,
            end_time=end_time,
            unit_type=norm,
        )

    total = len(rooms)
    offset = (page - 1) * limit
    page_rooms = rooms[offset : offset + limit]
    items = [room_to_browse_item(r) for r in page_rooms]
    return RoomBrowsePage(items=items, total=total, page=page, limit=limit)


@router.get("/{room_id}", response_model=RoomDetailPublic)
async def get_room(room_id: int, db: Annotated[AsyncSession, Depends(get_db)]) -> RoomDetailPublic:
    r = await db.execute(
        select(Room)
        .options(
            selectinload(Room.images),
            selectinload(Room.amenity_links).selectinload(RoomAmenity.amenity),
            selectinload(Room.bookable_units),
        )
        .where(Room.id == room_id, Room.is_active.is_(True))
    )
    room = r.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room_to_detail_public(room)
