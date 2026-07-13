from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import HTTPException

from app.models.room import Room
from app.models.tag import RoomTag, Tag, UserTag
from app.schemas.tag import TagOut


def dedupe_tag_ids(tag_ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for tid in tag_ids:
        if tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


async def ensure_tags_exist(db: AsyncSession, tag_ids: list[int]) -> None:
    if not tag_ids:
        return
    r = await db.execute(select(Tag.id).where(Tag.id.in_(tag_ids)))
    found = {row[0] for row in r.all()}
    missing = [i for i in tag_ids if i not in found]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown tag id(s): {missing}",
        )


async def get_room_or_404(db: AsyncSession, room_id: int) -> Room:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


async def load_room_tag_rows(db: AsyncSession, room_id: int) -> list[Tag]:
    r = await db.execute(
        select(RoomTag)
        .options(selectinload(RoomTag.tag))
        .where(RoomTag.room_id == room_id)
    )
    links = r.scalars().all()
    tags = [link.tag for link in links]
    tags.sort(key=lambda t: t.name.lower())
    return tags


def tags_to_out(tags: list[Tag]) -> list[TagOut]:
    return [TagOut.model_validate(t) for t in tags]


async def list_room_tags_out(db: AsyncSession, room_id: int) -> list[TagOut]:
    await get_room_or_404(db, room_id)
    return tags_to_out(await load_room_tag_rows(db, room_id))


async def replace_room_tags(db: AsyncSession, room_id: int, tag_ids: list[int]) -> None:
    unique = dedupe_tag_ids(tag_ids)
    await ensure_tags_exist(db, unique)
    await db.execute(delete(RoomTag).where(RoomTag.room_id == room_id))
    for tid in unique:
        db.add(RoomTag(room_id=room_id, tag_id=tid))
    await db.flush()


async def attach_room_tag(db: AsyncSession, room_id: int, tag_id: int) -> list[TagOut]:
    await get_room_or_404(db, room_id)
    await ensure_tags_exist(db, [tag_id])
    existing = await db.execute(
        select(RoomTag.id).where(
            RoomTag.room_id == room_id,
            RoomTag.tag_id == tag_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Tag already linked to this room")
    db.add(RoomTag(room_id=room_id, tag_id=tag_id))
    await db.flush()
    return tags_to_out(await load_room_tag_rows(db, room_id))


async def detach_room_tag(db: AsyncSession, room_id: int, tag_id: int) -> list[TagOut]:
    await get_room_or_404(db, room_id)
    await db.execute(
        delete(RoomTag).where(
            RoomTag.room_id == room_id,
            RoomTag.tag_id == tag_id,
        )
    )
    await db.flush()
    return tags_to_out(await load_room_tag_rows(db, room_id))


async def load_user_tag_ids_for_user(db: AsyncSession, user_id: int) -> list[int]:
    r = await db.execute(select(UserTag.tag_id).where(UserTag.user_id == user_id))
    return list(r.scalars().all())


async def set_user_tags(db: AsyncSession, user_id: int, tag_ids: list[int]) -> list[TagOut]:
    from app.models.user import User

    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    unique = dedupe_tag_ids(tag_ids)
    await ensure_tags_exist(db, unique)
    await db.execute(delete(UserTag).where(UserTag.user_id == user_id))
    for tid in unique:
        db.add(UserTag(user_id=user_id, tag_id=tid))
    await db.flush()
    r = await db.execute(
        select(Tag)
        .join(UserTag, UserTag.tag_id == Tag.id)
        .where(UserTag.user_id == user_id)
        .order_by(Tag.name.asc())
    )
    return tags_to_out(list(r.scalars().all()))
