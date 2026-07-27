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


def _vevent_lines(
    *,
    booking: Booking,
    room: Room,
    unit: BookableUnit,
    attendee_email: str,
    now: datetime,
) -> list[str]:
    summary = _ics_escape(f"Room booking: {room.name} ({unit.name})")
    location = _ics_escape(room.location or room.name)
    description_parts = [
        f"Room: {room.name}",
        f"Unit: {unit.name}",
        f"Booking ID: {booking.id}",
        f"Purpose: {booking.purpose or 'Not specified'}",
    ]
    if booking.series_id is not None:
        description_parts.insert(3, f"Series ID: {booking.series_id}")
    description = _ics_escape("\n".join(description_parts))
    uid = f"mafex-booking-{booking.id}@room-booking"
    attendee = _ics_escape(attendee_email)
    return [
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
    ]


def build_booking_ics(
    *,
    booking: Booking,
    room: Room,
    unit: BookableUnit,
    attendee_email: str,
) -> str:
    now = datetime.now(timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mafex Rooms//Booking System//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        *_vevent_lines(
            booking=booking,
            room=room,
            unit=unit,
            attendee_email=attendee_email,
            now=now,
        ),
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def build_series_booking_ics(
    *,
    bookings: list[Booking],
    room: Room,
    unit: BookableUnit,
    attendee_email: str,
) -> str:
    """One VCALENDAR with a VEVENT per series occurrence (stable per-booking UIDs)."""
    now = datetime.now(timezone.utc)
    ordered = sorted(bookings, key=lambda b: (b.booking_date, b.start_at))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mafex Rooms//Booking System//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for booking in ordered:
        lines.extend(
            _vevent_lines(
                booking=booking,
                room=room,
                unit=unit,
                attendee_email=attendee_email,
                now=now,
            )
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
