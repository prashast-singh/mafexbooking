from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OtpPurpose, UserType
from app.models.user import User
from app.models.user_email_history import UserEmailHistory
from app.services.auth_service import AuthError
from app.services.email_service import send_otp_email
from app.services.internal_domain_service import is_internal_email
from app.services.otp_service import create_and_store_otp, verify_otp_code
from app.utils.email_norm import normalize_email


async def request_email_change_otp(db: AsyncSession, *, user: User, new_email: str) -> None:
    email_n = normalize_email(new_email)
    if email_n == user.email:
        raise AuthError("same_email", "New email must differ from current email", 400)
    result = await db.execute(select(User).where(User.email == email_n))
    existing = result.scalar_one_or_none()
    if existing is not None and existing.id != user.id:
        raise AuthError("email_taken", "Email is already registered", 409)
    otp = await create_and_store_otp(db, email_n, OtpPurpose.email_change)
    await send_otp_email(email_n, otp, OtpPurpose.email_change.value)


async def verify_email_change_otp(
    db: AsyncSession,
    *,
    user: User,
    new_email: str,
    otp: str,
) -> User:
    email_n = normalize_email(new_email)
    ok = await verify_otp_code(db, email_n, OtpPurpose.email_change, otp)
    if not ok:
        raise AuthError("invalid_otp", "Invalid or expired OTP", 400)
    result = await db.execute(select(User).where(User.email == email_n))
    existing = result.scalar_one_or_none()
    if existing is not None and existing.id != user.id:
        raise AuthError("email_taken", "Email is already registered", 409)
    if email_n != user.email:
        db.add(
            UserEmailHistory(
                user_id=user.id,
                email=user.email,
                changed_by_id=user.id,
            )
        )
        user.email = email_n
        internal = await is_internal_email(db, email_n)
        user.user_type = UserType.internal.value if internal else UserType.external.value
        user.email_verified = True
    await db.flush()
    await db.refresh(user)
    return user


async def list_user_email_history(db: AsyncSession, *, user_id: int) -> list[UserEmailHistory]:
    r = await db.execute(
        select(UserEmailHistory)
        .where(UserEmailHistory.user_id == user_id)
        .order_by(UserEmailHistory.changed_at.desc())
    )
    return list(r.scalars().all())
