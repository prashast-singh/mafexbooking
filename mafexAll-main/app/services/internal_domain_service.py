from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.internal_domain import InternalDomain


async def is_internal_email(db: AsyncSession, email: str) -> bool:
    domain = email.split("@", 1)[-1].lower() if "@" in email else ""
    if not domain:
        return False
    result = await db.execute(
        select(InternalDomain).where(
            InternalDomain.domain == domain,
            InternalDomain.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None
