from __future__ import annotations

from datetime import datetime, timezone

from app.models.booking import Booking
from app.models.room import Room
from app.models.unit import BookableUnit


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _ics_datetime(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_booking_ics(
    *,
    booking: Booking,
    room: Room,
    unit: BookableUnit,
    attendee_email: str,
) -> str:
    summary = _ics_escape(f"Room booking: {room.name} ({unit.name})")
    location = _ics_escape(room.location or room.name)
    description_parts = [
        f"Room: {room.name}",
        f"Unit: {unit.name}",
        f"Booking ID: {booking.id}",
        f"Purpose: {booking.purpose or 'Not specified'}",
    ]
    description = _ics_escape("\n".join(description_parts))
    uid = f"mafex-booking-{booking.id}@room-booking"
    now = datetime.now(timezone.utc)
    attendee = _ics_escape(attendee_email)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mafex Rooms//Booking System//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_ics_datetime(now)}",
        f"DTSTART:{_ics_datetime(booking.start_at)}",
        f"DTEND:{_ics_datetime(booking.end_at)}",
        f"SUMMARY:{summary}",
        f"LOCATION:{location}",
        f"DESCRIPTION:{description}",
        "ORGANIZER;CN=Mafex Rooms:MAILTO:mafex-ws@staff.uni-marburg.de",
        f"ATTENDEE;CN={attendee};ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=FALSE:MAILTO:{attendee}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
