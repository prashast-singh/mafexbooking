from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import select

from app.core.enums import ApprovalStatus, OtpPurpose, UserType
from app.core.security import hash_otp
from app.db.session import AsyncSessionLocal
from app.models.booking_policy import BookingPolicy
from app.models.internal_domain import InternalDomain
from app.models.otp import OtpCode
from app.models.room import Room
from app.models.unit import BookableUnit, UnitConflict
from app.models.user import User
from app.services.auth_service import verify_signup_otp
from app.services.booking_service import BookingError, create_booking
from app.utils.slots import combine_utc, duration_minutes, is_slot_aligned


@pytest.mark.asyncio
async def test_internal_signup_stays_pending_after_otp(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import auth_service

    async def noop_send(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(auth_service, "send_otp_email", noop_send)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(InternalDomain(domain="uni-marburg.de", is_active=True))
            db.add(
                User(
                    email="student@uni-marburg.de",
                    full_name="S",
                    role="user",
                    user_type=UserType.internal.value,
                    email_verified=False,
                    approval_status=ApprovalStatus.pending.value,
                    is_active=True,
                )
            )
        async with db.begin():
            r = await db.execute(select(User).where(User.email == "student@uni-marburg.de"))
            u = r.scalar_one()
            db.add(
                OtpCode(
                    email=u.email,
                    otp_hash=hash_otp("123456"),
                    purpose=OtpPurpose.signup.value,
                    expires_at=datetime.now(timezone.utc).replace(year=2099),
                )
            )
        async with db.begin():
            await verify_signup_otp(db, email="student@uni-marburg.de", otp="123456")
            r2 = await db.execute(select(User).where(User.email == "student@uni-marburg.de"))
            u2 = r2.scalar_one()
            assert u2.email_verified is True
            assert u2.approval_status == ApprovalStatus.pending.value


@pytest.mark.asyncio
async def test_external_signup_verification_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import auth_service

    async def noop_send(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(auth_service, "send_otp_email", noop_send)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(
                User(
                    email="ext@gmail.com",
                    full_name="E",
                    role="user",
                    user_type=UserType.external.value,
                    email_verified=False,
                    approval_status=ApprovalStatus.pending.value,
                    is_active=True,
                )
            )
            db.add(
                OtpCode(
                    email="ext@gmail.com",
                    otp_hash=hash_otp("654321"),
                    purpose=OtpPurpose.signup.value,
                    expires_at=datetime.now(timezone.utc).replace(year=2099),
                )
            )
        async with db.begin():
            await verify_signup_otp(db, email="ext@gmail.com", otp="654321")
            r = await db.execute(select(User).where(User.email == "ext@gmail.com"))
            u = r.scalar_one()
            assert u.email_verified is True
            assert u.approval_status == ApprovalStatus.pending.value


@pytest.mark.asyncio
async def test_booking_overlap_rejected() -> None:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=60))
            u = User(
                email="a@uni-marburg.de",
                full_name="A",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="R1", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(room_id=room.id, name="Whole", type="full_room", capacity=10, is_active=True)
            db.add(unit)
            await db.flush()
            uid = u.id
            rid = room.id
            unid = unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            d = date.today()
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=unid,
                booking_date=d,
                start_time=time(10, 0),
                end_time=time(11, 0),
                purpose=None,
            )

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            d = date.today()
            with pytest.raises(BookingError) as ei:
                await create_booking(
                    db,
                    user=user,
                    room_id=rid,
                    unit_id=unid,
                    booking_date=d,
                    start_time=time(10, 30),
                    end_time=time(11, 30),
                    purpose=None,
                )
            assert ei.value.code == "overlap"


@pytest.mark.asyncio
async def test_booking_conflict_rejected() -> None:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=60))
            u = User(
                email="b@uni-marburg.de",
                full_name="B",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="R2", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            u1 = BookableUnit(room_id=room.id, name="Full", type="full_room", capacity=10, is_active=True)
            u2 = BookableUnit(room_id=room.id, name="Table1", type="table", capacity=2, is_active=True)
            db.add(u1)
            db.add(u2)
            await db.flush()
            db.add(UnitConflict(unit_id=u1.id, conflict_with_unit_id=u2.id))
            uid = u.id
            rid = room.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            r2 = await db.execute(select(BookableUnit).where(BookableUnit.name == "Full"))
            full = r2.scalar_one()
            d = date.today()
            await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=full.id,
                booking_date=d,
                start_time=time(14, 0),
                end_time=time(15, 0),
                purpose=None,
            )

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            r2 = await db.execute(select(BookableUnit).where(BookableUnit.name == "Table1"))
            table = r2.scalar_one()
            d = date.today()
            with pytest.raises(BookingError) as ei:
                await create_booking(
                    db,
                    user=user,
                    room_id=rid,
                    unit_id=table.id,
                    booking_date=d,
                    start_time=time(14, 0),
                    end_time=time(14, 30),
                    purpose=None,
                )
            assert ei.value.code == "overlap"


@pytest.mark.asyncio
async def test_slot_alignment_validation() -> None:
    policy_minutes = 30
    assert is_slot_aligned(time(9, 0), policy_minutes) is True
    assert is_slot_aligned(time(9, 15), policy_minutes) is False
    assert duration_minutes(time(9, 0), time(9, 30),) == 30
    d = date(2025, 6, 1)
    s = combine_utc(d, time(9, 0))
    e = combine_utc(d, time(10, 0))
    assert s < e
