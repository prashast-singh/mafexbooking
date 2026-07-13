from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    user_type: str
    email_verified: bool
    approval_status: str
    is_active: bool
    created_at: datetime
    approved_at: datetime | None
    managed_room_ids: list[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ManagedRoomBrief(BaseModel):
    id: int
    name: str


class UserMeUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)


class EmailChangeRequestBody(BaseModel):
    new_email: EmailStr


class EmailChangeVerifyBody(BaseModel):
    new_email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class UserEmailHistoryOut(BaseModel):
    id: int
    email: EmailStr
    changed_at: datetime

    model_config = {"from_attributes": True}
