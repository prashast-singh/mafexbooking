from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApprovalStatus, BookingStatus
from app.models.booking import Booking
from app.models.room import Room
from app.models.unit import BookableUnit, UnitConflict
from app.models.user import User
from app.services.booking_email_service import (
    send_booking_cancellation_email,
    send_booking_confirmation_email,
    send_booking_denial_email,
    send_booking_updated_email,
)
from app.services.email_service import send_plain_email
from app.services.policy_service import get_booking_policy
from app.services.room_admin_service import can_manage_room, is_room_admin, list_managed_room_ids
from app.utils.slots import combine_utc, duration_minutes, is_slot_aligned


class BookingError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def _conflict_peer_unit_ids(db: AsyncSession, unit_id: int) -> set[int]:
    r1 = await db.execute(
        select(UnitConflict.conflict_with_unit_id).where(UnitConflict.unit_id == unit_id)
    )
    r2 = await db.execute(select(UnitConflict.unit_id).where(UnitConflict.conflict_with_unit_id == unit_id))
    return set(r1.scalars().all()) | set(r2.scalars().all())


async def _has_overlap(
    db: AsyncSession,
    *,
    unit_id: int,
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: int | None = None,
) -> bool:
    stmt = select(Booking.id).where(
        Booking.unit_id == unit_id,
        Booking.status.in_([BookingStatus.confirmed.value, BookingStatus.pending.value]),
        Booking.start_at < end_at,
        Booking.end_at > start_at,
    )
    if exclude_booking_id is not None:
        stmt = stmt.where(Booking.id != exclude_booking_id)
    r = await db.execute(stmt.limit(1))
    return r.scalar_one_or_none() is not None


async def _user_booked_minutes_on_date(
    db: AsyncSession,
    *,
    user_id: int,
    booking_date: date,
    exclude_booking_id: int | None = None,
) -> int:
    stmt = select(Booking).where(
        Booking.user_id == user_id,
        Booking.booking_date == booking_date,
        Booking.status == BookingStatus.confirmed.value,
    )
    if exclude_booking_id is not None:
        stmt = stmt.where(Booking.id != exclude_booking_id)
    r = await db.execute(stmt)
    rows = r.scalars().all()
    total = 0
    for b in rows:
        total += int((b.end_at - b.start_at).total_seconds() // 60)
    return total


async def build_booking_for_slot(
    db: AsyncSession,
    *,
    user: User,
    room_id: int,
    unit_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
    purpose: str | None,
    series_id: int | None = None,
    occurrence_index: int | None = None,
    exclude_booking_id: int | None = None,
) -> Booking:
    if user.approval_status != ApprovalStatus.approved.value:
        raise BookingError("not_approved", "Only approved users can book", 403)

    policy = await get_booking_policy(db)
    slot = policy.slot_minutes

    if not is_slot_aligned(start_time, slot) or not is_slot_aligned(end_time, slot):
        raise BookingError("slot_alignment", f"Times must align to {slot}-minute slots", 400)

    dur = duration_minutes(start_time, end_time)
    if dur <= 0 or dur % slot != 0:
        raise BookingError("invalid_range", "Invalid time range for slot policy", 400)

    start_at = combine_utc(booking_date, start_time)
    end_at = combine_utc(booking_date, end_time)
    if end_at <= start_at:
        raise BookingError("invalid_range", "End must be after start", 400)

    today = datetime.now(timezone.utc).date()
    max_day = today + timedelta(days=policy.max_advance_days)
    if booking_date < today or booking_date > max_day:
        raise BookingError("advance_window", "Booking date outside allowed advance window", 400)

    room = await db.get(Room, room_id)
    if room is None or not room.is_active:
        raise BookingError("room_inactive", "Room not available", 400)

    unit = await db.get(BookableUnit, unit_id)
    if unit is None or not unit.is_active or unit.room_id != room_id:
        raise BookingError("unit_invalid", "Bookable unit not valid for this room", 400)

    peer_ids = await _conflict_peer_unit_ids(db, unit_id)
    all_units_to_check = {unit_id} | peer_ids

    for uid in all_units_to_check:
        if await _has_overlap(
            db,
            unit_id=uid,
            start_at=start_at,
            end_at=end_at,
            exclude_booking_id=exclude_booking_id,
        ):
            raise BookingError("overlap", "Selected slot conflicts with an existing booking", 409)

    new_minutes = dur
    existing_minutes = await _user_booked_minutes_on_date(
        db,
        user_id=user.id,
        booking_date=booking_date,
        exclude_booking_id=exclude_booking_id,
    )
    max_minutes = policy.max_booking_hours_per_day * 60
    if existing_minutes + new_minutes > max_minutes:
        raise BookingError("daily_limit", "Exceeds max booking hours for this day", 400)

    return Booking(
        user_id=user.id,
        room_id=room_id,
        unit_id=unit_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        start_at=start_at,
        end_at=end_at,
        purpose=purpose,
        series_id=series_id,
        occurrence_index=occurrence_index,
        status=(
            BookingStatus.pending.value
            if unit.booking_mode == "request"
            else BookingStatus.confirmed.value
        ),
    )


async def create_booking(
    db: AsyncSession,
    *,
    user: User,
    room_id: int,
    unit_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
    purpose: str | None,
) -> Booking:
    booking = await build_booking_for_slot(
        db,
        user=user,
        room_id=room_id,
        unit_id=unit_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        purpose=purpose,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)
    if booking.status == BookingStatus.confirmed.value:
        try:
            await send_booking_confirmation_email(db, booking=booking)
        except Exception:
            pass
    return booking


async def cancel_booking(
    db: AsyncSession,
    *,
    user: User,
    booking_id: int,
    reason: str | None,
    as_admin: bool = False,
) -> Booking:
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise BookingError("not_found", "Booking not found", 404)
    staff_cancel = as_admin and await can_manage_room(db, actor=user, room_id=booking.room_id)
    if not staff_cancel:
        if booking.user_id != user.id and not await is_room_admin(db, room_id=booking.room_id, user_id=user.id):
            raise BookingError("forbidden", "Not allowed to cancel this booking", 403)
    if booking.status not in (BookingStatus.confirmed.value, BookingStatus.pending.value):
        raise BookingError("invalid_status", "Booking cannot be cancelled", 400)

    policy = await get_booking_policy(db)
    now = datetime.now(timezone.utc)
    start_at = booking.start_at
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    else:
        start_at = start_at.astimezone(timezone.utc)
    cutoff = start_at - timedelta(minutes=policy.cancellation_cutoff_minutes)
    if now > cutoff and not staff_cancel:
        raise BookingError("too_late", "Cancellation cutoff has passed", 400)

    booking.status = BookingStatus.cancelled.value
    booking.cancelled_by_id = user.id
    booking.cancellation_reason = reason
    await db.flush()
    await db.refresh(booking)
    try:
        await send_booking_cancellation_email(db, booking=booking)
    except Exception:
        pass
    return booking


async def update_booking(
    db: AsyncSession,
    *,
    actor: User,
    booking_id: int,
    unit_id: int | None = None,
    booking_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    purpose: str | None = None,
    as_admin: bool = False,
) -> Booking:
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise BookingError("not_found", "Booking not found", 404)

    staff_edit = as_admin and await can_manage_room(db, actor=actor, room_id=booking.room_id)
    is_owner = booking.user_id == actor.id
    is_room_mgr = await is_room_admin(db, room_id=booking.room_id, user_id=actor.id)

    if not staff_edit and not is_owner and not is_room_mgr:
        raise BookingError("forbidden", "Not allowed to modify this booking", 403)

    if booking.status not in (BookingStatus.confirmed.value, BookingStatus.pending.value):
        raise BookingError("invalid_status", "Booking cannot be modified", 400)

    policy = await get_booking_policy(db)
    now = datetime.now(timezone.utc)
    start_at_existing = booking.start_at
    if start_at_existing.tzinfo is None:
        start_at_existing = start_at_existing.replace(tzinfo=timezone.utc)
    else:
        start_at_existing = start_at_existing.astimezone(timezone.utc)
    cutoff = start_at_existing - timedelta(minutes=policy.cancellation_cutoff_minutes)
    if now > cutoff and not staff_edit and not is_room_mgr:
        raise BookingError("too_late", "Modification cutoff has passed", 400)

    owner = await db.get(User, booking.user_id)
    if owner is None:
        raise BookingError("not_found", "Booking owner not found", 404)

    new_unit_id = unit_id if unit_id is not None else booking.unit_id
    new_date = booking_date if booking_date is not None else booking.booking_date
    new_start = start_time if start_time is not None else booking.start_time
    new_end = end_time if end_time is not None else booking.end_time
    new_purpose = purpose if purpose is not None else booking.purpose

    unit = await db.get(BookableUnit, new_unit_id)
    if unit is None:
        raise BookingError("unit_invalid", "Bookable unit not valid", 400)
    new_room_id = unit.room_id

    was_confirmed = booking.status == BookingStatus.confirmed.value

    validated = await build_booking_for_slot(
        db,
        user=owner,
        room_id=new_room_id,
        unit_id=new_unit_id,
        booking_date=new_date,
        start_time=new_start,
        end_time=new_end,
        purpose=new_purpose,
        series_id=booking.series_id,
        occurrence_index=booking.occurrence_index,
        exclude_booking_id=booking.id,
    )

    booking.room_id = validated.room_id
    booking.unit_id = validated.unit_id
    booking.booking_date = validated.booking_date
    booking.start_time = validated.start_time
    booking.end_time = validated.end_time
    booking.start_at = validated.start_at
    booking.end_at = validated.end_at
    booking.purpose = validated.purpose

    if unit.booking_mode == "request":
        booking.status = BookingStatus.pending.value
    elif was_confirmed or staff_edit or is_room_mgr:
        booking.status = BookingStatus.confirmed.value
    else:
        booking.status = validated.status

    await db.flush()
    await db.refresh(booking)

    if booking.status == BookingStatus.confirmed.value:
        try:
            await send_booking_updated_email(db, booking=booking)
        except Exception:
            pass

    return booking


async def list_pending_bookings_for_actor(
    db: AsyncSession,
    *,
    actor: User,
    room_id: int | None,
    skip: int,
    limit: int,
) -> list[Booking]:
    stmt = select(Booking).where(Booking.status == BookingStatus.pending.value).order_by(Booking.created_at.asc())
    if actor.role != "admin":
        managed_room_ids = await list_managed_room_ids(db, user_id=actor.id)
        if not managed_room_ids:
            raise BookingError("forbidden", "Not allowed", 403)
        if room_id is not None:
            if room_id not in managed_room_ids:
                raise BookingError("forbidden", "Not allowed", 403)
            stmt = stmt.where(Booking.room_id == room_id)
        else:
            stmt = stmt.where(Booking.room_id.in_(managed_room_ids))
    elif room_id is not None:
        stmt = stmt.where(Booking.room_id == room_id)
    r = await db.execute(stmt.offset(skip).limit(limit))
    return list(r.scalars().all())


async def approve_pending_booking(
    db: AsyncSession,
    *,
    actor: User,
    booking_id: int,
    reason: str | None,
) -> Booking:
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise BookingError("not_found", "Booking not found", 404)
    if booking.status != BookingStatus.pending.value:
        raise BookingError("invalid_status", "Booking is not pending", 400)
    if actor.role != "admin" and not await is_room_admin(db, room_id=booking.room_id, user_id=actor.id):
        raise BookingError("forbidden", "Not allowed", 403)

    unit_id = booking.unit_id
    peer_ids = await _conflict_peer_unit_ids(db, unit_id)
    all_units = {unit_id} | peer_ids

    # Cancel overlapping confirmed bookings in conflicting units.
    stmt = select(Booking).where(
        Booking.status == BookingStatus.confirmed.value,
        Booking.unit_id.in_(all_units),
        Booking.start_at < booking.end_at,
        Booking.end_at > booking.start_at,
    )
    r = await db.execute(stmt)
    overlaps = list(r.scalars().all())

    for b in overlaps:
        b.status = BookingStatus.cancelled.value
        b.cancelled_by_id = actor.id
        b.cancellation_reason = "Auto-cancelled due to approved conflicting booking"

    booking.status = BookingStatus.confirmed.value
    booking.decided_by_id = actor.id
    booking.decided_at = datetime.now(timezone.utc)
    booking.decision_reason = reason
    await db.flush()
    await db.refresh(booking)

    # Notify impacted users (best-effort).
    # We keep emails plain and robust; failures should not abort approval.
    for b in overlaps:
        try:
            subject = "Booking cancelled"
            body = (
                "Your booking was cancelled because a conflicting booking request was approved.\n\n"
                f"Room ID: {b.room_id}\n"
                f"Unit ID: {b.unit_id}\n"
                f"Date: {b.booking_date}\n"
                f"Time: {str(b.start_time)[:5]}–{str(b.end_time)[:5]}\n\n"
                f"Reason: {b.cancellation_reason}\n"
            )
            user = await db.get(User, b.user_id)
            if user is not None:
                await send_plain_email(user.email, subject, body)
        except Exception:
            # Avoid breaking approval due to email issues.
            pass

    try:
        await send_booking_confirmation_email(db, booking=booking)
    except Exception:
        pass

    return booking


async def deny_pending_booking(
    db: AsyncSession,
    *,
    actor: User,
    booking_id: int,
    reason: str | None,
) -> Booking:
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise BookingError("not_found", "Booking not found", 404)
    if booking.status != BookingStatus.pending.value:
        raise BookingError("invalid_status", "Booking is not pending", 400)
    if actor.role != "admin" and not await is_room_admin(db, room_id=booking.room_id, user_id=actor.id):
        raise BookingError("forbidden", "Not allowed", 403)
    booking.status = BookingStatus.denied.value
    booking.decided_by_id = actor.id
    booking.decided_at = datetime.now(timezone.utc)
    booking.decision_reason = reason
    await db.flush()
    await db.refresh(booking)
    try:
        await send_booking_denial_email(db, booking=booking)
    except Exception:
        pass
    return booking
