import datetime as dt

from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    room_id: int
    unit_id: int
    booking_date: dt.date
    start_time: dt.time
    end_time: dt.time
    purpose: str | None = None


class BookingOut(BaseModel):
    id: int
    user_id: int
    room_id: int
    unit_id: int
    booking_date: dt.date
    start_time: dt.time
    end_time: dt.time
    start_at: dt.datetime
    end_at: dt.datetime
    purpose: str | None
    status: str
    series_id: int | None = None
    occurrence_index: int | None = None
    decided_by_id: int | None = None
    decided_at: dt.datetime | None = None
    decision_reason: str | None = None
    cancelled_by_id: int | None
    cancellation_reason: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class BookingOutWithRoom(BookingOut):
    room_name: str
    room_location: str | None = None


class BookingCancelBody(BaseModel):
    reason: str | None = Field(None, max_length=2000)
