"""Create the first admin user (no OTP; for bootstrap only)."""

import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApprovalStatus, UserRole, UserType
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.utils.email_norm import normalize_email


async def create_admin(email: str, full_name: str) -> User:
    email_n = normalize_email(email)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            r = await session.execute(select(User).where(User.email == email_n))
            existing = r.scalar_one_or_none()
            if existing:
                existing.role = UserRole.admin.value
                existing.email_verified = True
                existing.approval_status = ApprovalStatus.approved.value
                existing.is_active = True
                existing.full_name = full_name
                await session.flush()
                return existing
            user = User(
                email=email_n,
                full_name=full_name,
                role=UserRole.admin.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user


def main() -> None:
    p = argparse.ArgumentParser(description="Create or promote admin user")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True, dest="full_name")
    args = p.parse_args()
    if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    user = asyncio.run(create_admin(args.email, args.full_name))
    print(f"Admin ready: id={user.id} email={user.email}")
if __name__ == "__main__":
    main()
