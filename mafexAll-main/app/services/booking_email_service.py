from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User
from app.services.email_service import send_email_with_attachments
from app.utils.ics import build_booking_ics


async def send_booking_confirmation_email(
    db: AsyncSession,
    *,
    booking: Booking,
) -> None:
    user = await db.get(User, booking.user_id)
    room = await db.get(Room, booking.room_id)
    unit = await db.get(BookableUnit, booking.unit_id)
    if user is None or room is None or unit is None:
        return

    start_label = booking.start_time.strftime("%H:%M")
    end_label = booking.end_time.strftime("%H:%M")
    location_line = f"Location: {room.location}\n" if room.location else ""
    purpose_line = f"Purpose: {booking.purpose}\n" if booking.purpose else ""

    subject = f"Booking confirmed: {room.name}"
    body = (
        f"Hello {user.full_name},\n\n"
        "Your room booking is confirmed.\n\n"
        f"Room: {room.name}\n"
        f"Unit: {unit.name}\n"
        f"{location_line}"
        f"Date: {booking.booking_date}\n"
        f"Time: {start_label}–{end_label}\n"
        f"{purpose_line}\n"
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
