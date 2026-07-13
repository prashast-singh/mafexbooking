from pydantic import BaseModel, Field

from app.schemas.booking import BookingOut


class BookingDecisionBody(BaseModel):
    reason: str | None = Field(None, max_length=2000)


class PendingBookingOut(BookingOut):
    room_name: str
    unit_name: str
    user_full_name: str
    user_email: str

