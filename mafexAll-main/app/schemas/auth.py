from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(..., pattern="^(signup|login|email_change)$")


class LoginRequestOtpBody(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
