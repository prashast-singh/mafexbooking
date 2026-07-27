from app.core.config import get_settings


def frontend_base_url() -> str:
    return get_settings().frontend_base_url


def admin_approvals_url() -> str:
    return f"{frontend_base_url()}/admin/approvals"


def admin_booking_requests_url() -> str:
    return f"{frontend_base_url()}/admin/booking-requests"
