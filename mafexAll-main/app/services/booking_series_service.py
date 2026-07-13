from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import BookingStatus
from app.models.booking import Booking
from app.models.booking_series import BookingSeries
from app.models.room import Room
from app.models.room_admin import RoomAdmin
from app.models.unit import BookableUnit
from app.models.user import User
from app.schemas.booking import BookingOut
from app.schemas.booking_series import (
    AdminBookingDetailOut,
    AdminBookingListItem,
    AdminBookingSeriesDetailOut,
    BookingSeriesCancelBody,
    BookingSeriesCancelOut,
    BookingSeriesCreate,
    BookingSeriesOut,
    BookingSeriesPreviewOut,
    BookingSeriesRescheduleBody,
    BookingSeriesRescheduleOut,
    SeriesSkippedItem,
)
from app.services.booking_email_service import send_booking_confirmation_email
from app.services.booking_service import (
    BookingError,
    _assert_can_modify_booking,
    apply_booking_slot_update,
    build_booking_for_slot,
    cancel_booking,
)
from app.services.booking_service import (
    approve_pending_booking,
    deny_pending_booking,
)
from app.services.policy_service import get_booking_policy
from app.services.room_admin_service import can_manage_room, is_room_admin

MAX_SERIES_CANDIDATES = 52


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def expand_occurrence_dates(
    *,
    series_start_date: date,
    frequency: str,
    interval: int,
    end_date: date | None,
    max_occurrences: int | None,
) -> list[date]:
    dates: list[date] = []
    if frequency == "weekly":
        current = series_start_date
        while len(dates) < MAX_SERIES_CANDIDATES:
            if end_date and current > end_date:
                break
            if max_occurrences and len(dates) >= max_occurrences:
                break
            dates.append(current)
            current += timedelta(days=7 * interval)
    elif frequency == "monthly":
        step = 0
        while len(dates) < MAX_SERIES_CANDIDATES:
            current = series_start_date if step == 0 else _add_months(series_start_date, step * interval)
            if end_date and current > end_date:
                break
            if max_occurrences and len(dates) >= max_occurrences:
                break
            dates.append(current)
            step += 1
    return dates


async def _assert_series_access(db: AsyncSession, *, actor: User, series: BookingSeries) -> None:
    if series.user_id == actor.id:
        return
    if actor.role == "admin":
        return
    if await is_room_admin(db, room_id=series.room_id, user_id=actor.id):
        return
    raise BookingError("forbidden", "Not allowed", 403)


async def _load_series_names(
    db: AsyncSession, series_rows: list[BookingSeries]
) -> tuple[dict[int, str], dict[int, str]]:
    if not series_rows:
        return {}, {}
    room_ids = {s.room_id for s in series_rows}
    unit_ids = {s.unit_id for s in series_rows}
    room_rows = await db.execute(select(Room.id, Room.name).where(Room.id.in_(room_ids)))
    unit_rows = await db.execute(select(BookableUnit.id, BookableUnit.name).where(BookableUnit.id.in_(unit_ids)))
    return (
        {rid: name for rid, name in room_rows.all()},
        {uid: name for uid, name in unit_rows.all()},
    )


def _series_to_out(
    series: BookingSeries,
    *,
    room_name: str,
    unit_name: str,
    bookings: list[Booking],
    skipped: list[SeriesSkippedItem] | None = None,
) -> BookingSeriesOut:
    return BookingSeriesOut(
        id=series.id,
        user_id=series.user_id,
        room_id=series.room_id,
        room_name=room_name,
        unit_id=series.unit_id,
        unit_name=unit_name,
        start_time=series.start_time,
        end_time=series.end_time,
        frequency=series.frequency,
        interval=series.interval,
        weekday=series.weekday,
        series_start_date=series.series_start_date,
        end_date=series.end_date,
        max_occurrences=series.max_occurrences,
        purpose=series.purpose,
        created_at=series.created_at,
        created_count=len(bookings),
        skipped_count=len(skipped or []),
        bookings=[BookingOut.model_validate(b) for b in bookings],
        skipped=skipped or [],
    )


async def _evaluate_series_date(
    db: AsyncSession,
    *,
    user: User,
    body: BookingSeriesCreate,
    occurrence_date: date,
    max_day: date,
    series_id: int | None = None,
    occurrence_index: int | None = None,
) -> tuple[Booking | None, str | None]:
    if occurrence_date > max_day:
        return None, "beyond_advance_window"
    if occurrence_date < datetime.now(timezone.utc).date():
        return None, "past_date"
    try:
        booking = await build_booking_for_slot(
            db,
            user=user,
            room_id=body.room_id,
            unit_id=body.unit_id,
            booking_date=occurrence_date,
            start_time=body.start_time,
            end_time=body.end_time,
            purpose=body.purpose,
            series_id=series_id,
            occurrence_index=occurrence_index,
        )
        return booking, None
    except BookingError as exc:
        return None, exc.code


async def preview_booking_series(
    db: AsyncSession,
    *,
    user: User,
    body: BookingSeriesCreate,
) -> BookingSeriesPreviewOut:
    policy = await get_booking_policy(db)
    today = datetime.now(timezone.utc).date()
    max_day = today + timedelta(days=policy.max_advance_days)
    candidates = expand_occurrence_dates(
        series_start_date=body.booking_date,
        frequency=body.frequency,
        interval=body.interval,
        end_date=body.end_date,
        max_occurrences=body.max_occurrences,
    )
    bookable: list[date] = []
    skipped: list[SeriesSkippedItem] = []
    for idx, occurrence_date in enumerate(candidates):
        _, reason = await _evaluate_series_date(
            db,
            user=user,
            body=body,
            occurrence_date=occurrence_date,
            max_day=max_day,
            occurrence_index=idx + 1,
        )
        if reason:
            skipped.append(SeriesSkippedItem(date=occurrence_date, reason=reason))
        else:
            bookable.append(occurrence_date)
    return BookingSeriesPreviewOut(total_candidates=len(candidates), bookable=bookable, skipped=skipped)


async def create_booking_series(
    db: AsyncSession,
    *,
    user: User,
    body: BookingSeriesCreate,
) -> BookingSeriesOut:
    policy = await get_booking_policy(db)
    today = datetime.now(timezone.utc).date()
    max_day = today + timedelta(days=policy.max_advance_days)
    candidates = expand_occurrence_dates(
        series_start_date=body.booking_date,
        frequency=body.frequency,
        interval=body.interval,
        end_date=body.end_date,
        max_occurrences=body.max_occurrences,
    )

    series = BookingSeries(
        user_id=user.id,
        room_id=body.room_id,
        unit_id=body.unit_id,
        start_time=body.start_time,
        end_time=body.end_time,
        frequency=body.frequency,
        interval=body.interval,
        weekday=body.booking_date.weekday(),
        series_start_date=body.booking_date,
        end_date=body.end_date,
        max_occurrences=body.max_occurrences,
        purpose=body.purpose,
    )
    db.add(series)
    await db.flush()

    created: list[Booking] = []
    skipped: list[SeriesSkippedItem] = []
    for idx, occurrence_date in enumerate(candidates):
        booking, reason = await _evaluate_series_date(
            db,
            user=user,
            body=body,
            occurrence_date=occurrence_date,
            max_day=max_day,
            series_id=series.id,
            occurrence_index=idx + 1,
        )
        if reason or booking is None:
            skipped.append(SeriesSkippedItem(date=occurrence_date, reason=reason or "unknown"))
            continue
        db.add(booking)
        await db.flush()
        created.append(booking)
        if booking.status == BookingStatus.confirmed.value:
            try:
                await send_booking_confirmation_email(db, booking=booking)
            except Exception:
                pass

    if not created:
        raise BookingError("no_bookings_created", "No dates could be booked for this series", 409)

    await db.refresh(series)
    room = await db.get(Room, series.room_id)
    unit = await db.get(BookableUnit, series.unit_id)
    room_name = room.name if room is not None else f"Room #{series.room_id}"
    unit_name = unit.name if unit is not None else f"Unit #{series.unit_id}"
    return _series_to_out(
        series,
        room_name=room_name,
        unit_name=unit_name,
        bookings=created,
        skipped=skipped,
    )


async def cancel_booking_series(
    db: AsyncSession,
    *,
    actor: User,
    series_id: int,
    body: BookingSeriesCancelBody,
    as_admin: bool = False,
) -> BookingSeriesCancelOut:
    series = await db.get(BookingSeries, series_id)
    if series is None:
        raise BookingError("not_found", "Series not found", 404)
    await _assert_series_access(db, actor=actor, series=series)

    today = datetime.now(timezone.utc).date()
    stmt = select(Booking).where(
        Booking.series_id == series_id,
        Booking.status.in_([BookingStatus.confirmed.value, BookingStatus.pending.value]),
    )
    if body.scope == "all_future":
        stmt = stmt.where(Booking.booking_date >= today)
    elif body.scope == "from_date":
        assert body.from_date is not None
        stmt = stmt.where(Booking.booking_date >= body.from_date)

    r = await db.execute(stmt.order_by(Booking.booking_date.asc()))
    targets = list(r.scalars().all())
    cancelled_ids: list[int] = []
    for booking in targets:
        bypass_cutoff = await can_manage_room(db, actor=actor, room_id=booking.room_id)
        try:
            await cancel_booking(
                db,
                user=actor,
                booking_id=booking.id,
                reason=body.reason,
                as_admin=bypass_cutoff,
            )
            cancelled_ids.append(booking.id)
        except BookingError:
            continue
    return BookingSeriesCancelOut(cancelled_count=len(cancelled_ids), cancelled_booking_ids=cancelled_ids)


async def reschedule_booking_series(
    db: AsyncSession,
    *,
    actor: User,
    series_id: int,
    body: BookingSeriesRescheduleBody,
    as_admin: bool = False,
) -> BookingSeriesRescheduleOut:
    series = await db.get(BookingSeries, series_id)
    if series is None:
        raise BookingError("not_found", "Series not found", 404)
    await _assert_series_access(db, actor=actor, series=series)

    anchor = await db.get(Booking, body.anchor_booking_id)
    if anchor is None or anchor.series_id != series_id:
        raise BookingError("invalid_anchor", "Anchor booking not in this series", 400)

    today = datetime.now(timezone.utc).date()
    stmt = select(Booking).where(
        Booking.series_id == series_id,
        Booking.status.in_([BookingStatus.confirmed.value, BookingStatus.pending.value]),
    )
    if body.scope == "all_future":
        stmt = stmt.where(Booking.booking_date >= today)
    elif body.scope == "from_date":
        stmt = stmt.where(Booking.booking_date >= anchor.booking_date)

    r = await db.execute(stmt.order_by(Booking.booking_date.asc()))
    targets = list(r.scalars().all())
    if not targets:
        raise BookingError("no_targets", "No bookings to reschedule in this scope", 400)

    unit = await db.get(BookableUnit, body.unit_id)
    if unit is None or not unit.is_active:
        raise BookingError("unit_invalid", "Bookable unit not valid", 400)

    updated_ids: list[int] = []
    skipped = 0
    new_purpose = body.purpose if body.purpose is not None else series.purpose

    for booking in targets:
        owner = await db.get(User, booking.user_id)
        if owner is None:
            skipped += 1
            continue
        try:
            staff_edit, is_room_mgr = await _assert_can_modify_booking(
                db, actor=actor, booking=booking, as_admin=as_admin
            )
            await apply_booking_slot_update(
                db,
                booking=booking,
                owner=owner,
                unit_id=body.unit_id,
                booking_date=booking.booking_date,
                start_time=body.start_time,
                end_time=body.end_time,
                purpose=new_purpose,
                staff_edit=staff_edit,
                is_room_mgr=is_room_mgr,
            )
            updated_ids.append(booking.id)
        except BookingError:
            skipped += 1
            continue

    if not updated_ids:
        raise BookingError("no_updates", "No bookings could be rescheduled", 409)

    series.unit_id = body.unit_id
    series.room_id = unit.room_id
    series.start_time = body.start_time
    series.end_time = body.end_time
    series.purpose = new_purpose
    await db.flush()

    return BookingSeriesRescheduleOut(
        updated_count=len(updated_ids),
        updated_booking_ids=updated_ids,
        skipped_count=skipped,
    )


async def list_user_booking_series(db: AsyncSession, *, user_id: int) -> list[BookingSeriesOut]:
    r = await db.execute(
        select(BookingSeries)
        .where(BookingSeries.user_id == user_id)
        .order_by(BookingSeries.created_at.desc())
    )
    series_rows = list(r.scalars().all())
    if not series_rows:
        return []

    series_ids = [s.id for s in series_rows]
    br = await db.execute(
        select(Booking)
        .where(Booking.series_id.in_(series_ids))
        .order_by(Booking.occurrence_index.asc())
    )
    bookings_by_series: dict[int, list[Booking]] = {}
    for booking in br.scalars().all():
        if booking.series_id is not None:
            bookings_by_series.setdefault(booking.series_id, []).append(booking)

    room_names, unit_names = await _load_series_names(db, series_rows)

    return [
        _series_to_out(
            series,
            room_name=room_names.get(series.room_id, f"Room #{series.room_id}"),
            unit_name=unit_names.get(series.unit_id, f"Unit #{series.unit_id}"),
            bookings=bookings_by_series.get(series.id, []),
        )
        for series in series_rows
    ]


def _booking_to_admin_item(
    booking: Booking,
    *,
    user: User,
    room: Room,
    unit: BookableUnit,
    series: BookingSeries | None = None,
) -> AdminBookingListItem:
    return AdminBookingListItem(
        id=booking.id,
        user_id=user.id,
        user_email=user.email,
        user_full_name=user.full_name,
        room_id=room.id,
        room_name=room.name,
        unit_id=unit.id,
        unit_name=unit.name,
        booking_date=booking.booking_date,
        start_time=booking.start_time,
        end_time=booking.end_time,
        status=booking.status,
        purpose=booking.purpose,
        series_id=booking.series_id,
        occurrence_index=booking.occurrence_index,
        series_frequency=series.frequency if series else None,
        series_interval=series.interval if series else None,
    )


async def _allowed_room_ids(db: AsyncSession, actor: User) -> set[int] | None:
    if actor.role == "admin":
        return None
    r = await db.execute(select(RoomAdmin.room_id).where(RoomAdmin.user_id == actor.id))
    return set(r.scalars().all())


async def list_bookings_for_admin(
    db: AsyncSession,
    *,
    actor: User,
    date_from: date | None = None,
    date_to: date | None = None,
    room_id: int | None = None,
    status: str | None = None,
    user_q: str | None = None,
    series_id: int | None = None,
    booking_kind: str | None = None,
    upcoming_only: bool = False,
    past_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[AdminBookingListItem]:
    allowed = await _allowed_room_ids(db, actor)
    if allowed is not None and not allowed:
        return []

    stmt = (
        select(Booking, User, Room, BookableUnit, BookingSeries)
        .join(User, Booking.user_id == User.id)
        .join(Room, Booking.room_id == Room.id)
        .join(BookableUnit, Booking.unit_id == BookableUnit.id)
        .outerjoin(BookingSeries, Booking.series_id == BookingSeries.id)
        .order_by(Booking.booking_date.desc(), Booking.start_time.desc())
    )
    if allowed is not None:
        stmt = stmt.where(Booking.room_id.in_(allowed))
    if room_id is not None:
        if allowed is not None and room_id not in allowed:
            raise BookingError("forbidden", "Not allowed for this room", 403)
        stmt = stmt.where(Booking.room_id == room_id)
    if status is not None:
        stmt = stmt.where(Booking.status == status)
    if series_id is not None:
        stmt = stmt.where(Booking.series_id == series_id)
    if booking_kind == "single":
        stmt = stmt.where(Booking.series_id.is_(None))
    elif booking_kind == "series":
        stmt = stmt.where(Booking.series_id.is_not(None))
    if user_q:
        pattern = f"%{user_q.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    today = datetime.now(timezone.utc).date()
    if upcoming_only:
        stmt = stmt.where(Booking.booking_date >= today)
    if past_only:
        stmt = stmt.where(Booking.booking_date < today)
    if date_from is not None:
        stmt = stmt.where(Booking.booking_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Booking.booking_date <= date_to)

    r = await db.execute(stmt.offset(skip).limit(limit))
    return [
        _booking_to_admin_item(booking, user=user, room=room, unit=unit, series=series)
        for booking, user, room, unit, series in r.all()
    ]


async def get_admin_booking_detail(db: AsyncSession, *, actor: User, booking_id: int) -> AdminBookingDetailOut:
    r = await db.execute(
        select(Booking, User, Room, BookableUnit, BookingSeries)
        .join(User, Booking.user_id == User.id)
        .join(Room, Booking.room_id == Room.id)
        .join(BookableUnit, Booking.unit_id == BookableUnit.id)
        .outerjoin(BookingSeries, Booking.series_id == BookingSeries.id)
        .where(Booking.id == booking_id)
    )
    row = r.one_or_none()
    if row is None:
        raise BookingError("not_found", "Booking not found", 404)
    booking, user, room, unit, series = row
    allowed = await _allowed_room_ids(db, actor)
    if allowed is not None and booking.room_id not in allowed:
        raise BookingError("forbidden", "Not allowed", 403)
    base = _booking_to_admin_item(booking, user=user, room=room, unit=unit, series=series)
    return AdminBookingDetailOut(
        **base.model_dump(),
        room_location=room.location,
        cancellation_reason=booking.cancellation_reason,
        created_at=booking.created_at,
    )


async def get_admin_booking_series_detail(
    db: AsyncSession,
    *,
    actor: User,
    series_id: int,
) -> AdminBookingSeriesDetailOut:
    series = await db.get(BookingSeries, series_id)
    if series is None:
        raise BookingError("not_found", "Series not found", 404)
    await _assert_series_access(db, actor=actor, series=series)

    r = await db.execute(
        select(Booking, User, Room, BookableUnit)
        .join(User, Booking.user_id == User.id)
        .join(Room, Booking.room_id == Room.id)
        .join(BookableUnit, Booking.unit_id == BookableUnit.id)
        .where(Booking.series_id == series_id)
        .order_by(Booking.occurrence_index.asc(), Booking.booking_date.asc())
    )
    bookings = [
        _booking_to_admin_item(booking, user=user, room=room, unit=unit, series=series)
        for booking, user, room, unit in r.all()
    ]
    booking_rows = await db.execute(select(Booking).where(Booking.series_id == series_id))
    room = await db.get(Room, series.room_id)
    unit = await db.get(BookableUnit, series.unit_id)
    series_out = _series_to_out(
        series,
        room_name=room.name if room is not None else f"Room #{series.room_id}",
        unit_name=unit.name if unit is not None else f"Unit #{series.unit_id}",
        bookings=list(booking_rows.scalars().all()),
    )
    return AdminBookingSeriesDetailOut(series=series_out, bookings=bookings)


async def approve_pending_series(
    db: AsyncSession,
    *,
    actor: User,
    series_id: int,
    reason: str | None,
) -> tuple[int, list[int], int]:
    series = await db.get(BookingSeries, series_id)
    if series is None:
        raise BookingError("not_found", "Series not found", 404)
    if actor.role != "admin" and not await is_room_admin(db, room_id=series.room_id, user_id=actor.id):
        raise BookingError("forbidden", "Not allowed", 403)

    r = await db.execute(
        select(Booking)
        .where(
            Booking.series_id == series_id,
            Booking.status == BookingStatus.pending.value,
        )
        .order_by(Booking.booking_date.asc(), Booking.start_time.asc())
    )
    pending = list(r.scalars().all())
    processed: list[int] = []
    skipped = 0
    for booking in pending:
        try:
            approved = await approve_pending_booking(
                db,
                actor=actor,
                booking_id=booking.id,
                reason=reason,
            )
            processed.append(approved.id)
        except BookingError:
            skipped += 1
    return len(processed), processed, skipped


async def deny_pending_series(
    db: AsyncSession,
    *,
    actor: User,
    series_id: int,
    reason: str | None,
) -> tuple[int, list[int], int]:
    series = await db.get(BookingSeries, series_id)
    if series is None:
        raise BookingError("not_found", "Series not found", 404)
    if actor.role != "admin" and not await is_room_admin(db, room_id=series.room_id, user_id=actor.id):
        raise BookingError("forbidden", "Not allowed", 403)

    r = await db.execute(
        select(Booking)
        .where(
            Booking.series_id == series_id,
            Booking.status == BookingStatus.pending.value,
        )
        .order_by(Booking.booking_date.asc(), Booking.start_time.asc())
    )
    pending = list(r.scalars().all())
    processed: list[int] = []
    for booking in pending:
        denied = await deny_pending_booking(
            db,
            actor=actor,
            booking_id=booking.id,
            reason=reason,
        )
        processed.append(denied.id)
    return len(processed), processed, 0
