from datetime import date

import pytest
from httpx import AsyncClient

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.booking_policy import BookingPolicy
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User


@pytest.mark.asyncio
async def test_my_bookings_includes_unit_name(client: AsyncClient) -> None:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(
                BookingPolicy(
                    slot_minutes=30,
                    max_booking_hours_per_day=8,
                    max_advance_days=30,
                    cancellation_cutoff_minutes=0,
                )
            )
            user = User(
                email="booker@uni-marburg.de",
                full_name="Booker",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            room = Room(name="Study Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(
                room_id=room.id,
                name="Table A",
                type="table",
                capacity=2,
                is_active=True,
                booking_mode="direct",
            )
            db.add(unit)
            await db.flush()
            user_id, room_id, unit_id = user.id, room.id, unit.id

    headers = {"Authorization": f"Bearer {create_access_token(str(user_id))}"}
    created = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_id,
            "unit_id": unit_id,
            "booking_date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
        headers=headers,
    )
    assert created.status_code == 201

    listed = await client.get("/api/v1/users/me/bookings", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["room_name"] == "Study Room"
    assert body["items"][0]["unit_name"] == "Table A"
