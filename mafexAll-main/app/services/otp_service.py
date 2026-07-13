from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import OtpPurpose
from app.core.security import generate_otp_code, hash_otp, verify_otp
from app.models.otp import OtpCode


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def create_and_store_otp(
    db: AsyncSession,
    email: str,
    purpose: OtpPurpose,
) -> str:
    settings = get_settings()
    otp = generate_otp_code()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    row = OtpCode(
        email=email,
        otp_hash=hash_otp(otp),
        purpose=purpose.value,
        expires_at=expires,
        attempts=0,
    )
    db.add(row)
    await db.flush()
    return otp


async def verify_otp_code(
    db: AsyncSession,
    email: str,
    purpose: OtpPurpose,
    plain_otp: str,
) -> bool:
    settings = get_settings()
    result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.email == email,
            OtpCode.purpose == purpose.value,
            OtpCode.used_at.is_(None),
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    now = datetime.now(timezone.utc)
    if _as_utc_aware(row.expires_at) < now:
        return False
    if row.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False
    if not verify_otp(plain_otp, row.otp_hash):
        row.attempts += 1
        return False
    row.used_at = now
    return True
