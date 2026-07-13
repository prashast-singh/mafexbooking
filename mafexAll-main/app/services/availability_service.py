from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.unit import BookableUnit
from app.schemas.room_frontend import (
    RoomAvailabilityGrid,
    SlotAvailabilityRow,
    SlotUnitAvailability,
)
from app.models.user import User
from app.services.booking_service import _conflict_peer_unit_ids, _has_overlap
from app.services.policy_service import get_booking_policy
from app.services.room_browse_service import normalize_unit_type_filter, select_rooms_browse_base
from app.services.tag_visibility_service import load_user_tag_ids
from app.utils.slots import combine_utc, iter_window_slot_intervals

# Default daily window when room columns are unset (UTC wall clock, consistent with bookings)
DEFAULT_AVAILABILITY_WINDOW_START = time(8, 0)
DEFAULT_AVAILABILITY_WINDOW_END = time(20, 0)


def room_availability_window(room: Room) -> tuple[time, time]:
    start = room.availability_window_start or DEFAULT_AVAILABILITY_WINDOW_START
    end = room.availability_window_end or DEFAULT_AVAILABILITY_WINDOW_END
    return start, end


async def is_unit_free(
    db: AsyncSession,
    *,
    unit_id: int,
    start_at: datetime,
    end_at: datetime,
) -> bool:
    peer_ids = await _conflict_peer_unit_ids(db, unit_id)
    for uid in {unit_id} | peer_ids:
        if await _has_overlap(db, unit_id=uid, start_at=start_at, end_at=end_at):
            return False
    return True


async def unit_slot_status(
    db: AsyncSession,
    *,
    unit_id: int,
    start_at: datetime,
    end_at: datetime,
) -> tuple[bool, str | None]:
    unit = await db.get(BookableUnit, unit_id)
    if unit is None or not unit.is_active:
        return False, "inactive"
    if await _has_overlap(db, unit_id=unit_id, start_at=start_at, end_at=end_at):
        return False, "booked"
    peer_ids = await _conflict_peer_unit_ids(db, unit_id)
    for pid in peer_ids:
        if await _has_overlap(db, unit_id=pid, start_at=start_at, end_at=end_at):
            return False, "conflict"
    return True, None


async def room_has_any_available_unit(
    db: AsyncSession,
    *,
    room_id: int,
    start_at: datetime,
    end_at: datetime,
) -> bool:
    r = await db.execute(
        select(BookableUnit).where(
            BookableUnit.room_id == room_id,
            BookableUnit.is_active.is_(True),
        )
    )
    for u in r.scalars().all():
        if await is_unit_free(db, unit_id=u.id, start_at=start_at, end_at=end_at):
            return True
    return False


async def room_is_available_for_booking_range(
    db: AsyncSession,
    *,
    room_id: int,
    booking_date: date,
    filter_start: time,
    filter_end: time,
    unit_type: str | None = None,
) -> bool:
    """
    True if the room can host a booking for the entire [filter_start, filter_end) window.

    When browsing without unit_type, a booked full_room over the window blocks the whole room
    (e.g. full room booked 08:00–12:00 → searching 09:00–10:00 does not list the room).
    """
    if filter_end <= filter_start:
        return False

    start_at = combine_utc(booking_date, filter_start)
    end_at = combine_utc(booking_date, filter_end)

    r = await db.execute(
        select(BookableUnit).where(
            BookableUnit.room_id == room_id,
            BookableUnit.is_active.is_(True),
        )
    )
    all_units = list(r.scalars().all())
    if not all_units:
        return False

    candidates = (
        all_units
        if unit_type is None
        else [u for u in all_units if u.type == unit_type]
    )
    if not candidates:
        return False

    # Browsing without unit_type: a blocked full_room hides the whole room.
    if unit_type is None:
        full_room_units = [u for u in all_units if u.type == "full_room"]
        if full_room_units:
            any_full_free = False
            for u in full_room_units:
                if await is_unit_free(
                    db, unit_id=u.id, start_at=start_at, end_at=end_at
                ):
                    any_full_free = True
                    break
            if not any_full_free:
                return False

    for u in candidates:
        if await is_unit_free(db, unit_id=u.id, start_at=start_at, end_at=end_at):
            return True
    return False


async def filter_rooms_with_available_slot(
    db: AsyncSession,
    rooms: list[Room],
    *,
    booking_date: date,
    start_time: time,
    end_time: time,
    unit_type: str | None = None,
) -> list[Room]:
    out: list[Room] = []
    for room in rooms:
        if await room_is_available_for_booking_range(
            db,
            room_id=room.id,
            booking_date=booking_date,
            filter_start=start_time,
            filter_end=end_time,
            unit_type=unit_type,
        ):
            out.append(room)
    return out


def _slot_in_range(
    slot_start: datetime,
    slot_end: datetime,
    filter_start: time | None,
    filter_end: time | None,
) -> bool:
    if filter_start is None or filter_end is None:
        return True
    fs = combine_utc(slot_start.date(), filter_start)
    fe = combine_utc(slot_start.date(), filter_end)
    return slot_start < fe and slot_end > fs


async def build_room_availability_grid(
    db: AsyncSession,
    *,
    room_id: int,
    day: date,
    slot_filter_start: time | None = None,
    slot_filter_end: time | None = None,
) -> RoomAvailabilityGrid | None:
    room = await db.get(Room, room_id)
    if room is None or not room.is_active:
        return None

    policy = await get_booking_policy(db)
    slot_minutes = policy.slot_minutes
    window_start, window_end = room_availability_window(room)
    intervals = iter_window_slot_intervals(
        day, slot_minutes, window_start, window_end
    )

    r = await db.execute(
        select(BookableUnit).where(
            BookableUnit.room_id == room_id,
            BookableUnit.is_active.is_(True),
        ).order_by(BookableUnit.id.asc())
    )
    units = r.scalars().all()

    slot_rows: list[SlotAvailabilityRow] = []
    for s, e in intervals:
        if not _slot_in_range(s, e, slot_filter_start, slot_filter_end):
            continue
        unit_payloads: list[SlotUnitAvailability] = []
        for u in units:
            ok, reason = await unit_slot_status(db, unit_id=u.id, start_at=s, end_at=e)
            unit_payloads.append(
                SlotUnitAvailability(
                    unit_id=u.id,
                    unit_name=u.name,
                    unit_type=u.type,
                    available=ok,
                    reason=None if ok else reason,
                )
            )
        slot_rows.append(
            SlotAvailabilityRow(
                start_time=s.time().replace(tzinfo=None).isoformat(timespec="minutes"),
                end_time=e.time().replace(tzinfo=None).isoformat(timespec="minutes"),
                units=unit_payloads,
            )
        )

    return RoomAvailabilityGrid(
        room_id=room.id,
        room_name=room.name,
        date=day,
        slot_minutes=slot_minutes,
        availability_window_start=window_start.isoformat(timespec="minutes"),
        availability_window_end=window_end.isoformat(timespec="minutes"),
        slots=slot_rows,
    )


async def availability_for_room(
    db: AsyncSession,
    *,
    room_id: int,
    day: date,
) -> RoomAvailabilityGrid | None:
    return await build_room_availability_grid(db, room_id=room_id, day=day)


async def search_availability_multi(
    db: AsyncSession,
    *,
    day: date,
    capacity: int | None,
    amenity_ids: list[int] | None,
    unit_type: str | None,
    slot_filter_start: time | None,
    slot_filter_end: time | None,
    user: User | None = None,
) -> list[RoomAvailabilityGrid]:
    norm = normalize_unit_type_filter(unit_type)
    if norm == "__invalid__":
        return []

    user_tag_ids = None
    if user is not None:
        user_tag_ids = await load_user_tag_ids(db, user.id)

    stmt = select_rooms_browse_base(
        capacity=capacity,
        amenity_ids=amenity_ids,
        unit_type=norm,
        user_tag_ids=user_tag_ids,
    )
    r = await db.execute(stmt)
    rooms = list(r.scalars().unique().all())

    grids: list[RoomAvailabilityGrid] = []
    for room in rooms:
        grid = await build_room_availability_grid(
            db,
            room_id=room.id,
            day=day,
            slot_filter_start=slot_filter_start,
            slot_filter_end=slot_filter_end,
        )
        if grid is not None:
            grids.append(grid)
    return grids


async def search_availability(
    db: AsyncSession,
    *,
    day: date,
    min_capacity: int | None,
    room_id: int | None,
) -> list[dict]:
    """Legacy flat search (slot hits). Kept for backward compatibility."""
    stmt_base = select(Room).where(Room.is_active.is_(True))
    if room_id is not None:
        stmt_base = stmt_base.where(Room.id == room_id)
    r = await db.execute(stmt_base)
    rooms = r.scalars().all()

    policy = await get_booking_policy(db)

    hits: list[dict] = []
    for room in rooms:
        window_start, window_end = room_availability_window(room)
        intervals = iter_window_slot_intervals(
            day, policy.slot_minutes, window_start, window_end
        )
        u_stmt = select(BookableUnit).where(
            BookableUnit.room_id == room.id,
            BookableUnit.is_active.is_(True),
        )
        if min_capacity is not None:
            u_stmt = u_stmt.where(BookableUnit.capacity >= min_capacity)
        ur = await db.execute(u_stmt)
        for u in ur.scalars().all():
            for s, e in intervals:
                if await is_unit_free(db, unit_id=u.id, start_at=s, end_at=e):
                    hits.append(
                        {
                            "room_id": room.id,
                            "room_name": room.name,
                            "unit_id": u.id,
                            "unit_name": u.name,
                            "slot_start": s.time().replace(tzinfo=None).isoformat(timespec="minutes"),
                            "slot_end": e.time().replace(tzinfo=None).isoformat(timespec="minutes"),
                        }
                    )
    return hits
