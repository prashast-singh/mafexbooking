import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import get_settings
from app.services.room_image_storage import MAX_LONG_SIDE, process_upload_bytes, resize_to_max_long_side


@pytest.mark.asyncio
async def test_get_room_amenities(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    a = await client.post("/api/v1/admin/amenities", json={"name": "Proj"}, headers=admin_headers)
    aid = a.json()["id"]
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "RG", "booking_mode": "hybrid", "capacity": 1},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    await client.post(f"/api/v1/admin/rooms/{rid}/amenities", json={"amenity_id": aid}, headers=admin_headers)
    g = await client.get(f"/api/v1/admin/rooms/{rid}/amenities", headers=admin_headers)
    assert g.status_code == 200
    assert len(g.json()) == 1
    assert g.json()[0]["name"] == "Proj"


@pytest.mark.asyncio
async def test_attach_amenity_to_room(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    a = await client.post(
        "/api/v1/admin/amenities",
        json={"name": "Whiteboard"},
        headers=admin_headers,
    )
    assert a.status_code == 201
    aid = a.json()["id"]
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "R1", "booking_mode": "hybrid", "capacity": 4},
        headers=admin_headers,
    )
    assert r.status_code == 201
    rid = r.json()["id"]
    resp = await client.post(
        f"/api/v1/admin/rooms/{rid}/amenities",
        json={"amenity_id": aid},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == aid
    assert data[0]["name"] == "Whiteboard"


@pytest.mark.asyncio
async def test_duplicate_attach_returns_409(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    a = await client.post(
        "/api/v1/admin/amenities",
        json={"name": "LAN"},
        headers=admin_headers,
    )
    aid = a.json()["id"]
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "R2", "booking_mode": "hybrid", "capacity": 2},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    assert (await client.post(f"/api/v1/admin/rooms/{rid}/amenities", json={"amenity_id": aid}, headers=admin_headers)).status_code == 200
    dup = await client.post(
        f"/api/v1/admin/rooms/{rid}/amenities",
        json={"amenity_id": aid},
        headers=admin_headers,
    )
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_detach_amenity_from_room(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    a = await client.post(
        "/api/v1/admin/amenities",
        json={"name": "Monitor"},
        headers=admin_headers,
    )
    aid = a.json()["id"]
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "R3", "booking_mode": "hybrid", "capacity": 2},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    await client.post(f"/api/v1/admin/rooms/{rid}/amenities", json={"amenity_id": aid}, headers=admin_headers)
    resp = await client.delete(
        f"/api/v1/admin/rooms/{rid}/amenities/{aid}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_room_with_amenity_ids(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    a1 = await client.post("/api/v1/admin/amenities", json={"name": "A1"}, headers=admin_headers)
    a2 = await client.post("/api/v1/admin/amenities", json={"name": "A2"}, headers=admin_headers)
    id1, id2 = a1.json()["id"], a2.json()["id"]
    r = await client.post(
        "/api/v1/admin/rooms",
        json={
            "name": "R4",
            "booking_mode": "hybrid",
            "capacity": 3,
            "amenity_ids": [id2, id1, id2],
        },
        headers=admin_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["amenities"]) == 2
    names = {x["name"] for x in body["amenities"]}
    assert names == {"A1", "A2"}


@pytest.mark.asyncio
async def test_patch_room_replaces_amenities(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    a1 = await client.post("/api/v1/admin/amenities", json={"name": "B1"}, headers=admin_headers)
    a2 = await client.post("/api/v1/admin/amenities", json={"name": "B2"}, headers=admin_headers)
    id1, id2 = a1.json()["id"], a2.json()["id"]
    cr = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "R5", "booking_mode": "hybrid", "capacity": 1, "amenity_ids": [id1]},
        headers=admin_headers,
    )
    rid = cr.json()["id"]
    patch = await client.patch(
        f"/api/v1/admin/rooms/{rid}",
        json={"amenity_ids": [id2]},
        headers=admin_headers,
    )
    assert patch.status_code == 200
    ams = patch.json()["amenities"]
    assert len(ams) == 1
    assert ams[0]["id"] == id2


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (80, 60), color="blue").save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_successful_image_upload(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "ImgRoom", "booking_mode": "hybrid", "capacity": 1},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    files = {"file": ("shot.png", _png_bytes(), "image/png")}
    data = {"sort_order": "3"}
    resp = await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files=files,
        data=data,
        headers=admin_headers,
    )
    assert resp.status_code == 201
    j = resp.json()
    assert j["room_id"] == rid
    assert j["sort_order"] == 3
    assert j["file_url"].startswith("/storage/room_images/")
    assert j["file_url"].endswith(".jpg")


@pytest.mark.asyncio
async def test_invalid_image_extension_rejected(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "ImgRoom2", "booking_mode": "hybrid", "capacity": 1},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    files = {"file": ("x.gif", b"GIF89a", "image/gif")}
    resp = await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files=files,
        headers=admin_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_image_upload_stores_db_row_with_file_url(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.room import RoomImage

    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "ImgRoom3", "booking_mode": "hybrid", "capacity": 1},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    resp = await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files={"file": ("a.jpeg", _png_bytes(), "image/jpeg")},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    iid = resp.json()["id"]
    async with AsyncSessionLocal() as db:
        row = await db.get(RoomImage, iid)
        assert row is not None
        assert row.file_url.startswith("/storage/room_images/")
        q = await db.execute(select(RoomImage).where(RoomImage.room_id == rid))
        assert len(q.scalars().all()) == 1


@pytest.mark.asyncio
async def test_delete_image_removes_db_row(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.room import RoomImage

    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "ImgRoom4", "booking_mode": "hybrid", "capacity": 1},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    up = await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files={"file": ("z.png", _png_bytes(), "image/png")},
        headers=admin_headers,
    )
    iid = up.json()["id"]
    del_resp = await client.delete(
        f"/api/v1/admin/rooms/{rid}/images/{iid}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 204
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(RoomImage).where(RoomImage.id == iid))
        assert q.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_image_removes_local_file(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "ImgRoom5", "booking_mode": "hybrid", "capacity": 1},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    up = await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files={"file": ("z.png", _png_bytes(), "image/png")},
        headers=admin_headers,
    )
    url = up.json()["file_url"]
    name = Path(url).name
    disk_path = get_settings().room_images_dir / name
    assert disk_path.is_file()
    iid = up.json()["id"]
    await client.delete(f"/api/v1/admin/rooms/{rid}/images/{iid}", headers=admin_headers)
    assert not disk_path.exists()


@pytest.mark.asyncio
async def test_uploaded_image_served_via_static_mount(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/admin/rooms",
        json={"name": "ImgRoom6", "booking_mode": "hybrid", "capacity": 1},
        headers=admin_headers,
    )
    rid = r.json()["id"]
    up = await client.post(
        f"/api/v1/admin/rooms/{rid}/images",
        files={"file": ("z.png", _png_bytes(), "image/png")},
        headers=admin_headers,
    )
    path = up.json()["file_url"]
    got = await client.get(path)
    assert got.status_code == 200
    assert got.headers.get("content-type", "").startswith("image/")


def test_resize_reduces_oversized_image_preserves_aspect() -> None:
    large = Image.new("RGB", (2000, 1000), color="red")
    out = resize_to_max_long_side(large)
    assert max(out.size) == MAX_LONG_SIDE
    assert out.size[0] == MAX_LONG_SIDE
    assert out.size[1] == MAX_LONG_SIDE // 2


def test_process_upload_resizes_oversized_file() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (2400, 600), color="green").save(buf, format="PNG")
    content = buf.getvalue()
    url, path = process_upload_bytes(content, "big.png")
    assert url.startswith("/storage/room_images/")
    saved = Image.open(path)
    try:
        assert max(saved.size) <= MAX_LONG_SIDE
        w, h = saved.size
        assert abs(w / h - 4.0) < 0.02
    finally:
        saved.close()
    path.unlink(missing_ok=True)
