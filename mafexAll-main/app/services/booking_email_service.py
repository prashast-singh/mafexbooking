from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.room import Room
from app.models.unit import BookableUnit
from app.models.user import User
from app.services.email_service import send_email_with_attachments, send_plain_email
from app.utils.ics import build_booking_ics, build_series_booking_ics


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
    purpose_line = f"Purpose: {booking.purpose or 'Not specified'}\n"
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


def _series_occurrence_lines(bookings: list[Booking]) -> str:
    ordered = sorted(bookings, key=lambda b: (b.booking_date, b.start_time))
    lines: list[str] = []
    for booking in ordered:
        start_label = booking.start_time.strftime("%H:%M")
        end_label = booking.end_time.strftime("%H:%M")
        lines.append(f"- {booking.booking_date}: {start_label}–{end_label}")
    return "\n".join(lines)


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


async def send_series_confirmation_email(
    db: AsyncSession,
    *,
    bookings: list[Booking],
) -> None:
    if not bookings:
        return
    first = bookings[0]
    ctx = await _load_booking_context(db, first)
    if ctx is None:
        return
    user, room, unit = ctx
    location_line = f"Location: {room.location}\n" if room.location else ""
    purpose = first.purpose or "Not specified"
    series_id = first.series_id
    series_label = f"Series ID: {series_id}\n" if series_id is not None else ""
    occurrence_block = _series_occurrence_lines(bookings)

    subject = f"Series booking confirmed: {room.name}"
    body = (
        f"Hello {user.full_name},\n\n"
        "Your series room booking is confirmed.\n\n"
        f"Room: {room.name}\n"
        f"Unit: {unit.name}\n"
        f"{location_line}"
        f"{series_label}"
        f"Purpose: {purpose}\n"
        f"Occurrences ({len(bookings)}):\n"
        f"{occurrence_block}\n\n"
        "A calendar invite (.ics) with all occurrences is attached.\n"
    )

    ics_text = build_series_booking_ics(
        bookings=bookings,
        room=room,
        unit=unit,
        attendee_email=user.email,
    )
    filename = (
        f"series-{series_id}.ics" if series_id is not None else f"series-booking-{first.id}.ics"
    )
    attachments = [
        (filename, ics_text.encode("utf-8"), "text", "calendar"),
    ]
    await send_email_with_attachments(user.email, subject, body, attachments)


async def send_series_updated_email(
    db: AsyncSession,
    *,
    bookings: list[Booking],
) -> None:
    if not bookings:
        return
    first = bookings[0]
    ctx = await _load_booking_context(db, first)
    if ctx is None:
        return
    user, room, unit = ctx
    location_line = f"Location: {room.location}\n" if room.location else ""
    purpose = first.purpose or "Not specified"
    series_id = first.series_id
    series_label = f"Series ID: {series_id}\n" if series_id is not None else ""
    occurrence_block = _series_occurrence_lines(bookings)

    subject = f"Series booking updated: {room.name}"
    body = (
        f"Hello {user.full_name},\n\n"
        "Your series room booking has been updated.\n\n"
        f"Room: {room.name}\n"
        f"Unit: {unit.name}\n"
        f"{location_line}"
        f"{series_label}"
        f"Purpose: {purpose}\n"
        f"Updated occurrences ({len(bookings)}):\n"
        f"{occurrence_block}\n\n"
        "An updated calendar invite (.ics) with these occurrences is attached.\n"
    )

    ics_text = build_series_booking_ics(
        bookings=bookings,
        room=room,
        unit=unit,
        attendee_email=user.email,
    )
    filename = (
        f"series-{series_id}.ics" if series_id is not None else f"series-booking-{first.id}.ics"
    )
    attachments = [
        (filename, ics_text.encode("utf-8"), "text", "calendar"),
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


async def send_booking_request_notification_to_room_admins(
    db: AsyncSession,
    *,
    booking: Booking,
) -> None:
    from app.services.room_admin_service import list_room_admins
    from app.utils.frontend_urls import admin_booking_requests_url

    ctx = await _load_booking_context(db, booking)
    if ctx is None:
        return
    booker, room, unit = ctx
    admins = await list_room_admins(db, room_id=booking.room_id)
    if not admins:
        return

    start_label = booking.start_time.strftime("%H:%M")
    end_label = booking.end_time.strftime("%H:%M")
    purpose_line = f"Purpose: {booking.purpose or 'Not specified'}\n"
    subject = f"{room.name} {unit.name} new booking request"
    body = (
        "A new booking request needs review.\n\n"
        f"Requester: {booker.full_name}\n"
        f"Email: {booker.email}\n"
        f"Room: {room.name}\n"
        f"Unit: {unit.name}\n"
        f"Date: {booking.booking_date}\n"
        f"Time: {start_label}–{end_label}\n"
        f"{purpose_line}"
        f"\nOpen booking requests: {admin_booking_requests_url()}\n"
    )

    for row in admins:
        admin_user = row.user
        if admin_user is None or not admin_user.email:
            continue
        try:
            await send_plain_email(admin_user.email, subject, body)
        except Exception:
            pass


async def send_series_booking_request_notification_to_room_admins(
    db: AsyncSession,
    *,
    bookings: list[Booking],
) -> None:
    from app.core.enums import BookingStatus
    from app.services.room_admin_service import list_room_admins
    from app.utils.frontend_urls import admin_booking_requests_url

    pending = [b for b in bookings if b.status == BookingStatus.pending.value]
    if not pending:
        return

    first = pending[0]
    ctx = await _load_booking_context(db, first)
    if ctx is None:
        return
    booker, room, unit = ctx
    admins = await list_room_admins(db, room_id=first.room_id)
    if not admins:
        return

    purpose_line = f"Purpose: {first.purpose or 'Not specified'}\n"
    occurrences = _series_occurrence_lines(pending)
    subject = f"{room.name} {unit.name} new booking request"
    body = (
        "A new series booking request needs review.\n\n"
        f"Requester: {booker.full_name}\n"
        f"Email: {booker.email}\n"
        f"Room: {room.name}\n"
        f"Unit: {unit.name}\n"
        f"{purpose_line}"
        f"Requested slots:\n{occurrences}\n"
        f"\nOpen booking requests: {admin_booking_requests_url()}\n"
    )

    for row in admins:
        admin_user = row.user
        if admin_user is None or not admin_user.email:
            continue
        try:
            await send_plain_email(admin_user.email, subject, body)
        except Exception:
            pass
