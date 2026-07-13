from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ApprovedUser, CurrentUser
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.booking import Booking
from app.schemas.booking import BookingCancelBody, BookingCreate, BookingOut, BookingUpdate
from app.schemas.booking_series import (
    BookingSeriesCancelBody,
    BookingSeriesCancelOut,
    BookingSeriesCreate,
    BookingSeriesOut,
    BookingSeriesPreviewOut,
    BookingSeriesRescheduleBody,
    BookingSeriesRescheduleOut,
)
from app.services.booking_service import BookingError, cancel_booking, create_booking, update_booking
from app.services.booking_series_service import (
    cancel_booking_series,
    create_booking_series,
    preview_booking_series,
    reschedule_booking_series,
)
from app.services.tag_visibility_service import room_visible_to_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/series/preview", response_model=BookingSeriesPreviewOut)
async def preview_series(
    body: BookingSeriesCreate,
    user: ApprovedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingSeriesPreviewOut:
    if not await room_visible_to_user(db, room_id=body.room_id, user=user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    try:
        return await preview_booking_series(db, user=user, body=body)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/series", response_model=BookingSeriesOut, status_code=status.HTTP_201_CREATED)
async def create_series(
    body: BookingSeriesCreate,
    user: ApprovedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingSeriesOut:
    if not await room_visible_to_user(db, room_id=body.room_id, user=user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    try:
        return await create_booking_series(db, user=user, body=body)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.patch("/series/{series_id}/cancel", response_model=BookingSeriesCancelOut)
async def cancel_series(
    series_id: int,
    body: BookingSeriesCancelBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingSeriesCancelOut:
    try:
        return await cancel_booking_series(db, actor=user, series_id=series_id, body=body)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.patch("/series/{series_id}/reschedule", response_model=BookingSeriesRescheduleOut)
async def reschedule_series(
    series_id: int,
    body: BookingSeriesRescheduleBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingSeriesRescheduleOut:
    try:
        return await reschedule_booking_series(
            db,
            actor=user,
            series_id=series_id,
            body=body,
            as_admin=(user.role == UserRole.admin.value),
        )
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: BookingCreate,
    user: ApprovedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingOut:
    if not await room_visible_to_user(db, room_id=body.room_id, user=user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    try:
        b = await create_booking(
            db,
            user=user,
            room_id=body.room_id,
            unit_id=body.unit_id,
            booking_date=body.booking_date,
            start_time=body.start_time,
            end_time=body.end_time,
            purpose=body.purpose,
        )
        return BookingOut.model_validate(b)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingOut:
    r = await db.execute(select(Booking).where(Booking.id == booking_id))
    b = r.scalar_one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Not found")
    if b.user_id != user.id and user.role != UserRole.admin.value:
        raise HTTPException(status_code=403, detail="Forbidden")
    return BookingOut.model_validate(b)


@router.patch("/{booking_id}", response_model=BookingOut)
async def update(
    booking_id: int,
    body: BookingUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingOut:
    try:
        b = await update_booking(
            db,
            actor=user,
            booking_id=booking_id,
            unit_id=body.unit_id,
            booking_date=body.booking_date,
            start_time=body.start_time,
            end_time=body.end_time,
            purpose=body.purpose,
            as_admin=(user.role == UserRole.admin.value),
        )
        return BookingOut.model_validate(b)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.patch("/{booking_id}/cancel", response_model=BookingOut)
async def cancel(
    booking_id: int,
    body: BookingCancelBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookingOut:
    try:
        b = await cancel_booking(
            db,
            user=user,
            booking_id=booking_id,
            reason=body.reason,
            as_admin=(user.role == UserRole.admin.value),
        )
        return BookingOut.model_validate(b)
    except BookingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
