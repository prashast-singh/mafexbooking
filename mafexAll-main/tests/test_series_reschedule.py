from datetime import date, time, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.booking import Booking
from app.models.booking_policy import BookingPolicy
from app.models.booking_series import BookingSeries
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User
from app.schemas.booking_series import BookingSeriesCreate, BookingSeriesRescheduleBody
from app.services.booking_series_service import create_booking_series, list_user_booking_series, reschedule_booking_series


async def _setup_series_user(
    *,
    unit2_name: str = "Flex table 2",
) -> tuple[int, int, int, int]:
    """Returns user_id, room_id, unit1_id, unit2_id."""
    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(
                BookingPolicy(
                    slot_minutes=30,
                    max_booking_hours_per_day=8,
                    max_advance_days=60,
                    cancellation_cutoff_minutes=0,
                )
            )
            user = User(
                email="series-reschedule@uni-marburg.de",
                full_name="Series Reschedule",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            room = Room(name="StartupLabs", booking_mode="hybrid", capacity=20, is_active=True)
            db.add(room)
            await db.flush()
            unit1 = BookableUnit(
                room_id=room.id,
                name="Flex table 1",
                type="table",
                capacity=2,
                is_active=True,
                booking_mode="direct",
            )
            unit2 = BookableUnit(
                room_id=room.id,
                name=unit2_name,
                type="table",
                capacity=2,
                is_active=True,
                booking_mode="direct",
            )
            db.add_all([unit1, unit2])
            await db.flush()
            return user.id, room.id, unit1.id, unit2.id


async def _create_weekly_series(
    user_id: int,
    room_id: int,
    unit_id: int,
    *,
    start_offset_days: int = 3,
    max_occurrences: int = 3,
) -> tuple[int, list[int]]:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            r = await db.execute(select(User).where(User.id == user_id))
            user = r.scalar_one()
            start = date.today() + timedelta(days=start_offset_days)
            body = BookingSeriesCreate(
                room_id=room_id,
                unit_id=unit_id,
                booking_date=start,
                start_time=time(10, 0),
                end_time=time(11, 0),
                purpose="Weekly standup",
                frequency="weekly",
                interval=1,
                max_occurrences=max_occurrences,
            )
            created = await create_booking_series(db, user=user, body=body)
            booking_ids = [b.id for b in created.bookings]
            return created.id, booking_ids


async def _noop_email(*args, **kwargs):  # noqa: ANN002, ANN003
    return None


@pytest.mark.asyncio
async def test_series_unit_change_stays_in_series(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", _noop_email)
    monkeypatch.setattr("app.services.booking_service.send_booking_updated_email", _noop_email)

    user_id, room_id, unit1_id, unit2_id = await _setup_series_user()
    series_id, booking_ids = await _create_weekly_series(user_id, room_id, unit1_id)
    headers = {"Authorization": f"Bearer {create_access_token(str(user_id))}"}

    target_id = booking_ids[0]
    updated = await client.patch(
        f"/api/v1/bookings/{target_id}",
        json={"unit_id": unit2_id},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["unit_id"] == unit2_id
    assert updated.json()["series_id"] == series_id

    listed = await client.get("/api/v1/users/me/bookings", headers=headers)
    row = next(i for i in listed.json()["items"] if i["id"] == target_id)
    assert row["unit_name"] == "Flex table 2"
    assert row["series_id"] == series_id


@pytest.mark.asyncio
async def test_series_date_change_detaches(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", _noop_email)
    monkeypatch.setattr("app.services.booking_service.send_booking_updated_email", _noop_email)

    user_id, room_id, unit1_id, unit2_id = await _setup_series_user()
    _, booking_ids = await _create_weekly_series(user_id, room_id, unit1_id)
    headers = {"Authorization": f"Bearer {create_access_token(str(user_id))}"}

    target_id = booking_ids[0]
    new_date = str(date.today() + timedelta(days=4))
    updated = await client.patch(
        f"/api/v1/bookings/{target_id}",
        json={"booking_date": new_date},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["series_id"] is None


@pytest.mark.asyncio
async def test_series_purpose_only_stays_in_series(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", _noop_email)
    monkeypatch.setattr("app.services.booking_service.send_booking_updated_email", _noop_email)

    user_id, room_id, unit1_id, _ = await _setup_series_user()
    series_id, booking_ids = await _create_weekly_series(user_id, room_id, unit1_id)
    headers = {"Authorization": f"Bearer {create_access_token(str(user_id))}"}

    updated = await client.patch(
        f"/api/v1/bookings/{booking_ids[0]}",
        json={"purpose": "One-off topic"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["series_id"] == series_id


@pytest.mark.asyncio
async def test_reschedule_all_future_syncs_series(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", _noop_email)
    monkeypatch.setattr("app.services.booking_service.send_booking_updated_email", _noop_email)

    user_id, room_id, unit1_id, unit2_id = await _setup_series_user()
    series_id, booking_ids = await _create_weekly_series(user_id, room_id, unit1_id, start_offset_days=1)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            r = await db.execute(select(User).where(User.id == user_id))
            user = r.scalar_one()
            out = await reschedule_booking_series(
                db,
                actor=user,
                series_id=series_id,
                body=BookingSeriesRescheduleBody(
                    anchor_booking_id=booking_ids[0],
                    scope="all_future",
                    unit_id=unit2_id,
                    start_time=time(14, 0),
                    end_time=time(15, 0),
                    purpose="Afternoon slot",
                ),
            )
            assert out.updated_count >= 1

        async with db.begin():
            series = await db.get(BookingSeries, series_id)
            assert series is not None
            assert series.unit_id == unit2_id
            assert series.start_time == time(14, 0)
            assert series.end_time == time(15, 0)
            assert series.purpose == "Afternoon slot"

            r = await db.execute(select(Booking).where(Booking.id.in_(out.updated_booking_ids)))
            for booking in r.scalars().all():
                assert booking.unit_id == unit2_id
                assert booking.start_time == time(14, 0)


@pytest.mark.asyncio
async def test_reschedule_from_date_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", _noop_email)
    monkeypatch.setattr("app.services.booking_service.send_booking_updated_email", _noop_email)

    user_id, room_id, unit1_id, unit2_id = await _setup_series_user()
    series_id, booking_ids = await _create_weekly_series(user_id, room_id, unit1_id, max_occurrences=3)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            r = await db.execute(select(User).where(User.id == user_id))
            user = r.scalar_one()
            anchor_id = booking_ids[1]
            anchor = await db.get(Booking, anchor_id)
            assert anchor is not None
            out = await reschedule_booking_series(
                db,
                actor=user,
                series_id=series_id,
                body=BookingSeriesRescheduleBody(
                    anchor_booking_id=anchor_id,
                    scope="from_date",
                    unit_id=unit2_id,
                    start_time=time(15, 0),
                    end_time=time(16, 0),
                ),
            )
            assert out.updated_count >= 1

        async with db.begin():
            r = await db.execute(select(Booking).where(Booking.series_id == series_id))
            rows = list(r.scalars().all())
            first = next(b for b in rows if b.id == booking_ids[0])
            assert first.unit_id == unit1_id
            later = [b for b in rows if b.booking_date >= anchor.booking_date and b.status == "confirmed"]
            assert all(b.unit_id == unit2_id for b in later)


@pytest.mark.asyncio
async def test_booking_series_out_includes_unit_name(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_series_service

    monkeypatch.setattr(booking_series_service, "send_booking_confirmation_email", _noop_email)

    user_id, room_id, unit1_id, _ = await _setup_series_user()
    await _create_weekly_series(user_id, room_id, unit1_id)

    async with AsyncSessionLocal() as db:
        rows = await list_user_booking_series(db, user_id=user_id)
        assert len(rows) == 1
        assert rows[0].room_name == "StartupLabs"
        assert rows[0].unit_name == "Flex table 1"
