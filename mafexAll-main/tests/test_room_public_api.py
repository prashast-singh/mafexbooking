import io
from datetime import date, time

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.db.session import AsyncSessionLocal
from app.models.booking_policy import BookingPolicy
from app.models.user import User
from app.services.booking_service import create_booking
from app.utils.slots import iter_window_slot_intervals


def _png() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(b, format="PNG")
    return b.getvalue()


@pytest.fixture
async def browse_setup(client: AsyncClient, admin_headers: dict[str, str]) -> dict:
    """Room with two amenities, two images (sort_order 2 then 1), one unit."""
    am1 = await client.post(
        "/api/v1/admin/amenities", json={"name": "WB", "icon": "whiteboard"}, headers=admin_headers
    )
    am2 = await client.post(
        "/api/v1/admin/amenities", json={"name": "Mon", "icon": "monitor"}, headers=admin_headers
    )
    id1, id2 = am1.json()["id"], am2.json()["id"]
    room = await client.post(
        "/api/v1/admin/rooms",
        json={
            "name": "Browse Room",
            "booking_mode": "hybrid",
            "capacity": 10,
            "amenity_ids": [id2, id1],
        },
        headers=admin_headers,
    )
    rid = room.json()["id"]
    await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files={"file": ("b.png", _png(), "image/png")},
        data={"sort_order": "2"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files={"file": ("a.png", _png(), "image/png")},
        data={"sort_order": "1"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/v1/admin/rooms/{rid}/bookable-units",
        json={"name": "Full", "type": "full_room", "capacity": 10},
        headers=admin_headers,
    )
    return {"room_id": rid, "amenity_ids": (id1, id2)}


@pytest.mark.asyncio
async def test_room_list_includes_amenities_and_ordered_images(
    client: AsyncClient, browse_setup: dict
) -> None:
    rid = browse_setup["room_id"]
    r = await client.get("/api/v1/rooms")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert body["total"] >= 1
    item = next(x for x in body["items"] if x["id"] == rid)
    assert len(item["amenities"]) == 2
    names = {a["name"] for a in item["amenities"]}
    assert names == {"WB", "Mon"}
    assert all("id" in a and "icon" in a for a in item["amenities"])
    assert len(item["images"]) == 2
    orders = [img["sort_order"] for img in item["images"]]
    assert orders == sorted(orders)


@pytest.mark.asyncio
async def test_room_list_thumbnail_matches_first_ordered_image(
    client: AsyncClient, browse_setup: dict
) -> None:
    rid = browse_setup["room_id"]
    r = await client.get("/api/v1/rooms")
    item = next(x for x in r.json()["items"] if x["id"] == rid)
    first = min(item["images"], key=lambda i: (i["sort_order"], i["id"]))
    assert item["thumbnail_url"] == first["file_url"]


@pytest.mark.asyncio
async def test_room_detail_amenities_images_units(client: AsyncClient, browse_setup: dict) -> None:
    rid = browse_setup["room_id"]
    d = await client.get(f"/api/v1/rooms/{rid}")
    assert d.status_code == 200
    body = d.json()
    assert len(body["amenities"]) == 2
    assert len(body["images"]) == 2
    assert body["thumbnail_url"] is not None
    assert len(body["bookable_units"]) == 1
    u = body["bookable_units"][0]
    assert u["name"] == "Full"
    assert u["type"] == "full_room"
    assert u["parent_unit_id"] is None


@pytest.mark.asyncio
async def test_availability_returns_slot_grid_with_units(client: AsyncClient, browse_setup: dict) -> None:
    rid = browse_setup["room_id"]
    today = date.today().isoformat()
    r = await client.get(f"/api/v1/availability/rooms/{rid}", params={"date": today})
    assert r.status_code == 200
    g = r.json()
    assert g["room_id"] == rid
    assert g["room_name"] == "Browse Room"
    assert g["date"] == today
    assert g["slot_minutes"] == 30
    assert len(g["slots"]) > 0
    slot0 = g["slots"][0]
    assert "start_time" in slot0 and "end_time" in slot0
    assert len(slot0["units"]) == 1
    assert slot0["units"][0]["unit_name"] == "Full"


@pytest.mark.asyncio
async def test_availability_shows_booked_unavailable(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Booked R", "booking_mode": "hybrid", "capacity": 4},
        headers=admin_headers,
    )
    rid = room.json()["id"]
    uresp = await client.post(
        f"/api/v1/admin/rooms/{rid}/bookable-units",
        json={"name": "U1", "type": "table", "capacity": 2},
        headers=admin_headers,
    )
    uid = uresp.json()["id"]
    d = date.today()
    st, et = time(10, 0), time(10, 30)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            pol = await db.execute(select(BookingPolicy).limit(1))
            if pol.scalar_one_or_none() is None:
                db.add(
                    BookingPolicy(
                        slot_minutes=30,
                        max_booking_hours_per_day=8,
                        max_advance_days=30,
                        cancellation_cutoff_minutes=60,
                    )
                )
            user = User(
                email="booker@test.local",
                full_name="B",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=uid,
                booking_date=d,
                start_time=st,
                end_time=et,
                purpose=None,
            )

    r = await client.get(f"/api/v1/availability/rooms/{rid}", params={"date": d.isoformat()})
    grid = r.json()
    hit = next(
        (s for s in grid["slots"] if s["start_time"] == "10:00" and s["end_time"] == "10:30"),
        None,
    )
    assert hit is not None
    u = hit["units"][0]
    assert u["available"] is False
    assert u["reason"] == "booked"


@pytest.mark.asyncio
async def test_availability_conflict_reason(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Conflict R", "booking_mode": "hybrid", "capacity": 8},
        headers=admin_headers,
    )
    rid = room.json()["id"]
    f = await client.post(
        f"/api/v1/admin/rooms/{rid}/bookable-units",
        json={"name": "Full", "type": "full_room", "capacity": 8},
        headers=admin_headers,
    )
    tid = (
        await client.post(
            f"/api/v1/admin/rooms/{rid}/bookable-units",
            json={"name": "T1", "type": "table", "capacity": 2},
            headers=admin_headers,
        )
    ).json()["id"]
    fid = f.json()["id"]
    await client.post(
        f"/api/v1/admin/bookable-units/{fid}/conflicts",
        json={"conflict_with_unit_id": tid},
        headers=admin_headers,
    )
    d = date.today()
    async with AsyncSessionLocal() as db:
        async with db.begin():
            user = User(
                email="cbooker@test.local",
                full_name="C",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=fid,
                booking_date=d,
                start_time=time(11, 0),
                end_time=time(11, 30),
                purpose=None,
            )

    r = await client.get(f"/api/v1/availability/rooms/{rid}", params={"date": d.isoformat()})
    grid = r.json()
    hit = next(
        (s for s in grid["slots"] if s["start_time"] == "11:00" and s["end_time"] == "11:30"),
        None,
    )
    assert hit is not None
    table_row = next(x for x in hit["units"] if x["unit_id"] == tid)
    assert table_row["available"] is False
    assert table_row["reason"] == "conflict"


@pytest.mark.asyncio
async def test_room_list_available_true_filters_by_time_range(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    r1 = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Taken", "booking_mode": "hybrid", "capacity": 2},
        headers=admin_headers,
    )
    r2 = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Free", "booking_mode": "hybrid", "capacity": 2},
        headers=admin_headers,
    )
    id1, id2 = r1.json()["id"], r2.json()["id"]
    u1 = (
        await client.post(
            f"/api/v1/admin/rooms/{id1}/bookable-units",
            json={"name": "Only", "type": "table", "capacity": 2},
            headers=admin_headers,
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/admin/rooms/{id2}/bookable-units",
        json={"name": "Open", "type": "table", "capacity": 2},
        headers=admin_headers,
    )
    d = date.today()
    async with AsyncSessionLocal() as db:
        async with db.begin():
            user = User(
                email="filt@test.local",
                full_name="F",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            await create_booking(
                db,
                user=user,
                room_id=id1,
                unit_id=u1,
                booking_date=d,
                start_time=time(15, 0),
                end_time=time(16, 0),
                purpose=None,
            )

    params = {
        "available": "true",
        "date": d.isoformat(),
        "start_time": "15:00",
        "end_time": "16:00",
    }
    r = await client.get("/api/v1/rooms", params=params)
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()["items"]}
    assert id1 not in ids
    assert id2 in ids


@pytest.mark.asyncio
async def test_room_list_available_excludes_room_when_full_range_inside_booking(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    """Full room booked 08:00–12:00 must not appear when filtering availability 09:00–10:00."""
    room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Blocked Full", "booking_mode": "hybrid", "capacity": 10},
        headers=admin_headers,
    )
    rid = room.json()["id"]
    uid = (
        await client.post(
            f"/api/v1/admin/rooms/{rid}/bookable-units",
            json={"name": "Whole", "type": "full_room", "capacity": 10},
            headers=admin_headers,
        )
    ).json()["id"]
    d = date.today()
    async with AsyncSessionLocal() as db:
        async with db.begin():
            user = User(
                email="blocked@test.local",
                full_name="B",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=uid,
                booking_date=d,
                start_time=time(8, 0),
                end_time=time(12, 0),
                purpose=None,
            )

    r = await client.get(
        "/api/v1/rooms",
        params={
            "available": "true",
            "date": d.isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
        },
    )
    assert r.status_code == 200
    assert rid not in {x["id"] for x in r.json()["items"]}


@pytest.mark.asyncio
async def test_room_list_available_excludes_with_unit_type_full_room(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "FR Blocked", "booking_mode": "hybrid", "capacity": 10},
        headers=admin_headers,
    )
    rid = room.json()["id"]
    uid = (
        await client.post(
            f"/api/v1/admin/rooms/{rid}/bookable-units",
            json={"name": "Whole", "type": "full_room", "capacity": 10},
            headers=admin_headers,
        )
    ).json()["id"]
    d = date.today()
    async with AsyncSessionLocal() as db:
        async with db.begin():
            user = User(
                email="frtype@test.local",
                full_name="F",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=uid,
                booking_date=d,
                start_time=time(8, 0),
                end_time=time(12, 0),
                purpose=None,
            )

    for params in (
        {
            "available": "true",
            "unit_type": "full_room",
            "date": d.isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
        },
        {
            "unit_type": "full_room",
            "date": d.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
    ):
        r = await client.get("/api/v1/rooms", params=params)
        assert r.status_code == 200, params
        assert rid not in {x["id"] for x in r.json()["items"]}, params


@pytest.mark.asyncio
async def test_availability_search_response_shape(client: AsyncClient, browse_setup: dict) -> None:
    today = date.today().isoformat()
    r = await client.get("/api/v1/availability/search", params={"date": today})
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == today
    assert body["slot_minutes"] == 30
    assert isinstance(body["rooms"], list)
    rid = browse_setup["room_id"]
    match = next((x for x in body["rooms"] if x["room_id"] == rid), None)
    assert match is not None
    assert len(match["slots"]) > 0


@pytest.mark.asyncio
async def test_create_unit_request_mode_and_booking_is_pending(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    from app.core.security import create_access_token

    room = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "Request Room", "booking_mode": "hybrid", "capacity": 4},
        headers=admin_headers,
    )
    rid = room.json()["id"]
    uresp = await client.post(
        f"/api/v1/admin/rooms/{rid}/bookable-units",
        json={"name": "Desk", "type": "table", "capacity": 2, "booking_mode": "request"},
        headers=admin_headers,
    )
    assert uresp.status_code == 201
    unit = uresp.json()
    assert unit["booking_mode"] == "request"

    detail = await client.get(f"/api/v1/rooms/{rid}")
    assert detail.json()["bookable_units"][0]["booking_mode"] == "request"

    async with AsyncSessionLocal() as db:
        async with db.begin():
            pol = await db.execute(select(BookingPolicy).limit(1))
            if pol.scalar_one_or_none() is None:
                db.add(
                    BookingPolicy(
                        slot_minutes=30,
                        max_booking_hours_per_day=8,
                        max_advance_days=30,
                        cancellation_cutoff_minutes=60,
                    )
                )
            user = User(
                email="requester@test.local",
                full_name="Requester",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            uid = user.id

    user_headers = {"Authorization": f"Bearer {create_access_token(str(uid))}"}
    d = date.today()
    booking = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": rid,
            "unit_id": unit["id"],
            "booking_date": d.isoformat(),
            "start_time": "10:00",
            "end_time": "10:30",
        },
        headers=user_headers,
    )
    assert booking.status_code == 201
    assert booking.json()["status"] == "pending"

    pending = await client.get("/api/v1/admin/bookings/pending", headers=admin_headers)
    assert pending.status_code == 200
    row = next(x for x in pending.json() if x["id"] == booking.json()["id"])
    assert row["room_name"] == "Request Room"
    assert row["unit_name"] == "Desk"
    assert row["user_full_name"] == "Requester"


def test_iter_window_slot_intervals_respects_bounds() -> None:
    from datetime import date as ddate

    from app.services.availability_service import (
        DEFAULT_AVAILABILITY_WINDOW_END,
        DEFAULT_AVAILABILITY_WINDOW_START,
    )

    day = ddate(2026, 3, 25)
    slots = iter_window_slot_intervals(
        day, 30, DEFAULT_AVAILABILITY_WINDOW_START, DEFAULT_AVAILABILITY_WINDOW_END
    )
    assert len(slots) > 0
    assert slots[0][0].hour == 8
    last_s, last_e = slots[-1]
    assert last_e.hour == 20 and last_e.minute == 0
