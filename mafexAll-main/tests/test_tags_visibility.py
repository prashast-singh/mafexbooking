import pytest
from httpx import AsyncClient

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def _user_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


async def _create_tag(client: AsyncClient, admin_headers: dict[str, str], name: str) -> int:
    r = await client.post(
        "/api/v1/admin/tags",
        json={"name": name},
        headers=admin_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_room(client: AsyncClient, admin_headers: dict[str, str], name: str) -> int:
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": name, "booking_mode": "hybrid", "capacity": 4},
        headers=admin_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_tag_crud(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    created = await client.post(
        "/api/v1/admin/tags",
        json={"name": "Physics", "description": "Physics dept"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    tid = created.json()["id"]

    listed = await client.get("/api/v1/tags")
    assert listed.status_code == 200
    assert any(t["id"] == tid for t in listed.json())

    patched = await client.patch(
        f"/api/v1/admin/tags/{tid}",
        json={"description": "Updated"},
        headers=admin_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "Updated"

    deleted = await client.delete(f"/api/v1/admin/tags/{tid}", headers=admin_headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_tag_visibility_rules(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    tag_a = await _create_tag(client, admin_headers, "DeptA")
    tag_b = await _create_tag(client, admin_headers, "DeptB")
    room_tagged_a = await _create_room(client, admin_headers, "RoomA")
    room_tagged_b = await _create_room(client, admin_headers, "RoomB")
    room_untagged = await _create_room(client, admin_headers, "RoomPublic")

    await client.post(
        f"/api/v1/admin/rooms/{room_tagged_a}/tags",
        json={"tag_id": tag_a},
        headers=admin_headers,
    )
    await client.post(
        f"/api/v1/admin/rooms/{room_tagged_b}/tags",
        json={"tag_id": tag_b},
        headers=admin_headers,
    )

    async with AsyncSessionLocal() as db:
        async with db.begin():
            u = User(
                email="tagged@uni-marburg.de",
                full_name="Tagged User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            uid = u.id

    await client.patch(
        f"/api/v1/admin/users/{uid}/tags",
        json={"tag_ids": [tag_a]},
        headers=admin_headers,
    )
    headers = await _user_headers(uid)

    browse = await client.get("/api/v1/rooms", headers=headers)
    assert browse.status_code == 200
    names = {item["name"] for item in browse.json()["items"]}
    assert "RoomA" in names
    assert "RoomB" not in names
    assert "RoomPublic" not in names

    detail_untagged = await client.get(f"/api/v1/rooms/{room_untagged}", headers=headers)
    assert detail_untagged.status_code == 404

    async with AsyncSessionLocal() as db:
        async with db.begin():
            u2 = User(
                email="untagged@uni-marburg.de",
                full_name="Untagged User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u2)
            await db.flush()
            uid2 = u2.id

    headers2 = await _user_headers(uid2)
    browse2 = await client.get("/api/v1/rooms", headers=headers2)
    names2 = {item["name"] for item in browse2.json()["items"]}
    assert "RoomA" in names2
    assert "RoomB" in names2
    assert "RoomPublic" in names2


@pytest.mark.asyncio
async def test_tagged_user_cannot_book_invisible_room(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    from datetime import date, time, timedelta

    from app.models.booking_policy import BookingPolicy
    from app.db.session import AsyncSessionLocal

    tag_a = await _create_tag(client, admin_headers, "BookTagA")
    room_visible = await _create_room(client, admin_headers, "BookRoomVisible")
    room_hidden = await _create_room(client, admin_headers, "BookRoomHidden")

    await client.post(
        f"/api/v1/admin/rooms/{room_visible}/tags",
        json={"tag_id": tag_a},
        headers=admin_headers,
    )

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
            u = User(
                email="booktag@uni-marburg.de",
                full_name="Book Tag User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            uid = u.id

    unit_visible = await client.post(
        f"/api/v1/admin/rooms/{room_visible}/bookable-units",
        json={"name": "Desk", "type": "table", "capacity": 2, "booking_mode": "direct"},
        headers=admin_headers,
    )
    unit_hidden = await client.post(
        f"/api/v1/admin/rooms/{room_hidden}/bookable-units",
        json={"name": "Desk", "type": "table", "capacity": 2, "booking_mode": "direct"},
        headers=admin_headers,
    )
    assert unit_visible.status_code == 201
    assert unit_hidden.status_code == 201

    await client.patch(
        f"/api/v1/admin/users/{uid}/tags",
        json={"tag_ids": [tag_a]},
        headers=admin_headers,
    )
    headers = await _user_headers(uid)
    booking_date = str(date.today() + timedelta(days=1))

    blocked = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_hidden,
            "unit_id": unit_hidden.json()["id"],
            "booking_date": booking_date,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
        headers=headers,
    )
    assert blocked.status_code == 404

    allowed = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": room_visible,
            "unit_id": unit_visible.json()["id"],
            "booking_date": booking_date,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
        headers=headers,
    )
    assert allowed.status_code == 201
