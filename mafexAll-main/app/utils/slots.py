from datetime import date, datetime, time, timedelta, timezone


def combine_utc(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)


def is_slot_aligned(t: time, slot_minutes: int) -> bool:
    if t.second or t.microsecond:
        return False
    total = t.hour * 60 + t.minute
    return total % slot_minutes == 0


def duration_minutes(start: time, end: time) -> int:
    s = start.hour * 60 + start.minute
    e = end.hour * 60 + end.minute
    return e - s


def iter_day_slot_intervals(day: date, slot_minutes: int) -> list[tuple[datetime, datetime]]:
    slots: list[tuple[datetime, datetime]] = []
    day_start = datetime.combine(day, time(0, 0), tzinfo=timezone.utc)
    m = 0
    while m + slot_minutes <= 24 * 60:
        s = day_start + timedelta(minutes=m)
        e = day_start + timedelta(minutes=m + slot_minutes)
        slots.append((s, e))
        m += slot_minutes
    return slots


def _minutes_since_midnight(t: time) -> int:
    return t.hour * 60 + t.minute


def iter_window_slot_intervals(
    day: date,
    slot_minutes: int,
    window_start: time,
    window_end: time,
) -> list[tuple[datetime, datetime]]:
    """Half-open window [window_start, window_end): slots aligned to slot_minutes from midnight."""
    slots: list[tuple[datetime, datetime]] = []
    day_start = datetime.combine(day, time(0, 0), tzinfo=timezone.utc)
    start_m = _minutes_since_midnight(window_start)
    end_m = _minutes_since_midnight(window_end)
    if end_m <= start_m or slot_minutes <= 0:
        return slots
    # align first slot boundary at or after window_start
    m = start_m
    if m % slot_minutes != 0:
        m = m + (slot_minutes - (m % slot_minutes))
    while m + slot_minutes <= end_m:
        s = day_start + timedelta(minutes=m)
        e = day_start + timedelta(minutes=m + slot_minutes)
        slots.append((s, e))
        m += slot_minutes
    return slots


def ranges_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start
