from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def _create_user(
    *,
    email: str,
    role: str = "user",
    is_active: bool = True,
    deactivate_at: datetime | None = None,
) -> int:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            u = User(
                email=email,
                full_name=email.split("@")[0],
                role=role,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=is_active,
                deactivate_at=deactivate_at,
            )
            db.add(u)
            await db.flush()
            return u.id


@pytest.mark.asyncio
async def test_admin_deactivate_and_reactivate_user(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    uid = await _create_user(email="deact@uni-marburg.de")
    token = create_access_token(str(uid))
    user_headers = {"Authorization": f"Bearer {token}"}

    deactivated = await client.patch(
        f"/api/v1/admin/users/{uid}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    me = await client.get("/api/v1/users/me", headers=user_headers)
    assert me.status_code == 403

    reactivated = await client.patch(
        f"/api/v1/admin/users/{uid}/status",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True

    me2 = await client.get("/api/v1/users/me", headers=user_headers)
    assert me2.status_code == 200


@pytest.mark.asyncio
async def test_scheduled_deactivation_in_past_applies_on_auth(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    uid = await _create_user(email="pastsched@uni-marburg.de", deactivate_at=past)
    token = create_access_token(str(uid))
    user_headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/users/me", headers=user_headers)
    assert me.status_code == 403


@pytest.mark.asyncio
async def test_scheduled_deactivation_in_future_keeps_active(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    uid = await _create_user(email="futuresched@uni-marburg.de")
    future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    resp = await client.patch(
        f"/api/v1/admin/users/{uid}/status",
        json={"deactivate_at": future},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True
    assert resp.json()["deactivate_at"] is not None

    token = create_access_token(str(uid))
    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_cannot_deactivate_self(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    resp = await client.patch(
        "/api/v1/admin/users/1/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "self_action"


@pytest.mark.asyncio
async def test_delete_user_cascades_bookings(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    from datetime import date

    uid = await _create_user(email="todelete@uni-marburg.de")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            from app.models.booking_policy import BookingPolicy
            from app.models.room import Room
            from app.models.unit import BookableUnit

            db.add(
                BookingPolicy(
                    slot_minutes=30,
                    max_booking_hours_per_day=8,
                    max_advance_days=30,
                    cancellation_cutoff_minutes=0,
                )
            )
            room = Room(name="Del Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(
                room_id=room.id,
                name="Desk",
                type="table",
                capacity=2,
                is_active=True,
                booking_mode="direct",
            )
            db.add(unit)
            await db.flush()
            rid, unid = room.id, unit.id

    token = create_access_token(str(uid))
    created = await client.post(
        "/api/v1/bookings",
        json={
            "room_id": rid,
            "unit_id": unid,
            "booking_date": str(date.today()),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201

    deleted = await client.delete(f"/api/v1/admin/users/{uid}", headers=admin_headers)
    assert deleted.status_code == 204

    gone = await client.patch(
        f"/api/v1/admin/users/{uid}/status",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_nulls_approved_by_refs(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    approver_id = await _create_user(email="approver@uni-marburg.de")
    target_id = await _create_user(email="approveduser@uni-marburg.de")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            target = await db.get(User, target_id)
            assert target is not None
            target.approved_by_id = approver_id

    deleted = await client.delete(f"/api/v1/admin/users/{approver_id}", headers=admin_headers)
    assert deleted.status_code == 204

    async with AsyncSessionLocal() as db:
        target = await db.get(User, target_id)
        assert target is not None
        assert target.approved_by_id is None
