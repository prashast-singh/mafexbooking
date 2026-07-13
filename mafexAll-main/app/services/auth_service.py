from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApprovalStatus, OtpPurpose, UserRole, UserType
from app.core.security import create_access_token
from app.models.user import User
from app.services.email_service import send_otp_email
from app.services.internal_domain_service import is_internal_email
from app.services.otp_service import create_and_store_otp, verify_otp_code
from app.services.user_admin_service import ensure_user_account_active
from app.utils.email_norm import normalize_email


class AuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def signup_request(
    db: AsyncSession,
    *,
    email: str,
    full_name: str,
) -> None:
    email_n = normalize_email(email)
    result = await db.execute(select(User).where(User.email == email_n))
    existing = result.scalar_one_or_none()
    if existing and existing.email_verified:
        raise AuthError("email_taken", "Email is already registered", 409)
    internal = await is_internal_email(db, email_n)
    user_type = UserType.internal if internal else UserType.external
    if existing and not existing.email_verified:
        existing.full_name = full_name
        existing.user_type = user_type.value
    else:
        user = User(
            email=email_n,
            full_name=full_name,
            role=UserRole.user.value,
            user_type=user_type.value,
            email_verified=False,
            approval_status=ApprovalStatus.pending.value,
            is_active=True,
        )
        db.add(user)
    await db.flush()
    otp = await create_and_store_otp(db, email_n, OtpPurpose.signup)
    await send_otp_email(email_n, otp, OtpPurpose.signup.value)


async def verify_signup_otp(
    db: AsyncSession,
    *,
    email: str,
    otp: str,
) -> str:
    email_n = normalize_email(email)
    ok = await verify_otp_code(db, email_n, OtpPurpose.signup, otp)
    if not ok:
        raise AuthError("invalid_otp", "Invalid or expired OTP", 400)
    result = await db.execute(select(User).where(User.email == email_n))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("not_found", "User not found", 404)
    user.email_verified = True
    user.approval_status = ApprovalStatus.pending.value
    await db.flush()
    token = create_access_token(str(user.id), {"role": user.role})
    return token


async def resend_otp(
    db: AsyncSession,
    *,
    email: str,
    purpose: OtpPurpose,
) -> None:
    email_n = normalize_email(email)
    result = await db.execute(select(User).where(User.email == email_n))
    user = result.scalar_one_or_none()
    if purpose == OtpPurpose.signup:
        if user is None:
            raise AuthError("not_found", "User not found", 404)
        if user.email_verified:
            raise AuthError("already_verified", "Email already verified", 400)
    elif purpose == OtpPurpose.login:
        if user is None or not user.email_verified:
            raise AuthError("not_found", "User not found", 404)
    otp = await create_and_store_otp(db, email_n, purpose)
    await send_otp_email(email_n, otp, purpose.value)


async def login_request_otp(db: AsyncSession, *, email: str) -> None:
    email_n = normalize_email(email)
    result = await db.execute(select(User).where(User.email == email_n))
    user = result.scalar_one_or_none()
    if user is None or not user.email_verified:
        raise AuthError("not_found", "User not found", 404)
    otp = await create_and_store_otp(db, email_n, OtpPurpose.login)
    await send_otp_email(email_n, otp, OtpPurpose.login.value)


async def login_verify_otp(db: AsyncSession, *, email: str, otp: str) -> str:
    email_n = normalize_email(email)
    ok = await verify_otp_code(db, email_n, OtpPurpose.login, otp)
    if not ok:
        raise AuthError("invalid_otp", "Invalid or expired OTP", 400)
    result = await db.execute(select(User).where(User.email == email_n))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("not_found", "User not found", 404)
    user = await ensure_user_account_active(db, user)
    if not user.is_active:
        raise AuthError("not_found", "User not found", 404)
    return create_access_token(str(user.id), {"role": user.role})
