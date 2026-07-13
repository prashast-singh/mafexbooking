from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.enums import ApprovalStatus, OtpPurpose, UserRole, UserType
from app.core.security import create_access_token, hash_otp
from app.db.session import AsyncSessionLocal
from app.models.internal_domain import InternalDomain
from app.models.otp import OtpCode
from app.models.user import User
from app.models.user_email_history import UserEmailHistory
from app.services.user_profile_service import (
    list_user_email_history,
    request_email_change_otp,
    verify_email_change_otp,
)


@pytest.mark.asyncio
async def test_update_name_via_patch(client, admin_headers: dict[str, str]) -> None:
    from app.core.security import create_access_token
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        async with db.begin():
            u = User(
                email="namepatch@uni-marburg.de",
                full_name="Old Name",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            uid = u.id
    token = create_access_token(str(uid))
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.patch("/api/v1/users/me", headers=headers, json={"full_name": "New Name"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "New Name"


@pytest.mark.asyncio
async def test_email_change_creates_history(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import user_profile_service

    async def noop_send(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(user_profile_service, "send_otp_email", noop_send)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(InternalDomain(domain="uni-marburg.de", is_active=True))
            u = User(
                email="old@uni-marburg.de",
                full_name="User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            uid = u.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            db.add(
                OtpCode(
                    email="new@uni-marburg.de",
                    otp_hash=hash_otp("654321"),
                    purpose=OtpPurpose.email_change.value,
                    expires_at=datetime.now(timezone.utc).replace(year=2099),
                )
            )

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            updated = await verify_email_change_otp(
                db, user=user, new_email="new@uni-marburg.de", otp="654321"
            )
            assert updated.email == "new@uni-marburg.de"
            assert updated.approval_status == ApprovalStatus.approved.value

        async with db.begin():
            history = await list_user_email_history(db, user_id=uid)
            assert len(history) == 1
            assert history[0].email == "old@uni-marburg.de"


@pytest.mark.asyncio
async def test_email_change_to_external_updates_type(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import user_profile_service

    async def noop_send(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(user_profile_service, "send_otp_email", noop_send)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(InternalDomain(domain="uni-marburg.de", is_active=True))
            u = User(
                email="internal@uni-marburg.de",
                full_name="User",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            uid = u.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            db.add(
                OtpCode(
                    email="ext@gmail.com",
                    otp_hash=hash_otp("111111"),
                    purpose=OtpPurpose.email_change.value,
                    expires_at=datetime.now(timezone.utc).replace(year=2099),
                )
            )
            await db.flush()
            updated = await verify_email_change_otp(
                db, user=user, new_email="ext@gmail.com", otp="111111"
            )
            assert updated.user_type == UserType.external.value
            assert updated.approval_status == ApprovalStatus.approved.value
