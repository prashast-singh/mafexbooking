from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.amenity import AmenityOut


def _dedupe_int_ids(ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


class RoomImageOut(BaseModel):
    id: int
    room_id: int
    file_url: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BookableUnitOut(BaseModel):
    id: int
    room_id: int
    parent_unit_id: int | None
    name: str
    type: str
    booking_mode: str
    capacity: int
    is_active: bool

    model_config = {"from_attributes": True}


def _validate_availability_window(start: time, end: time) -> None:
    if end <= start:
        raise ValueError("availability_window_end must be after availability_window_start")


class RoomListOut(BaseModel):
    id: int
    name: str
    description: str | None
    location: str | None
    capacity: int
    booking_mode: str
    availability_window_start: time
    availability_window_end: time
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomAdminOut(RoomListOut):
    amenities: list[AmenityOut]


class RoomDetailOut(RoomListOut):
    images: list[RoomImageOut]
    amenities: list[str]
    bookable_units: list[BookableUnitOut]


class RoomAmenityAttach(BaseModel):
    amenity_id: int = Field(..., ge=1)


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    location: str | None = Field(None, max_length=512)
    capacity: int = Field(1, ge=1)
    booking_mode: str = Field(
        ...,
        pattern="^(full_room_only|tables_only|hybrid|sections_only)$",
    )
    is_active: bool = True
    availability_window_start: time = time(8, 0)
    availability_window_end: time = time(20, 0)
    amenity_ids: list[int] | None = None

    @field_validator("amenity_ids")
    @classmethod
    def dedupe_amenity_ids(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        return _dedupe_int_ids(v)

    @model_validator(mode="after")
    def validate_window(self) -> "RoomCreate":
        _validate_availability_window(
            self.availability_window_start, self.availability_window_end
        )
        return self


class RoomUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    location: str | None = Field(None, max_length=512)
    capacity: int | None = Field(None, ge=1)
    booking_mode: str | None = Field(
        None,
        pattern="^(full_room_only|tables_only|hybrid|sections_only)$",
    )
    is_active: bool | None = None
    availability_window_start: time | None = None
    availability_window_end: time | None = None
    amenity_ids: list[int] | None = None

    @field_validator("amenity_ids")
    @classmethod
    def dedupe_amenity_ids(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        return _dedupe_int_ids(v)

    @model_validator(mode="after")
    def validate_window(self) -> "RoomUpdate":
        if self.availability_window_start is not None and self.availability_window_end is not None:
            _validate_availability_window(
                self.availability_window_start, self.availability_window_end
            )
        return self


class BookableUnitCreate(BaseModel):
    parent_unit_id: int | None = None
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(
        ...,
        pattern="^(full_room|half_room|section|table)$",
    )
    booking_mode: str = Field("direct", pattern="^(direct|request)$")
    capacity: int = Field(1, ge=1)
    is_active: bool = True


class BookableUnitUpdate(BaseModel):
    parent_unit_id: int | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    type: str | None = Field(
        None,
        pattern="^(full_room|half_room|section|table)$",
    )
    booking_mode: str | None = Field(None, pattern="^(direct|request)$")
    capacity: int | None = Field(None, ge=1)
    is_active: bool | None = None


class UnitConflictCreate(BaseModel):
    conflict_with_unit_id: int
