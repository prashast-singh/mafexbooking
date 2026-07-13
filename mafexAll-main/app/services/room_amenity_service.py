from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import HTTPException

from app.models.amenity import Amenity, RoomAmenity
from app.models.room import Room
from app.schemas.amenity import AmenityOut
from app.services.room_tag_service import load_room_tag_rows, tags_to_out


def dedupe_amenity_ids(amenity_ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for aid in amenity_ids:
        if aid not in seen:
            seen.add(aid)
            out.append(aid)
    return out


async def ensure_amenities_exist(db: AsyncSession, amenity_ids: list[int]) -> None:
    if not amenity_ids:
        return
    r = await db.execute(select(Amenity.id).where(Amenity.id.in_(amenity_ids)))
    found = {row[0] for row in r.all()}
    missing = [i for i in amenity_ids if i not in found]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown amenity id(s): {missing}",
        )


async def get_room_or_404(db: AsyncSession, room_id: int) -> Room:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


async def load_room_amenity_rows(db: AsyncSession, room_id: int) -> list[Amenity]:
    r = await db.execute(
        select(RoomAmenity)
        .options(selectinload(RoomAmenity.amenity))
        .where(RoomAmenity.room_id == room_id)
    )
    links = r.scalars().all()
    amenities = [link.amenity for link in links]
    amenities.sort(key=lambda a: a.name.lower())
    return amenities


def amenities_to_out(amenities: list[Amenity]) -> list[AmenityOut]:
    return [AmenityOut.model_validate(a) for a in amenities]


async def list_room_amenities_out(db: AsyncSession, room_id: int) -> list[AmenityOut]:
    await get_room_or_404(db, room_id)
    return amenities_to_out(await load_room_amenity_rows(db, room_id))


async def replace_room_amenities(db: AsyncSession, room_id: int, amenity_ids: list[int]) -> None:
    unique = dedupe_amenity_ids(amenity_ids)
    await ensure_amenities_exist(db, unique)
    await db.execute(delete(RoomAmenity).where(RoomAmenity.room_id == room_id))
    for aid in unique:
        db.add(RoomAmenity(room_id=room_id, amenity_id=aid))
    await db.flush()


async def attach_room_amenity(db: AsyncSession, room_id: int, amenity_id: int) -> list[AmenityOut]:
    await get_room_or_404(db, room_id)
    await ensure_amenities_exist(db, [amenity_id])
    existing = await db.execute(
        select(RoomAmenity.id).where(
            RoomAmenity.room_id == room_id,
            RoomAmenity.amenity_id == amenity_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Amenity already linked to this room")
    db.add(RoomAmenity(room_id=room_id, amenity_id=amenity_id))
    await db.flush()
    return amenities_to_out(await load_room_amenity_rows(db, room_id))


async def detach_room_amenity(db: AsyncSession, room_id: int, amenity_id: int) -> list[AmenityOut]:
    await get_room_or_404(db, room_id)
    await db.execute(
        delete(RoomAmenity).where(
            RoomAmenity.room_id == room_id,
            RoomAmenity.amenity_id == amenity_id,
        )
    )
    await db.flush()
    return amenities_to_out(await load_room_amenity_rows(db, room_id))


async def room_admin_out(db: AsyncSession, room: Room):
    from app.schemas.room import RoomAdminOut

    amenities = await load_room_amenity_rows(db, room.id)
    tags = await load_room_tag_rows(db, room.id)
    return RoomAdminOut(
        id=room.id,
        name=room.name,
        description=room.description,
        location=room.location,
        capacity=room.capacity,
        booking_mode=room.booking_mode,
        availability_window_start=room.availability_window_start,
        availability_window_end=room.availability_window_end,
        is_active=room.is_active,
        created_at=room.created_at,
        amenities=amenities_to_out(amenities),
        tags=tags_to_out(tags),
    )
