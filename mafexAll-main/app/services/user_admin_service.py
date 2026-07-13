from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.models.booking import Booking
from app.models.user import User
from app.models.user_email_history import UserEmailHistory


class UserAdminError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def ensure_user_account_active(db: AsyncSession, user: User) -> User:
    """Apply scheduled deactivation lazily when deactivate_at has passed."""
    if user.deactivate_at is None:
        return user
    at = _normalize_dt(user.deactivate_at)
    if at <= _utc_now():
        user.is_active = False
        await db.flush()
        await db.refresh(user)
    return user


async def _assert_not_last_admin(db: AsyncSession, target: User) -> None:
    if target.role != UserRole.admin.value:
        return
    r = await db.execute(
        select(func.count())
        .select_from(User)
        .where(User.role == UserRole.admin.value)
    )
    if int(r.scalar_one()) <= 1:
        raise UserAdminError("last_admin", "Cannot modify the last admin account", 400)


async def update_user_status(
    db: AsyncSession,
    *,
    actor: User,
    user_id: int,
    is_active: bool | None = None,
    deactivate_at: datetime | None = None,
    set_is_active: bool = False,
    set_deactivate_at: bool = False,
) -> User:
    if user_id == actor.id:
        raise UserAdminError("self_action", "Cannot change your own account status", 400)

    user = await db.get(User, user_id)
    if user is None:
        raise UserAdminError("not_found", "User not found", 404)

    if set_is_active:
        if is_active is False:
            await _assert_not_last_admin(db, user)
            user.is_active = False
            user.deactivate_at = None
        elif is_active is True:
            user.is_active = True
            user.deactivate_at = None

    if set_deactivate_at:
        if deactivate_at is None:
            user.deactivate_at = None
        else:
            at = _normalize_dt(deactivate_at)
            if at <= _utc_now():
                raise UserAdminError("invalid_date", "deactivate_at must be in the future", 400)
            user.deactivate_at = at
            user.is_active = True

    await db.flush()
    await db.refresh(user)
    return user


async def delete_user_account(
    db: AsyncSession,
    *,
    actor: User,
    user_id: int,
) -> None:
    if user_id == actor.id:
        raise UserAdminError("self_action", "Cannot delete your own account", 400)

    user = await db.get(User, user_id)
    if user is None:
        raise UserAdminError("not_found", "User not found", 404)

    await _assert_not_last_admin(db, user)

    await db.execute(
        update(Booking)
        .where(Booking.decided_by_id == user_id)
        .values(decided_by_id=None)
    )
    await db.execute(
        update(Booking)
        .where(Booking.cancelled_by_id == user_id)
        .values(cancelled_by_id=None)
    )
    await db.execute(
        update(User)
        .where(User.approved_by_id == user_id)
        .values(approved_by_id=None)
    )
    await db.execute(
        update(UserEmailHistory)
        .where(UserEmailHistory.changed_by_id == user_id)
        .values(changed_by_id=None)
    )

    await db.execute(delete(User).where(User.id == user_id))
    await db.flush()
