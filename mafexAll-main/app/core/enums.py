from enum import StrEnum


class UserRole(StrEnum):
    user = "user"
    admin = "admin"


class UserType(StrEnum):
    internal = "internal"
    external = "external"


class ApprovalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OtpPurpose(StrEnum):
    signup = "signup"
    login = "login"
    email_change = "email_change"


class BookingMode(StrEnum):
    full_room_only = "full_room_only"
    tables_only = "tables_only"
    hybrid = "hybrid"
    sections_only = "sections_only"


class BookableUnitType(StrEnum):
    full_room = "full_room"
    half_room = "half_room"
    section = "section"
    table = "table"


class BookingStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    denied = "denied"
    cancelled = "cancelled"
    completed = "completed"
