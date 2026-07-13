from datetime import datetime

from pydantic import BaseModel, Field


class TagOut(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TagBrief(BaseModel):
    id: int
    name: str


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=2000)


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None


class UserTagsUpdate(BaseModel):
    tag_ids: list[int] = Field(default_factory=list)
