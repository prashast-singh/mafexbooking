import pytest
from httpx import AsyncClient

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User


@pytest.mark.asyncio
async def test_cancel_booking_sends_email(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    from app.services import booking_service

    sent: list[int] = []

    async def capture_cancel_email(db, *, booking):  # noqa: ANN001
        sent.append(booking.id)

    monkeypatch.setattr(booking_service, "send_booking_cancellation_email", capture_cancel_email)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            from app.models.booking_policy import BookingPolicy
            from app.models.room import Room
            from app.models.unit import BookableUnit
            from datetime import date, time

            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=0))
            u = User(
                email="cancel@uni-marburg.de",
                full_name="Cancel User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="R-Cancel", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(room_id=room.id, name="Desk", type="table", capacity=2, is_active=True, booking_mode="direct")
            db.add(unit)
            await db.flush()
            uid, rid, unid = u.id, room.id, unit.id

    token = create_access_token(str(uid))
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": rid,
            "unit_id": unid,
            "booking_date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
        headers=headers,
    )
    assert created.status_code == 201
    bid = created.json()["id"]

    cancelled = await client.patch(f"/api/v1/bookings/{bid}/cancel", json={"reason": "Changed plans"}, headers=headers)
    assert cancelled.status_code == 200
    assert len(sent) == 1
    assert sent[0] == bid


@pytest.mark.asyncio
async def test_update_booking_changes_time(client: AsyncClient) -> None:
    from datetime import date, time, timedelta

    async with AsyncSessionLocal() as db:
        async with db.begin():
            from app.models.booking_policy import BookingPolicy
            from app.models.room import Room
            from app.models.unit import BookableUnit

            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=0))
            u = User(
                email="update@uni-marburg.de",
                full_name="Update User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="R-Update", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(room_id=room.id, name="Desk", type="table", capacity=2, is_active=True, booking_mode="direct")
            db.add(unit)
            await db.flush()
            uid, rid, unid = u.id, room.id, unit.id

    token = create_access_token(str(uid))
    headers = {"Authorization": f"Bearer {token}"}
    booking_date = str(date.today() + timedelta(days=1))
    created = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": rid,
            "unit_id": unid,
            "booking_date": booking_date,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
        headers=headers,
    )
    assert created.status_code == 201
    bid = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/bookings/{bid}",
        json={"start_time": "11:00:00", "end_time": "12:00:00"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["start_time"].startswith("11:00")
