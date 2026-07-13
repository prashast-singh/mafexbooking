from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.amenity import RoomAmenity
from app.models.room import Room, RoomImage
from app.models.tag import RoomTag
from app.models.unit import BookableUnit
from app.models.user import User
from app.schemas.room_frontend import (
    AmenityBrief,
    BookableUnitPublic,
    RoomBrowseItem,
    RoomDetailPublic,
    RoomImageBrief,
    TagBrief,
)
from app.services.tag_visibility_service import apply_tag_visibility, load_user_tag_ids


def sorted_room_images(room: Room) -> list[RoomImage]:
    return sorted(room.images, key=lambda i: (i.sort_order, i.id))


def thumbnail_url_for_room(room: Room) -> str | None:
    imgs = sorted_room_images(room)
    return imgs[0].file_url if imgs else None


def tag_briefs_for_room(room: Room) -> list[TagBrief]:
    links = sorted(room.tag_links, key=lambda x: (x.tag.name.lower(), x.tag.id))
    return [TagBrief(id=link.tag.id, name=link.tag.name) for link in links]


def amenity_briefs_for_room(room: Room) -> list[AmenityBrief]:
    links = sorted(room.amenity_links, key=lambda x: (x.amenity.name.lower(), x.amenity.id))
    return [
        AmenityBrief(id=link.amenity.id, name=link.amenity.name, icon=link.amenity.icon)
        for link in links
    ]


def image_briefs_for_room(room: Room) -> list[RoomImageBrief]:
    return [
        RoomImageBrief(id=i.id, file_url=i.file_url, sort_order=i.sort_order)
        for i in sorted_room_images(room)
    ]


def room_to_browse_item(room: Room) -> RoomBrowseItem:
    return RoomBrowseItem(
        id=room.id,
        name=room.name,
        description=room.description,
        location=room.location,
        capacity=room.capacity,
        booking_mode=room.booking_mode,
        is_active=room.is_active,
        thumbnail_url=thumbnail_url_for_room(room),
        amenities=amenity_briefs_for_room(room),
        tags=tag_briefs_for_room(room),
        images=image_briefs_for_room(room),
    )


def room_to_detail_public(room: Room) -> RoomDetailPublic:
    units = sorted(room.bookable_units, key=lambda u: u.id)
    return RoomDetailPublic(
        id=room.id,
        name=room.name,
        description=room.description,
        location=room.location,
        capacity=room.capacity,
        booking_mode=room.booking_mode,
        availability_window_start=room.availability_window_start,
        availability_window_end=room.availability_window_end,
        is_active=room.is_active,
        thumbnail_url=thumbnail_url_for_room(room),
        amenities=amenity_briefs_for_room(room),
        tags=tag_briefs_for_room(room),
        images=image_briefs_for_room(room),
        bookable_units=[
            BookableUnitPublic(
                id=u.id,
                name=u.name,
                type=u.type,
                booking_mode=u.booking_mode,
                capacity=u.capacity,
                is_active=u.is_active,
                parent_unit_id=u.parent_unit_id,
            )
            for u in units
        ],
    )


def normalize_unit_type_filter(raw: str | None) -> str | None:
    if raw is None or raw == "":
        return None
    if raw == "room":
        return "full_room"
    allowed = {"full_room", "half_room", "section", "table"}
    if raw not in allowed:
        return "__invalid__"
    return raw


def select_rooms_browse_base(
    *,
    capacity: int | None,
    amenity_ids: list[int] | None,
    unit_type: str | None,
    user_tag_ids: list[int] | None = None,
):
    stmt = select(Room).where(Room.is_active.is_(True))

    if capacity is not None:
        unit_cap = exists().where(
            BookableUnit.room_id == Room.id,
            BookableUnit.is_active.is_(True),
            BookableUnit.capacity >= capacity,
        )
        stmt = stmt.where(or_(Room.capacity >= capacity, unit_cap))

    if amenity_ids:
        sub = (
            select(RoomAmenity.room_id)
            .where(RoomAmenity.amenity_id.in_(amenity_ids))
            .group_by(RoomAmenity.room_id)
            .having(func.count(func.distinct(RoomAmenity.amenity_id)) == len(amenity_ids))
        )
        stmt = stmt.where(Room.id.in_(sub))

    if unit_type is not None:
        stmt = stmt.where(
            exists().where(
                BookableUnit.room_id == Room.id,
                BookableUnit.is_active.is_(True),
                BookableUnit.type == unit_type,
            )
        )

    stmt = apply_tag_visibility(stmt, user_tag_ids)

    return stmt.options(
        selectinload(Room.images),
        selectinload(Room.amenity_links).selectinload(RoomAmenity.amenity),
        selectinload(Room.tag_links).selectinload(RoomTag.tag),
    ).order_by(Room.name.asc())


async def fetch_rooms_for_browse(
    db: AsyncSession,
    *,
    capacity: int | None,
    amenity_ids: list[int] | None,
    unit_type: str | None,
    user: User | None = None,
) -> list[Room]:
    user_tag_ids = None
    if user is not None:
        user_tag_ids = await load_user_tag_ids(db, user.id)
    stmt = select_rooms_browse_base(
        capacity=capacity,
        amenity_ids=amenity_ids,
        unit_type=unit_type,
        user_tag_ids=user_tag_ids,
    )
    r = await db.execute(stmt)
    return list(r.scalars().unique().all())


