from datetime import date, time, timedelta

import pytest
from sqlalchemy import select

from app.core.enums import ApprovalStatus, UserType
from app.db.session import AsyncSessionLocal
from app.models.booking import Booking
from app.models.booking_policy import BookingPolicy
from app.models.booking_series import BookingSeries
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User
from app.schemas.booking_series import BookingSeriesCancelBody, BookingSeriesCreate
from app.services.booking_series_service import (
    cancel_booking_series,
    create_booking_series,
    expand_occurrence_dates,
    preview_booking_series,
)
from app.services.booking_service import BookingError, create_booking


def test_expand_weekly_dates() -> None:
    start = date(2026, 7, 13)  # Monday
    dates = expand_occurrence_dates(
        series_start_date=start,
        frequency="weekly",
        interval=2,
        end_date=None,
        max_occurrences=3,
    )
    assert dates == [start, start + timedelta(days=14), start + timedelta(days=28)]


def test_expand_monthly_dates() -> None:
    start = date(2026, 1, 31)
    dates = expand_occurrence_dates(
        series_start_date=start,
        frequency="monthly",
        interval=1,
        end_date=None,
        max_occurrences=3,
    )
    assert dates[0] == date(2026, 1, 31)
    assert dates[1] == date(2026, 2, 28)
    assert dates[2] == date(2026, 3, 31)


@pytest.mark.asyncio
async def test_create_series_partial_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    async def noop_email(db, *, booking):  # noqa: ANN001
        return None

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", noop_email)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=60))
            u = User(
                email="series@uni-marburg.de",
                full_name="Series User",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="Series Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(room_id=room.id, name="Desk", type="table", capacity=2, is_active=True, booking_mode="direct")
            db.add(unit)
            await db.flush()
            uid, rid, unid = u.id, room.id, unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            start = date.today() + timedelta(days=1)
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=unid,
                booking_date=start,
                start_time=time(10, 0),
                end_time=time(11, 0),
                purpose=None,
            )

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            body = BookingSeriesCreate(
                room_id=rid,
                unit_id=unid,
                booking_date=start,
                start_time=time(10, 0),
                end_time=time(11, 0),
                frequency="weekly",
                interval=1,
                max_occurrences=3,
            )
            preview = await preview_booking_series(db, user=user, body=body)
            assert preview.total_candidates == 3
            assert len(preview.skipped) >= 1
            assert any(s.reason == "overlap" for s in preview.skipped)

            result = await create_booking_series(db, user=user, body=body)
            assert result.created_count >= 1
            assert result.skipped_count >= 1
            assert result.id > 0

        async with db.begin():
            r = await db.execute(select(Booking).where(Booking.series_id.is_not(None)))
            rows = list(r.scalars().all())
            assert len(rows) >= 1


@pytest.mark.asyncio
async def test_cancel_series_from_date(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    async def noop_email(db, *, booking):  # noqa: ANN001
        return None

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", noop_email)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=60))
            u = User(
                email="cancel-series@uni-marburg.de",
                full_name="Cancel Series",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="Cancel Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(room_id=room.id, name="Table", type="table", capacity=2, is_active=True, booking_mode="direct")
            db.add(unit)
            await db.flush()
            uid, rid, unid = u.id, room.id, unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            start = date.today() + timedelta(days=2)
            body = BookingSeriesCreate(
                room_id=rid,
                unit_id=unid,
                booking_date=start,
                start_time=time(12, 0),
                end_time=time(13, 0),
                frequency="weekly",
                interval=1,
                max_occurrences=3,
            )
            created = await create_booking_series(db, user=user, body=body)
            series_id = created.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            second_date = created.bookings[1].booking_date if len(created.bookings) > 1 else start + timedelta(days=7)
            out = await cancel_booking_series(
                db,
                actor=user,
                series_id=series_id,
                body=BookingSeriesCancelBody(scope="from_date", from_date=second_date),
            )
            assert out.cancelled_count >= 1

        async with db.begin():
            r = await db.execute(select(Booking).where(Booking.series_id == series_id))
            rows = list(r.scalars().all())
            cancelled = [b for b in rows if b.status == "cancelled"]
            active = [b for b in rows if b.status == "confirmed"]
            assert len(cancelled) >= 1
            if active:
                assert all(b.booking_date < second_date for b in active)


@pytest.mark.asyncio
async def test_create_series_all_skipped_raises() -> None:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=60))
            u = User(
                email="allskip@uni-marburg.de",
                full_name="All Skip",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="Skip Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(room_id=room.id, name="Desk", type="table", capacity=2, is_active=True, booking_mode="direct")
            db.add(unit)
            await db.flush()
            uid, rid, unid = u.id, room.id, unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            d = date.today() + timedelta(days=40)
            body = BookingSeriesCreate(
                room_id=rid,
                unit_id=unid,
                booking_date=d,
                start_time=time(9, 0),
                end_time=time(10, 0),
                frequency="weekly",
                interval=1,
                max_occurrences=2,
            )
            with pytest.raises(BookingError) as exc:
                await create_booking_series(db, user=user, body=body)
            assert exc.value.code == "no_bookings_created"
