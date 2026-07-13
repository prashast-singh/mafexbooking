from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.tag import RoomTag, UserTag
from app.models.user import User


async def load_user_tag_ids(db: AsyncSession, user_id: int) -> list[int]:
    r = await db.execute(select(UserTag.tag_id).where(UserTag.user_id == user_id))
    return list(r.scalars().all())


def apply_tag_visibility(stmt, user_tag_ids: list[int] | None):
    """Filter rooms by tag visibility rules.

    - No user tags: no filter (see everything).
    - User has tags: only rooms sharing at least one tag (untagged rooms excluded).
    """
    if not user_tag_ids:
        return stmt
    overlap = exists().where(
        RoomTag.room_id == Room.id,
        RoomTag.tag_id.in_(user_tag_ids),
    )
    return stmt.where(overlap)


async def room_visible_to_user(
    db: AsyncSession,
    *,
    room_id: int,
    user: User | None,
) -> bool:
    if user is None:
        return True
    user_tag_ids = await load_user_tag_ids(db, user.id)
    if not user_tag_ids:
        return True
    r = await db.execute(
        select(RoomTag.id).where(
            RoomTag.room_id == room_id,
            RoomTag.tag_id.in_(user_tag_ids),
        ).limit(1)
    )
    return r.scalar_one_or_none() is not None
