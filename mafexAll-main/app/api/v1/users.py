from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.booking import Booking
from app.schemas.booking import BookingOut, BookingOutWithRoom
from app.schemas.booking_series import BookingSeriesOut
from app.schemas.user import (
    EmailChangeRequestBody,
    EmailChangeVerifyBody,
    UserEmailHistoryOut,
    UserMeUpdate,
    ManagedRoomBrief,
    UserPublic,
)
from app.services.auth_service import AuthError
from app.services.booking_series_service import list_user_booking_series
from app.services.room_admin_service import list_managed_rooms, user_public_out
from app.services.user_profile_service import (
    list_user_email_history,
    request_email_change_otp,
    verify_email_change_otp,
)

from app.utils.pagination import PaginatedResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_me(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> UserPublic:
    return await user_public_out(db, user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: UserMeUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPublic:
    if body.full_name is not None:
        user.full_name = body.full_name
    await db.flush()
    await db.refresh(user)
    return await user_public_out(db, user)


@router.get("/me/managed-rooms", response_model=list[ManagedRoomBrief])
async def my_managed_rooms(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> list[ManagedRoomBrief]:
    return await list_managed_rooms(db, user_id=user.id)


@router.get("/me/bookings", response_model=PaginatedResponse[BookingOutWithRoom])
async def my_bookings(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[BookingOutWithRoom]:
    count_stmt = select(func.count()).select_from(Booking).where(Booking.user_id == user.id)
    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = (
        select(Booking)
        .where(Booking.user_id == user.id)
        .options(selectinload(Booking.room))
        .order_by(Booking.start_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return PaginatedResponse(
        items=[
            BookingOutWithRoom(
                **BookingOut.model_validate(b).model_dump(),
                room_name=b.room.name if b.room is not None else f"Room #{b.room_id}",
                room_location=b.room.location if b.room is not None else None,
            )
            for b in rows
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/me/booking-series", response_model=list[BookingSeriesOut])
async def my_booking_series(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BookingSeriesOut]:
    return await list_user_booking_series(db, user_id=user.id)


@router.post("/me/email/request-otp", status_code=status.HTTP_204_NO_CONTENT)
async def request_email_change(
    body: EmailChangeRequestBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        await request_email_change_otp(db, user=user, new_email=str(body.new_email))
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/me/email/verify-otp", response_model=UserPublic)
async def verify_email_change(
    body: EmailChangeVerifyBody,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPublic:
    try:
        updated = await verify_email_change_otp(
            db,
            user=user,
            new_email=str(body.new_email),
            otp=body.otp,
        )
        return await user_public_out(db, updated)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/me/email-history", response_model=list[UserEmailHistoryOut])
async def my_email_history(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserEmailHistoryOut]:
    rows = await list_user_email_history(db, user_id=user.id)
    return [UserEmailHistoryOut.model_validate(r) for r in rows]
