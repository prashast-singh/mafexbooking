from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class InternalDomainCreate(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)


class InternalDomainOut(BaseModel):
    id: int
    domain: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingPolicyOut(BaseModel):
    id: int
    slot_minutes: int
    max_booking_hours_per_day: int
    max_advance_days: int
    cancellation_cutoff_minutes: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingPolicyUpdate(BaseModel):
    slot_minutes: int | None = Field(None, ge=15, le=120)
    max_booking_hours_per_day: int | None = Field(None, ge=1, le=24)
    max_advance_days: int | None = Field(None, ge=1, le=365)
    cancellation_cutoff_minutes: int | None = Field(None, ge=0, le=10080)


class AdminUserOut(BaseModel):
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
    approved_by_id: int | None

    model_config = {"from_attributes": True}


class AdminRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(user|admin)$")


class AdminDashboardSummary(BaseModel):
    pending_approvals: int
    rooms_total: int
    bookings_today: int
    users_total: int
