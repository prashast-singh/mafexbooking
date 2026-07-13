from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking_policy import BookingPolicy


async def get_booking_policy(db: AsyncSession) -> BookingPolicy:
    result = await db.execute(select(BookingPolicy).order_by(BookingPolicy.id.asc()).limit(1))
    policy = result.scalar_one_or_none()
    if policy is None:
        return BookingPolicy(
            slot_minutes=30,
            max_booking_hours_per_day=8,
            max_advance_days=30,
            cancellation_cutoff_minutes=60,
        )
    return policy
