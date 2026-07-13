from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import select

from app.core.enums import ApprovalStatus, UserType
from app.db.session import AsyncSessionLocal
from app.models.booking import Booking
from app.models.booking_policy import BookingPolicy
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User
from app.services.booking_service import create_booking
from app.utils.ics import build_booking_ics


def _sample_booking() -> Booking:
    booking = Booking(
        user_id=1,
        room_id=1,
        unit_id=1,
        booking_date=date(2026, 7, 14),
        start_time=time(8, 0),
        end_time=time(9, 0),
        start_at=datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
        purpose="Team meeting",
        status="confirmed",
    )
    booking.id = 42
    return booking


def test_build_booking_ics_contains_event_fields() -> None:
    booking = _sample_booking()
    room = Room(name="Seminar Room A", booking_mode="hybrid", capacity=10, location="Building 12", is_active=True)
    unit = BookableUnit(room_id=1, name="Full room", type="full_room", capacity=10, is_active=True)

    ics = build_booking_ics(
        booking=booking,
        room=room,
        unit=unit,
        attendee_email="user@students.uni-marburg.de",
    )

    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "UID:mafex-booking-42@room-booking" in ics
    assert "DTSTART:20260714T080000Z" in ics
    assert "DTEND:20260714T090000Z" in ics
    assert "SUMMARY:Room booking: Seminar Room A (Full room)" in ics
    assert "LOCATION:Building 12" in ics
    assert "ATTENDEE" in ics
    assert "user@students.uni-marburg.de" in ics
    assert "Purpose: Team meeting" in ics


@pytest.mark.asyncio
async def test_confirmed_booking_sends_confirmation_email(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import booking_service

    sent: list[dict[str, object]] = []

    async def capture_send(db, *, booking):  # noqa: ANN001
        sent.append({"booking_id": booking.id, "status": booking.status})

    monkeypatch.setattr(booking_service, "send_booking_confirmation_email", capture_send)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(BookingPolicy(slot_minutes=30, max_booking_hours_per_day=8, max_advance_days=30, cancellation_cutoff_minutes=60))
            u = User(
                email="confirm@uni-marburg.de",
                full_name="Confirm User",
                role="user",
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            room = Room(name="R-Confirm", booking_mode="hybrid", capacity=10, is_active=True)
            db.add(room)
            await db.flush()
            unit = BookableUnit(room_id=room.id, name="Desk", type="table", capacity=2, is_active=True, booking_mode="direct")
            db.add(unit)
            await db.flush()
            uid = u.id
            rid = room.id
            unid = unit.id

        async with db.begin():
            r = await db.execute(select(User).where(User.id == uid))
            user = r.scalar_one()
            booking = await create_booking(
                db,
                user=user,
                room_id=rid,
                unit_id=unid,
                booking_date=date.today(),
                start_time=time(9, 0),
                end_time=time(10, 0),
                purpose="Focus work",
            )
            assert booking.status == "confirmed"

    assert len(sent) == 1
    assert sent[0]["status"] == "confirmed"
