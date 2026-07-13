from datetime import datetime

from pydantic import BaseModel, Field


class AmenityOut(BaseModel):
    id: int
    name: str
    icon: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AmenityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    icon: str | None = Field(None, max_length=255)


class AmenityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    icon: str | None = None
