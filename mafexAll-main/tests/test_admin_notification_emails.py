from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.enums import ApprovalStatus, OtpPurpose, UserRole, UserType
from app.core.security import hash_otp
from app.db.session import AsyncSessionLocal
from app.models.booking_policy import BookingPolicy
from app.models.otp import OtpCode
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User
from app.schemas.booking_series import BookingSeriesCreate
from app.services.auth_service import verify_signup_otp
from app.services.booking_service import create_booking
from app.services.booking_series_service import create_booking_series
from app.services.room_admin_service import add_room_admin
from app.utils.frontend_urls import admin_approvals_url, admin_booking_requests_url


@pytest.mark.asyncio
async def test_signup_verify_emails_admins_with_approvals_link(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import auth_service, email_service

    sent: list[dict[str, str]] = []

    async def noop_otp(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def capture_plain(to_email: str, subject: str, body: str) -> None:
        sent.append({"to": to_email, "subject": subject, "body": body})

    monkeypatch.setattr(auth_service, "send_otp_email", noop_otp)
    monkeypatch.setattr(email_service, "send_plain_email", capture_plain)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            admin = User(
                email="admin-notify@uni-marburg.de",
                full_name="Admin",
                role=UserRole.admin.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            signup = User(
                email="newuser-notify@uni-marburg.de",
                full_name="New User",
                signup_intent="Found via newsletter",
                role=UserRole.user.value,
                user_type=UserType.internal.value,
                email_verified=False,
                approval_status=ApprovalStatus.pending.value,
                is_active=True,
            )
            db.add(admin)
            db.add(signup)
            await db.flush()
            db.add(
                OtpCode(
                    email=signup.email,
                    otp_hash=hash_otp("111222"),
                    purpose=OtpPurpose.signup.value,
                    expires_at=datetime.now(timezone.utc).replace(year=2099),
                )
            )

        async with db.begin():
            await verify_signup_otp(db, email="newuser-notify@uni-marburg.de", otp="111222")

    assert len(sent) == 1
    assert sent[0]["to"] == "admin-notify@uni-marburg.de"
    assert "pending approval" in sent[0]["subject"].lower()
    assert "New User" in sent[0]["body"]
    assert "newuser-notify@uni-marburg.de" in sent[0]["body"]
    assert "Found via newsletter" in sent[0]["body"]
    assert admin_approvals_url() in sent[0]["body"]
    assert "/admin/approvals" in sent[0]["body"]


@pytest.mark.asyncio
async def test_pending_booking_emails_room_admin_with_requests_link(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_email_service, booking_service

    sent: list[dict[str, str]] = []

    async def capture_plain(to_email: str, subject: str, body: str) -> None:
        sent.append({"to": to_email, "subject": subject, "body": body})

    monkeypatch.setattr(booking_email_service, "send_plain_email", capture_plain)
    monkeypatch.setattr(
        booking_service,
        "send_booking_request_notification_to_room_admins",
        booking_email_service.send_booking_request_notification_to_room_admins,
    )

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(
                BookingPolicy(
                    slot_minutes=30,
                    max_booking_hours_per_day=8,
                    max_advance_days=30,
                    cancellation_cutoff_minutes=60,
                )
            )
            booker = User(
                email="booker-req@uni-marburg.de",
                full_name="Booker",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            room_admin = User(
                email="roomadmin-req@uni-marburg.de",
                full_name="Room Admin",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(booker)
            db.add(room_admin)
            await db.flush()
            room = Room(name="Request Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(
                room_id=room.id,
                name="Desk A",
                type="table",
                capacity=2,
                is_active=True,
                booking_mode="request",
            )
            db.add(unit)
            await db.flush()
            await add_room_admin(db, room_id=room.id, user_id=room_admin.id)
            booker_id, rid, unid = booker.id, room.id, unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == booker_id))
            user = r.scalar_one()
            booking = await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=unid,
                booking_date=date.today(),
                start_time=time(10, 0),
                end_time=time(11, 0),
                purpose="Study",
            )
            assert booking.status == "pending"

    assert len(sent) == 1
    assert sent[0]["to"] == "roomadmin-req@uni-marburg.de"
    assert sent[0]["subject"] == "Request Room Desk A new booking request"
    assert "Booker" in sent[0]["body"]
    assert "booker-req@uni-marburg.de" in sent[0]["body"]
    assert admin_booking_requests_url() in sent[0]["body"]
    assert "/admin/booking-requests" in sent[0]["body"]


@pytest.mark.asyncio
async def test_pending_booking_no_room_admins_sends_no_email(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_email_service, booking_service

    sent: list[dict[str, str]] = []

    async def capture_plain(to_email: str, subject: str, body: str) -> None:
        sent.append({"to": to_email, "subject": subject, "body": body})

    monkeypatch.setattr(booking_email_service, "send_plain_email", capture_plain)
    monkeypatch.setattr(
        booking_service,
        "send_booking_request_notification_to_room_admins",
        booking_email_service.send_booking_request_notification_to_room_admins,
    )

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(
                BookingPolicy(
                    slot_minutes=30,
                    max_booking_hours_per_day=8,
                    max_advance_days=30,
                    cancellation_cutoff_minutes=60,
                )
            )
            booker = User(
                email="booker-noreq@uni-marburg.de",
                full_name="Booker",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(booker)
            await db.flush()
            room = Room(name="No Admin Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(
                room_id=room.id,
                name="Desk",
                type="table",
                capacity=2,
                is_active=True,
                booking_mode="request",
            )
            db.add(unit)
            await db.flush()
            booker_id, rid, unid = booker.id, room.id, unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == booker_id))
            user = r.scalar_one()
            booking = await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=unid,
                booking_date=date.today(),
                start_time=time(12, 0),
                end_time=time(13, 0),
                purpose=None,
            )
            assert booking.status == "pending"

    assert sent == []


@pytest.mark.asyncio
async def test_series_pending_sends_one_email_with_all_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_email_service, booking_series_service

    sent: list[dict[str, str]] = []

    async def capture_plain(to_email: str, subject: str, body: str) -> None:
        sent.append({"to": to_email, "subject": subject, "body": body})

    async def noop_confirm(db, *, bookings):  # noqa: ANN001
        return None

    monkeypatch.setattr(booking_email_service, "send_plain_email", capture_plain)
    monkeypatch.setattr(booking_series_service, "send_series_confirmation_email", noop_confirm)
    monkeypatch.setattr(
        booking_series_service,
        "send_series_booking_request_notification_to_room_admins",
        booking_email_service.send_series_booking_request_notification_to_room_admins,
    )

    start = date.today()
    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(
                BookingPolicy(
                    slot_minutes=30,
                    max_booking_hours_per_day=8,
                    max_advance_days=90,
                    cancellation_cutoff_minutes=60,
                )
            )
            booker = User(
                email="series-req@uni-marburg.de",
                full_name="Series Booker",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            room_admin = User(
                email="series-admin@uni-marburg.de",
                full_name="Series Admin",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(booker)
            db.add(room_admin)
            await db.flush()
            room = Room(name="Series Req Room", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(
                room_id=room.id,
                name="Unit X",
                type="table",
                capacity=2,
                is_active=True,
                booking_mode="request",
            )
            db.add(unit)
            await db.flush()
            await add_room_admin(db, room_id=room.id, user_id=room_admin.id)
            booker_id, rid, unid = booker.id, room.id, unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == booker_id))
            user = r.scalar_one()
            out = await create_booking_series(
                db,
                user=user,
                body=BookingSeriesCreate(
                    room_id=rid,
                    unit_id=unid,
                    booking_date=start,
                    start_time=time(9, 0),
                    end_time=time(10, 0),
                    purpose="Weekly seminar",
                    frequency="weekly",
                    interval=1,
                    max_occurrences=3,
                ),
            )
            assert len(out.bookings) == 3
            assert all(b.status == "pending" for b in out.bookings)

    assert len(sent) == 1
    assert sent[0]["to"] == "series-admin@uni-marburg.de"
    assert sent[0]["subject"] == "Series Req Room Unit X new booking request"
    body = sent[0]["body"]
    assert "Weekly seminar" in body
    assert str(start) in body
    assert str(start + timedelta(days=7)) in body
    assert str(start + timedelta(days=14)) in body
    assert admin_booking_requests_url() in body
    assert "/admin/booking-requests" in body
