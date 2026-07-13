import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.room_frontend import AvailabilitySearchResponse, RoomAvailabilityGrid
from app.services.availability_service import availability_for_room, search_availability_multi
from app.services.policy_service import get_booking_policy
from app.services.room_browse_service import normalize_unit_type_filter
from app.utils.query_params import parse_comma_separated_ints

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("/search", response_model=AvailabilitySearchResponse)
async def search(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    date: dt.date = Query(..., alias="date"),
    capacity: int | None = Query(None, ge=1),
    amenities: str | None = Query(None, description="Comma-separated amenity ids"),
    unit_type: str | None = Query(None),
    start_time: dt.time | None = Query(None, description="Optional: limit slots overlapping this range"),
    end_time: dt.time | None = Query(None),
) -> AvailabilitySearchResponse:
    norm = normalize_unit_type_filter(unit_type)
    if norm == "__invalid__":
        raise HTTPException(status_code=400, detail="Invalid unit_type")
    policy = await get_booking_policy(db)
    grids = await search_availability_multi(
        db,
        day=date,
        capacity=capacity,
        amenity_ids=parse_comma_separated_ints(amenities, param_name="amenities"),
        unit_type=norm,
        slot_filter_start=start_time,
        slot_filter_end=end_time,
        user=user,
    )
    return AvailabilitySearchResponse(
        date=date,
        slot_minutes=policy.slot_minutes,
        rooms=grids,
    )


@router.get("/rooms/{room_id}", response_model=RoomAvailabilityGrid)
async def room_availability(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    date: dt.date = Query(..., alias="date"),
) -> RoomAvailabilityGrid:
    from app.services.tag_visibility_service import room_visible_to_user

    if not await room_visible_to_user(db, room_id=room_id, user=user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    grid = await availability_for_room(db, room_id=room_id, day=date)
    if grid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return grid
