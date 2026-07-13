import datetime as dt

from pydantic import BaseModel, Field


class AmenityBrief(BaseModel):
    id: int
    name: str
    icon: str | None


class RoomImageBrief(BaseModel):
    id: int
    file_url: str
    sort_order: int


class BookableUnitPublic(BaseModel):
    id: int
    name: str
    type: str
    booking_mode: str
    capacity: int
    is_active: bool
    parent_unit_id: int | None


class RoomBrowseItem(BaseModel):
    id: int
    name: str
    description: str | None
    location: str | None
    capacity: int
    booking_mode: str
    is_active: bool
    thumbnail_url: str | None
    amenities: list[AmenityBrief]
    images: list[RoomImageBrief]


class RoomBrowsePage(BaseModel):
    items: list[RoomBrowseItem]
    total: int
    page: int
    limit: int


class RoomDetailPublic(BaseModel):
    id: int
    name: str
    description: str | None
    location: str | None
    capacity: int
    booking_mode: str
    availability_window_start: dt.time
    availability_window_end: dt.time
    is_active: bool
    thumbnail_url: str | None
    amenities: list[AmenityBrief]
    images: list[RoomImageBrief]
    bookable_units: list[BookableUnitPublic]


class SlotUnitAvailability(BaseModel):
    unit_id: int
    unit_name: str
    unit_type: str
    available: bool
    reason: str | None = None


class SlotAvailabilityRow(BaseModel):
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    units: list[SlotUnitAvailability]


class RoomAvailabilityGrid(BaseModel):
    room_id: int
    room_name: str
    date: dt.date
    slot_minutes: int
    availability_window_start: str = Field(..., description="HH:MM")
    availability_window_end: str = Field(..., description="HH:MM")
    slots: list[SlotAvailabilityRow]


class AvailabilitySearchResponse(BaseModel):
    date: dt.date
    slot_minutes: int
    rooms: list[RoomAvailabilityGrid]
