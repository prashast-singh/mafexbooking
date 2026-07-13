from pydantic import BaseModel, Field

from app.schemas.booking import BookingOut


class BookingDecisionBody(BaseModel):
    reason: str | None = Field(None, max_length=2000)


class PendingBookingOut(BookingOut):
    room_name: str
    unit_name: str
    user_full_name: str
    user_email: str
    series_frequency: str | None = None
    series_interval: int | None = None


class BookingSeriesBatchOut(BaseModel):
    processed_count: int
    booking_ids: list[int]
    skipped_count: int = 0

