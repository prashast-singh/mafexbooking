from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.core.enums import OtpPurpose
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequestOtpBody,
    ResendOtpRequest,
    SignupRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.schemas.user import UserPublic
from app.models.user import User
from app.services.auth_service import (
    login_request_otp,
    login_verify_otp,
    resend_otp,
    signup_request,
    verify_signup_otp,
)
from app.services.room_admin_service import user_public_out

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_202_ACCEPTED)
async def signup(body: SignupRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    await signup_request(db, email=str(body.email), full_name=body.full_name)
    return {"detail": "OTP sent to email"}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOtpRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenResponse:
    token = await verify_signup_otp(db, email=str(body.email), otp=body.otp)
    return TokenResponse(access_token=token)


@router.post("/resend-otp", status_code=status.HTTP_202_ACCEPTED)
async def resend(body: ResendOtpRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    try:
        purpose = OtpPurpose(body.purpose)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "invalid", "message": str(e)}) from e
    await resend_otp(db, email=str(body.email), purpose=purpose)
    return {"detail": "OTP sent to email"}


@router.post("/login/request-otp", status_code=status.HTTP_202_ACCEPTED)
async def login_request(body: LoginRequestOtpBody, db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    await login_request_otp(db, email=str(body.email))
    return {"detail": "OTP sent to email"}


@router.post("/login/verify-otp", response_model=TokenResponse)
async def login_verify(body: VerifyOtpRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenResponse:
    token = await login_verify_otp(db, email=str(body.email), otp=body.otp)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
async def auth_me(
    user: Annotated[User | None, Depends(get_current_user_optional)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPublic:
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Not authenticated"})
    return await user_public_out(db, user)
