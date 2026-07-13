from datetime import datetime

from pydantic import BaseModel, Field


class RoomAdminAssignBody(BaseModel):
    user_id: int = Field(..., ge=1)


class RoomAdminOut(BaseModel):
    id: int
    room_id: int
    user_id: int
    user_email: str
    user_full_name: str
    created_at: datetime

