import asyncio
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser, CurrentUser
from app.core.enums import ApprovalStatus, UserType
from app.db.session import get_db
from app.models.amenity import Amenity
from app.models.booking import Booking
from app.models.booking_policy import BookingPolicy
from app.models.internal_domain import InternalDomain
from app.models.room import Room, RoomImage
from app.models.unit import BookableUnit, UnitConflict
from app.models.user import User
from app.schemas.admin import (
    AdminDashboardSummary,
    AdminRoleUpdate,
    AdminUserOut,
    BookingPolicyOut,
    BookingPolicyUpdate,
    InternalDomainCreate,
    InternalDomainOut,
)
from app.schemas.amenity import AmenityCreate, AmenityOut, AmenityUpdate
from app.schemas.booking import BookingOut
from app.schemas.booking_admin import BookingDecisionBody, PendingBookingOut
from app.schemas.booking_series import (
    AdminBookingDetailOut,
    AdminBookingListItem,
    AdminBookingSeriesDetailOut,
    BookingSeriesCancelBody,
    BookingSeriesCancelOut,
)
from app.schemas.room import (
    BookableUnitCreate,
    BookableUnitOut,
    BookableUnitUpdate,
    RoomAdminOut,
    RoomAmenityAttach,
    RoomCreate,
    RoomImageOut,
    RoomUpdate,
    UnitConflictCreate,
)
from app.schemas.room_admin import RoomAdminAssignBody, RoomAdminOut as RoomAdminMappingOut
from app.schemas.user import UserEmailHistoryOut
from app.services.room_amenity_service import (
    attach_room_amenity,
    detach_room_amenity,
    list_room_amenities_out,
    replace_room_amenities,
    room_admin_out,
)
from app.services.user_profile_service import list_user_email_history
from app.services.room_image_storage import delete_local_room_image, process_upload_bytes
from app.services.room_admin_service import add_room_admin, can_manage_room, list_room_admins, remove_room_admin
from app.services.booking_service import (
    BookingError,
    approve_pending_booking,
    cancel_booking,
    deny_pending_booking,
    list_pending_bookings_for_actor,
)
from app.services.booking_series_service import (
    cancel_booking_series,
    get_admin_booking_detail,
    get_admin_booking_series_detail,
    list_bookings_for_admin,
)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
async def admin_list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    approval_status: str | None = None,
    q: str | None = Query(None, min_length=1, max_length=200),
) -> list[AdminUserOut]:
    stmt = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    if approval_status is not None:
        stmt = stmt.where(User.approval_status == approval_status)
    if q is not None:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where((User.email.ilike(pattern)) | (User.full_name.ilike(pattern)))
    r = await db.execute(stmt)
    return [AdminUserOut.model_validate(u) for u in r.scalars().all()]


@router.get("/users/pending-approvals", response_model=list[AdminUserOut])
async def pending_users(db: Annotated[AsyncSession, Depends(get_db)], _: AdminUser) -> list[AdminUserOut]:
    r = await db.execute(
        select(User)
        .where(
            User.approval_status == ApprovalStatus.pending.value,
            User.email_verified.is_(True),
        )
        .order_by(User.created_at.asc())
    )
    return [AdminUserOut.model_validate(u) for u in r.scalars().all()]


@router.post("/users/{user_id}/approve", response_model=AdminUserOut)
async def approve_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminUser,
) -> AdminUserOut:
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    u.approval_status = ApprovalStatus.approved.value
    u.approved_by_id = admin.id
    u.approved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(u)
    return AdminUserOut.model_validate(u)


@router.post("/users/{user_id}/reject", response_model=AdminUserOut)
async def reject_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: AdminUser,
) -> AdminUserOut:
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    u.approval_status = ApprovalStatus.rejected.value
    u.approved_by_id = admin.id
    u.approved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(u)
    return AdminUserOut.model_validate(u)


@router.get("/users/{user_id}/email-history", response_model=list[UserEmailHistoryOut])
async def admin_user_email_history(
    user_id: int,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserEmailHistoryOut]:
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    rows = await list_user_email_history(db, user_id=user_id)
    return [UserEmailHistoryOut.model_validate(r) for r in rows]


@router.get("/bookings/pending", response_model=list[PendingBookingOut])
async def list_pending_bookings(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    room_id: int | None = Query(None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    rows = await list_pending_bookings_for_actor(
        db,
        actor=user,
        room_id=room_id,
        skip=skip,
        limit=limit,
    )
    if not rows:
        return []

    room_ids = {b.room_id for b in rows}
    unit_ids = {b.unit_id for b in rows}
    user_ids = {b.user_id for b in rows}
    room_rows = await db.execute(select(Room.id, Room.name).where(Room.id.in_(room_ids)))
    unit_rows = await db.execute(select(BookableUnit.id, BookableUnit.name).where(BookableUnit.id.in_(unit_ids)))
    user_rows = await db.execute(select(User.id, User.full_name, User.email).where(User.id.in_(user_ids)))
    room_names = {rid: name for rid, name in room_rows.all()}
    unit_names = {uid: name for uid, name in unit_rows.all()}
    users = {uid: (name, email) for uid, name, email in user_rows.all()}

    out: list[PendingBookingOut] = []
    for booking in rows:
        user_name, user_email = users.get(booking.user_id, ("Unknown", ""))
        out.append(
            PendingBookingOut(
                **BookingOut.model_validate(booking).model_dump(),
                room_name=room_names.get(booking.room_id, f"Room #{booking.room_id}"),
                unit_name=unit_names.get(booking.unit_id, f"Unit #{booking.unit_id}"),
                user_full_name=user_name,
                user_email=user_email,
            )
        )
    return out


@router.post("/bookings/{booking_id}/approve", response_model=BookingOut)
async def approve_booking(
    booking_id: int,
    body: BookingDecisionBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    b = await approve_pending_booking(db, actor=user, booking_id=booking_id, reason=body.reason)
    return BookingOut.model_validate(b)


@router.post("/bookings/{booking_id}/deny", response_model=BookingOut)
async def deny_booking(
    booking_id: int,
    body: BookingDecisionBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    b = await deny_pending_booking(db, actor=user, booking_id=booking_id, reason=body.reason)
    return BookingOut.model_validate(b)


@router.get("/bookings/series/{series_id}", response_model=AdminBookingSeriesDetailOut)
async def admin_get_booking_series(
    series_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBookingSeriesDetailOut:
    try:
        return await get_admin_booking_series_detail(db, actor=user, series_id=series_id)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.patch("/bookings/series/{series_id}/cancel", response_model=BookingSeriesCancelOut)
async def admin_cancel_booking_series(
    series_id: int,
    body: BookingSeriesCancelBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingSeriesCancelOut:
    try:
        return await cancel_booking_series(db, actor=user, series_id=series_id, body=body, as_admin=True)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/bookings", response_model=list[AdminBookingListItem])
async def admin_list_bookings(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date | None = None,
    date_to: date | None = None,
    room_id: int | None = Query(None, ge=1),
    status: str | None = None,
    user_q: str | None = Query(None, min_length=1, max_length=200),
    series_id: int | None = Query(None, ge=1),
    upcoming_only: bool = False,
    past_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[AdminBookingListItem]:
    try:
        return await list_bookings_for_admin(
            db,
            actor=user,
            date_from=date_from,
            date_to=date_to,
            room_id=room_id,
            status=status,
            user_q=user_q,
            series_id=series_id,
            upcoming_only=upcoming_only,
            past_only=past_only,
            skip=skip,
            limit=limit,
        )
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/bookings/{booking_id}", response_model=AdminBookingDetailOut)
async def admin_get_booking(
    booking_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBookingDetailOut:
    try:
        return await get_admin_booking_detail(db, actor=user, booking_id=booking_id)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.patch("/bookings/{booking_id}/cancel", response_model=BookingOut)
async def admin_cancel_booking(
    booking_id: int,
    body: BookingDecisionBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        booking = await db.get(Booking, booking_id)
        if booking is None:
            raise BookingError("not_found", "Booking not found", 404)
        if not await can_manage_room(db, actor=user, room_id=booking.room_id):
            raise BookingError("forbidden", "Not allowed", 403)
        b = await cancel_booking(
            db,
            user=user,
            booking_id=booking_id,
            reason=body.reason,
            as_admin=True,
        )
        return BookingOut.model_validate(b)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
async def patch_user_role(
    user_id: int,
    body: AdminRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> AdminUserOut:
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    u.role = body.role
    await db.flush()
    await db.refresh(u)
    return AdminUserOut.model_validate(u)


@router.post("/amenities", response_model=AmenityOut, status_code=status.HTTP_201_CREATED)
async def create_amenity(
    body: AmenityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> AmenityOut:
    a = Amenity(name=body.name.strip(), icon=body.icon)
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return AmenityOut.model_validate(a)


@router.patch("/amenities/{amenity_id}", response_model=AmenityOut)
async def update_amenity(
    amenity_id: int,
    body: AmenityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> AmenityOut:
    a = await db.get(Amenity, amenity_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Not found")
    if body.name is not None:
        a.name = body.name.strip()
    if body.icon is not None:
        a.icon = body.icon
    await db.flush()
    await db.refresh(a)
    return AmenityOut.model_validate(a)


@router.delete("/amenities/{amenity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_amenity(
    amenity_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> None:
    r = await db.execute(delete(Amenity).where(Amenity.id == amenity_id))
    if r.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/rooms", response_model=RoomAdminOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    body: RoomCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> RoomAdminOut:
    r = Room(
        name=body.name,
        description=body.description,
        location=body.location,
        capacity=body.capacity,
        booking_mode=body.booking_mode,
        availability_window_start=body.availability_window_start,
        availability_window_end=body.availability_window_end,
        is_active=body.is_active,
    )
    db.add(r)
    await db.flush()
    if body.amenity_ids is not None:
        await replace_room_amenities(db, r.id, body.amenity_ids)
    await db.refresh(r)
    return await room_admin_out(db, r)


@router.patch("/rooms/{room_id}", response_model=RoomAdminOut)
async def update_room(
    room_id: int,
    body: RoomUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> RoomAdminOut:
    r = await db.get(Room, room_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    amenity_ids = data.pop("amenity_ids", None)
    for k, v in data.items():
        setattr(r, k, v)
    await db.flush()
    if amenity_ids is not None:
        await replace_room_amenities(db, room_id, amenity_ids)
    await db.refresh(r)
    return await room_admin_out(db, r)


@router.get("/rooms/{room_id}/amenities", response_model=list[AmenityOut])
async def get_room_amenities(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> list[AmenityOut]:
    return await list_room_amenities_out(db, room_id)


@router.post("/rooms/{room_id}/amenities", response_model=list[AmenityOut])
async def post_room_amenity(
    room_id: int,
    body: RoomAmenityAttach,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> list[AmenityOut]:
    return await attach_room_amenity(db, room_id, body.amenity_id)


@router.delete("/rooms/{room_id}/amenities/{amenity_id}", response_model=list[AmenityOut])
async def delete_room_amenity(
    room_id: int,
    amenity_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> list[AmenityOut]:
    return await detach_room_amenity(db, room_id, amenity_id)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> None:
    r = await db.execute(delete(Room).where(Room.id == room_id))
    if r.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")


def _room_admin_mapping_out(row) -> RoomAdminMappingOut:
    return RoomAdminMappingOut(
        id=row.id,
        room_id=row.room_id,
        user_id=row.user_id,
        user_email=row.user.email,
        user_full_name=row.user.full_name,
        created_at=row.created_at,
    )


@router.get("/rooms/{room_id}/admins", response_model=list[RoomAdminMappingOut])
async def get_room_admins(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> list[RoomAdminMappingOut]:
    rows = await list_room_admins(db, room_id=room_id)
    return [_room_admin_mapping_out(x) for x in rows]


@router.post("/rooms/{room_id}/admins", response_model=RoomAdminMappingOut, status_code=status.HTTP_201_CREATED)
async def post_room_admin(
    room_id: int,
    body: RoomAdminAssignBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> RoomAdminMappingOut:
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        row = await add_room_admin(db, room_id=room_id, user_id=body.user_id)
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="User is already a room admin") from e
    return _room_admin_mapping_out(row)


@router.delete("/rooms/{room_id}/admins/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_admin(
    room_id: int,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> None:
    removed = await remove_room_admin(db, room_id=room_id, user_id=user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/rooms/{room_id}/images", response_model=RoomImageOut, status_code=status.HTTP_201_CREATED)
async def add_room_image(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
    file: UploadFile = File(...),
    sort_order: int = Form(0),
) -> RoomImageOut:
    r = await db.get(Room, room_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read()
    try:
        public_url, _path = await asyncio.to_thread(process_upload_bytes, content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    row = RoomImage(room_id=room_id, file_url=public_url, sort_order=sort_order)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return RoomImageOut.model_validate(row)


@router.delete("/rooms/{room_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_image(
    room_id: int,
    image_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> None:
    r = await db.execute(
        select(RoomImage).where(RoomImage.id == image_id, RoomImage.room_id == room_id)
    )
    row = r.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    file_url = row.file_url
    await db.execute(delete(RoomImage).where(RoomImage.id == image_id))
    await db.flush()
    await asyncio.to_thread(delete_local_room_image, file_url)


@router.post("/rooms/{room_id}/bookable-units", response_model=BookableUnitOut, status_code=status.HTTP_201_CREATED)
async def create_unit(
    room_id: int,
    body: BookableUnitCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> BookableUnitOut:
    r = await db.get(Room, room_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.parent_unit_id is not None:
        p = await db.get(BookableUnit, body.parent_unit_id)
        if p is None or p.room_id != room_id:
            raise HTTPException(status_code=400, detail="Invalid parent unit")
    u = BookableUnit(
        room_id=room_id,
        parent_unit_id=body.parent_unit_id,
        name=body.name,
        type=body.type,
        booking_mode=body.booking_mode,
        capacity=body.capacity,
        is_active=body.is_active,
    )
    db.add(u)
    await db.flush()
    await db.refresh(u)
    return BookableUnitOut.model_validate(u)


@router.patch("/bookable-units/{unit_id}", response_model=BookableUnitOut)
async def update_unit(
    unit_id: int,
    body: BookableUnitUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> BookableUnitOut:
    u = await db.get(BookableUnit, unit_id)
    if u is None:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if "parent_unit_id" in data and data["parent_unit_id"] is not None:
        p = await db.get(BookableUnit, data["parent_unit_id"])
        if p is None or p.room_id != u.room_id:
            raise HTTPException(status_code=400, detail="Invalid parent unit")
    for k, v in data.items():
        setattr(u, k, v)
    await db.flush()
    await db.refresh(u)
    return BookableUnitOut.model_validate(u)


@router.delete("/bookable-units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> None:
    r = await db.execute(delete(BookableUnit).where(BookableUnit.id == unit_id))
    if r.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/bookable-units/{unit_id}/conflicts", status_code=status.HTTP_201_CREATED)
async def add_conflict(
    unit_id: int,
    body: UnitConflictCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> dict:
    if unit_id == body.conflict_with_unit_id:
        raise HTTPException(status_code=400, detail="Cannot conflict with self")
    u1 = await db.get(BookableUnit, unit_id)
    u2 = await db.get(BookableUnit, body.conflict_with_unit_id)
    if u1 is None or u2 is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    row = UnitConflict(unit_id=unit_id, conflict_with_unit_id=body.conflict_with_unit_id)
    db.add(row)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Conflict pair already exists") from None
    return {"id": row.id, "unit_id": unit_id, "conflict_with_unit_id": body.conflict_with_unit_id}


@router.get("/bookable-units/{unit_id}/conflicts")
async def list_conflicts(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> list[dict]:
    r1 = await db.execute(
        select(UnitConflict).where(UnitConflict.unit_id == unit_id)
    )
    r2 = await db.execute(
        select(UnitConflict).where(UnitConflict.conflict_with_unit_id == unit_id)
    )
    out: dict[int, dict] = {}
    for row in r1.scalars().all():
        out[row.conflict_with_unit_id] = {
            "conflict_unit_id": row.conflict_with_unit_id,
            "relation": "outgoing",
            "row_id": row.id,
        }
    for row in r2.scalars().all():
        out[row.unit_id] = {
            "conflict_unit_id": row.unit_id,
            "relation": "incoming",
            "row_id": row.id,
        }
    return list(out.values())


@router.delete("/bookable-units/{unit_id}/conflicts/{conflict_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conflict(
    unit_id: int,
    conflict_unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> None:
    r = await db.execute(
        select(UnitConflict).where(
            (UnitConflict.unit_id == unit_id)
            & (UnitConflict.conflict_with_unit_id == conflict_unit_id)
        )
    )
    row = r.scalar_one_or_none()
    if row is None:
        r2 = await db.execute(
            select(UnitConflict).where(
                (UnitConflict.unit_id == conflict_unit_id)
                & (UnitConflict.conflict_with_unit_id == unit_id)
            )
        )
        row = r2.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    await db.execute(delete(UnitConflict).where(UnitConflict.id == row.id))


@router.get("/config/internal-domains", response_model=list[InternalDomainOut])
async def list_domains(db: Annotated[AsyncSession, Depends(get_db)], _: AdminUser) -> list[InternalDomainOut]:
    r = await db.execute(select(InternalDomain).order_by(InternalDomain.domain.asc()))
    return [InternalDomainOut.model_validate(x) for x in r.scalars().all()]


@router.post("/config/internal-domains", response_model=InternalDomainOut, status_code=status.HTTP_201_CREATED)
async def add_domain(
    body: InternalDomainCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> InternalDomainOut:
    d = body.domain.strip().lower().lstrip("@")
    dom = InternalDomain(domain=d, is_active=True)
    db.add(dom)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Domain already exists") from None
    await db.refresh(dom)
    return InternalDomainOut.model_validate(dom)


@router.delete("/config/internal-domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> None:
    r = await db.execute(delete(InternalDomain).where(InternalDomain.id == domain_id))
    if r.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/config/booking-policy", response_model=BookingPolicyOut)
async def get_policy(db: Annotated[AsyncSession, Depends(get_db)], _: AdminUser) -> BookingPolicyOut:
    r = await db.execute(select(BookingPolicy).order_by(BookingPolicy.id.asc()).limit(1))
    p = r.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Policy not configured")
    return BookingPolicyOut.model_validate(p)


@router.patch("/config/booking-policy", response_model=BookingPolicyOut)
async def patch_policy(
    body: BookingPolicyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminUser,
) -> BookingPolicyOut:
    r = await db.execute(select(BookingPolicy).order_by(BookingPolicy.id.asc()).limit(1))
    p = r.scalar_one_or_none()
    if p is None:
        p = BookingPolicy()
        db.add(p)
        await db.flush()
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    await db.flush()
    await db.refresh(p)
    return BookingPolicyOut.model_validate(p)


@router.get("/dashboard/summary", response_model=AdminDashboardSummary)
async def dashboard(db: Annotated[AsyncSession, Depends(get_db)], _: AdminUser) -> AdminDashboardSummary:
    today = datetime.now(timezone.utc).date()
    pending = await db.execute(
        select(func.count()).select_from(User).where(
            User.approval_status == ApprovalStatus.pending.value,
            User.email_verified.is_(True),
        )
    )
    rooms = await db.execute(select(func.count()).select_from(Room))
    bookings_today = await db.execute(
        select(func.count())
        .select_from(Booking)
        .where(Booking.booking_date == today, Booking.status == "confirmed")
    )
    users_total = await db.execute(select(func.count()).select_from(User))
    return AdminDashboardSummary(
        pending_approvals=int(pending.scalar_one()),
        rooms_total=int(rooms.scalar_one()),
        bookings_today=int(bookings_today.scalar_one()),
        users_total=int(users_total.scalar_one()),
    )
