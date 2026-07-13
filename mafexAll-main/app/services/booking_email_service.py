from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User
from app.services.email_service import send_email_with_attachments, send_plain_email
from app.utils.ics import build_booking_ics


def _booking_details_lines(
    *,
    user: User,
    room: Room,
    unit: BookableUnit,
    booking: Booking,
) -> tuple[str, str, str, str, str]:
    start_label = booking.start_time.strftime("%H:%M")
    end_label = booking.end_time.strftime("%H:%M")
    location_line = f"Location: {room.location}\n" if room.location else ""
    purpose_line = f"Purpose: {booking.purpose}\n" if booking.purpose else ""
    greeting = f"Hello {user.full_name},\n\n"
    core = (
        f"Room: {room.name}\n"
        f"Unit: {unit.name}\n"
        f"{location_line}"
        f"Date: {booking.booking_date}\n"
        f"Time: {start_label}–{end_label}\n"
        f"{purpose_line}"
    )
    return greeting, core, start_label, end_label, location_line


async def _load_booking_context(db: AsyncSession, booking: Booking):
    user = await db.get(User, booking.user_id)
    room = await db.get(Room, booking.room_id)
    unit = await db.get(BookableUnit, booking.unit_id)
    if user is None or room is None or unit is None:
        return None
    return user, room, unit


async def send_booking_confirmation_email(
    db: AsyncSession,
    *,
    booking: Booking,
) -> None:
    ctx = await _load_booking_context(db, booking)
    if ctx is None:
        return
    user, room, unit = ctx
    greeting, core, _, _, _ = _booking_details_lines(
        user=user, room=room, unit=unit, booking=booking
    )

    subject = f"Booking confirmed: {room.name}"
    body = (
        f"{greeting}"
        "Your room booking is confirmed.\n\n"
        f"{core}\n"
        "A calendar invite (.ics) is attached — open it to add this booking to your calendar.\n"
    )

    ics_text = build_booking_ics(
        booking=booking,
        room=room,
        unit=unit,
        attendee_email=user.email,
    )
    attachments = [
        (f"booking-{booking.id}.ics", ics_text.encode("utf-8"), "text", "calendar"),
    ]
    await send_email_with_attachments(user.email, subject, body, attachments)


async def send_booking_updated_email(
    db: AsyncSession,
    *,
    booking: Booking,
) -> None:
    ctx = await _load_booking_context(db, booking)
    if ctx is None:
        return
    user, room, unit = ctx
    greeting, core, _, _, _ = _booking_details_lines(
        user=user, room=room, unit=unit, booking=booking
    )

    subject = f"Booking updated: {room.name}"
    body = (
        f"{greeting}"
        "Your room booking has been updated.\n\n"
        f"{core}\n"
        "An updated calendar invite (.ics) is attached.\n"
    )

    ics_text = build_booking_ics(
        booking=booking,
        room=room,
        unit=unit,
        attendee_email=user.email,
    )
    attachments = [
        (f"booking-{booking.id}.ics", ics_text.encode("utf-8"), "text", "calendar"),
    ]
    await send_email_with_attachments(user.email, subject, body, attachments)


async def send_booking_cancellation_email(
    db: AsyncSession,
    *,
    booking: Booking,
) -> None:
    ctx = await _load_booking_context(db, booking)
    if ctx is None:
        return
    user, room, unit = ctx
    greeting, core, _, _, _ = _booking_details_lines(
        user=user, room=room, unit=unit, booking=booking
    )

    reason_line = ""
    if booking.cancellation_reason:
        reason_line = f"\nReason: {booking.cancellation_reason}\n"

    subject = f"Booking cancelled: {room.name}"
    body = (
        f"{greeting}"
        "Your room booking has been cancelled.\n\n"
        f"{core}"
        f"{reason_line}"
    )
    await send_plain_email(user.email, subject, body)


async def send_booking_denial_email(
    db: AsyncSession,
    *,
    booking: Booking,
) -> None:
    ctx = await _load_booking_context(db, booking)
    if ctx is None:
        return
    user, room, unit = ctx
    greeting, core, _, _, _ = _booking_details_lines(
        user=user, room=room, unit=unit, booking=booking
    )

    reason_line = ""
    if booking.decision_reason:
        reason_line = f"\nReason: {booking.decision_reason}\n"

    subject = f"Booking request denied: {room.name}"
    body = (
        f"{greeting}"
        "Your booking request was denied.\n\n"
        f"{core}"
        f"{reason_line}"
    )
    await send_plain_email(user.email, subject, body)
