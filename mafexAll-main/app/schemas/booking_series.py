import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.booking import BookingOut


class BookingSeriesCreate(BaseModel):
    room_id: int
    unit_id: int
    booking_date: dt.date
    start_time: dt.time
    end_time: dt.time
    purpose: str | None = None
    frequency: Literal["weekly", "monthly"]
    interval: int = Field(1, ge=1, le=12)
    end_date: dt.date | None = None
    max_occurrences: int | None = Field(None, ge=1, le=52)

    @model_validator(mode="after")
    def validate_end_condition(self) -> "BookingSeriesCreate":
        if self.end_date is None and self.max_occurrences is None:
            raise ValueError("Either end_date or max_occurrences is required")
        if self.end_date is not None and self.end_date < self.booking_date:
            raise ValueError("end_date must be on or after booking_date")
        return self


class SeriesSkippedItem(BaseModel):
    date: dt.date
    reason: str


class BookingSeriesPreviewOut(BaseModel):
    total_candidates: int
    bookable: list[dt.date]
    skipped: list[SeriesSkippedItem]


class BookingSeriesOut(BaseModel):
    id: int
    user_id: int
    room_id: int
    room_name: str
    unit_id: int
    unit_name: str
    start_time: dt.time
    end_time: dt.time
    frequency: str
    interval: int
    weekday: int
    series_start_date: dt.date
    end_date: dt.date | None
    max_occurrences: int | None
    purpose: str | None
    created_at: dt.datetime
    created_count: int
    skipped_count: int
    bookings: list[BookingOut]
    skipped: list[SeriesSkippedItem]

    model_config = {"from_attributes": True}


class BookingSeriesCancelBody(BaseModel):
    scope: Literal["all_future", "from_date"]
    from_date: dt.date | None = None
    reason: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def validate_from_date(self) -> "BookingSeriesCancelBody":
        if self.scope == "from_date" and self.from_date is None:
            raise ValueError("from_date is required when scope is from_date")
        return self


class BookingSeriesCancelOut(BaseModel):
    cancelled_count: int
    cancelled_booking_ids: list[int]


class BookingSeriesRescheduleBody(BaseModel):
    anchor_booking_id: int
    scope: Literal["all_future", "from_date"]
    unit_id: int
    start_time: dt.time
    end_time: dt.time
    purpose: str | None = None


class BookingSeriesRescheduleOut(BaseModel):
    updated_count: int
    updated_booking_ids: list[int]
    skipped_count: int


class AdminBookingListItem(BaseModel):
    id: int
    user_id: int
    user_email: str
    user_full_name: str
    room_id: int
    room_name: str
    unit_id: int
    unit_name: str
    booking_date: dt.date
    start_time: dt.time
    end_time: dt.time
    status: str
    purpose: str | None
    series_id: int | None = None
    occurrence_index: int | None = None
    series_frequency: str | None = None
    series_interval: int | None = None


class AdminBookingDetailOut(AdminBookingListItem):
    room_location: str | None = None
    cancellation_reason: str | None = None
    created_at: dt.datetime


class AdminBookingSeriesDetailOut(BaseModel):
    series: BookingSeriesOut
    bookings: list[AdminBookingListItem]
