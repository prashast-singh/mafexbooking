import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings


def hash_otp(otp: str) -> str:
    key = get_settings().JWT_SECRET_KEY.encode("utf-8")
    return hmac.new(key, otp.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_otp(plain_otp: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(plain_otp), otp_hash)


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def safe_decode_token(token: str) -> dict[str, Any] | None:
    try:
        return decode_access_token(token)
    except JWTError:
        return None
