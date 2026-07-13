"""Insert baseline internal domain, amenities, and booking policy (idempotent)."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.amenity import Amenity
from app.models.booking_policy import BookingPolicy
from app.models.internal_domain import InternalDomain


async def run() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _seed(session)


async def _seed(session: AsyncSession) -> None:
    r = await session.execute(
        select(InternalDomain).where(InternalDomain.domain == "uni-marburg.de")
    )
    if r.scalar_one_or_none() is None:
        session.add(InternalDomain(domain="uni-marburg.de", is_active=True))

    for name in ("Whiteboard", "Monitor", "LAN"):
        ar = await session.execute(select(Amenity).where(Amenity.name == name))
        if ar.scalar_one_or_none() is None:
            session.add(Amenity(name=name))

    pr = await session.execute(select(BookingPolicy).limit(1))
    if pr.scalar_one_or_none() is None:
        session.add(
            BookingPolicy(
                slot_minutes=30,
                max_booking_hours_per_day=8,
                max_advance_days=30,
                cancellation_cutoff_minutes=60,
            )
        )


if __name__ == "__main__":
    asyncio.run(run())
