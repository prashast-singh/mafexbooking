from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.booking_policy import BookingPolicy
from app.models.user import User
from app.services.booking_service import create_booking
from app.services.room_admin_service import add_room_admin


@pytest.mark.asyncio
async def test_room_admin_lists_and_cancels_room_bookings(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Managed Room", "booking_mode": "hybrid", "capacity": 4},
        headers=admin_headers,
    )
    rid = room.json()["id"]
    unit = await client.post(
        f"/api/v1/admin/rooms/{rid}/bookable-units",
        json={"name": "Desk", "type": "table", "capacity": 2, "booking_mode": "direct"},
        headers=admin_headers,
    )
    uid = unit.json()["id"]

    async with AsyncSessionLocal() as db:
        async with db.begin():
            if (await db.execute(select(BookingPolicy).limit(1))).scalar_one_or_none() is None:
                db.add(
                    BookingPolicy(
                        slot_minutes=30,
                        max_booking_hours_per_day=8,
                        max_advance_days=30,
                        cancellation_cutoff_minutes=60,
                    )
                )
            booker = User(
                email="booker-room-admin@example.com",
                full_name="Booker",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            room_admin = User(
                email="roomadmin@example.com",
                full_name="Room Admin",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(booker)
            db.add(room_admin)
            await db.flush()
            booker_id = booker.id
            room_admin_id = room_admin.id
            await add_room_admin(db, room_id=rid, user_id=room_admin_id)
            d = date.today()
            booking = await create_booking(
                db,
                user=booker,
                room_id=rid,
                unit_id=uid,
                booking_date=d,
                start_time=time(14, 0),
                end_time=time(14, 30),
                purpose="Team meeting",
            )
            booking_id = booking.id

    room_admin_headers = {"Authorization": f"Bearer {create_access_token(str(room_admin_id))}"}
    me = await client.get("/api/v1/users/me", headers=room_admin_headers)
    assert me.status_code == 200
    assert rid in me.json()["managed_room_ids"]

    managed = await client.get("/api/v1/users/me/managed-rooms", headers=room_admin_headers)
    assert managed.status_code == 200
    assert managed.json() == [{"id": rid, "name": "Managed Room"}]

    listed = await client.get("/api/v1/admin/bookings", headers=room_admin_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["id"] == booking_id
    assert body[0]["room_name"] == "Managed Room"

    cancelled = await client.patch(
        f"/api/v1/admin/bookings/{booking_id}/cancel",
        headers=room_admin_headers,
        json={},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    listed_after = await client.get("/api/v1/admin/bookings", headers=room_admin_headers, params={"status": "cancelled"})
    assert listed_after.status_code == 200
    assert any(row["id"] == booking_id for row in listed_after.json())

    other_room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Other Room", "booking_mode": "hybrid", "capacity": 2},
        headers=admin_headers,
    )
    other_rid = other_room.json()["id"]
    forbidden = await client.get("/api/v1/admin/bookings", headers=room_admin_headers, params={"room_id": other_rid})
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_admin_bookings_booking_kind_filter(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    from app.core.security import create_access_token

    room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Kind Filter Room", "booking_mode": "hybrid", "capacity": 4},
        headers=admin_headers,
    )
    rid = room.json()["id"]
    unit = await client.post(
        f"/api/v1/admin/rooms/{rid}/bookable-units",
        json={"name": "Desk", "type": "table", "capacity": 2, "booking_mode": "direct"},
        headers=admin_headers,
    )
    uid = unit.json()["id"]

    async with AsyncSessionLocal() as db:
        async with db.begin():
            if (await db.execute(select(BookingPolicy).limit(1))).scalar_one_or_none() is None:
                db.add(
                    BookingPolicy(
                        slot_minutes=30,
                        max_booking_hours_per_day=8,
                        max_advance_days=30,
                        cancellation_cutoff_minutes=60,
                    )
                )
            user = User(
                email="kindfilter@example.com",
                full_name="Kind Filter User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            uid_user = user.id
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=uid,
                booking_date=date.today(),
                start_time=time(9, 0),
                end_time=time(9, 30),
                purpose=None,
            )

    user_headers = {"Authorization": f"Bearer {create_access_token(str(uid_user))}"}
    series = await client.post(
        "/api/v1/bookings/series",
        json={
            "room_id": rid,
            "unit_id": uid,
            "booking_date": date.today().isoformat(),
            "start_time": "10:00",
            "end_time": "10:30",
            "frequency": "weekly",
            "interval": 1,
            "max_occurrences": 2,
        },
        headers=user_headers,
    )
    assert series.status_code == 201
    series_id = series.json()["id"]

    singles = await client.get("/api/v1/admin/bookings", headers=admin_headers, params={"booking_kind": "single"})
    assert singles.status_code == 200
    assert all(row["series_id"] is None for row in singles.json())

    series_rows = await client.get(
        "/api/v1/admin/bookings",
        headers=admin_headers,
        params={"booking_kind": "series", "series_id": series_id},
    )
    assert series_rows.status_code == 200
    assert len(series_rows.json()) >= 1
    assert all(row["series_id"] == series_id for row in series_rows.json())
