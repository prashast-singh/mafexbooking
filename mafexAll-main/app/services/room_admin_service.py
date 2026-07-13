from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.room import Room
from app.models.room_admin import RoomAdmin
from app.models.user import User
from app.schemas.user import ManagedRoomBrief, UserPublic


async def user_public_out(db: AsyncSession, user: User) -> UserPublic:
    managed_room_ids = await list_managed_room_ids(db, user_id=user.id)
    out = UserPublic.model_validate(user)
    return out.model_copy(update={"managed_room_ids": managed_room_ids})


async def list_managed_room_ids(db: AsyncSession, *, user_id: int) -> list[int]:
    r = await db.execute(select(RoomAdmin.room_id).where(RoomAdmin.user_id == user_id).order_by(RoomAdmin.room_id.asc()))
    return list(r.scalars().all())


async def list_managed_rooms(db: AsyncSession, *, user_id: int) -> list[ManagedRoomBrief]:
    r = await db.execute(
        select(Room.id, Room.name)
        .join(RoomAdmin, RoomAdmin.room_id == Room.id)
        .where(RoomAdmin.user_id == user_id)
        .order_by(Room.name.asc(), Room.id.asc())
    )
    return [ManagedRoomBrief(id=room_id, name=name) for room_id, name in r.all()]


async def can_manage_room(db: AsyncSession, *, actor: User, room_id: int) -> bool:
    if actor.role == "admin":
        return True
    return await is_room_admin(db, room_id=room_id, user_id=actor.id)


async def is_room_admin(db: AsyncSession, *, room_id: int, user_id: int) -> bool:
    r = await db.execute(
        select(RoomAdmin.id).where(RoomAdmin.room_id == room_id, RoomAdmin.user_id == user_id).limit(1)
    )
    return r.scalar_one_or_none() is not None


async def list_room_admins(db: AsyncSession, *, room_id: int) -> list[RoomAdmin]:
    r = await db.execute(
        select(RoomAdmin)
        .where(RoomAdmin.room_id == room_id)
        .options(selectinload(RoomAdmin.user))
        .order_by(RoomAdmin.created_at.asc())
    )
    return list(r.scalars().all())


async def add_room_admin(db: AsyncSession, *, room_id: int, user_id: int) -> RoomAdmin:
    row = RoomAdmin(room_id=room_id, user_id=user_id)
    db.add(row)
    await db.flush()
    await db.refresh(row, attribute_names=["user"])
    r = await db.execute(
        select(RoomAdmin)
        .where(RoomAdmin.id == row.id)
        .options(selectinload(RoomAdmin.user))
    )
    return r.scalar_one()


async def remove_room_admin(db: AsyncSession, *, room_id: int, user_id: int) -> bool:
    r = await db.execute(delete(RoomAdmin).where(RoomAdmin.room_id == room_id, RoomAdmin.user_id == user_id))
    return bool(r.rowcount)

