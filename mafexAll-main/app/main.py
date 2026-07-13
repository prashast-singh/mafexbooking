from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.scripts.create_admin import create_admin
from app.services.auth_service import AuthError
from app.services.booking_service import BookingError

settings = get_settings()

app = FastAPI(
    title="Office Room Booking API",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(BookingError)
async def booking_error_handler(request: Request, exc: BookingError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.on_event("startup")
async def bootstrap_admin() -> None:
    if settings.BOOTSTRAP_ADMIN_EMAIL:
        await create_admin(settings.BOOTSTRAP_ADMIN_EMAIL, settings.BOOTSTRAP_ADMIN_NAME)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


_storage_root = Path(settings.STORAGE_ROOT).resolve()
_storage_root.mkdir(parents=True, exist_ok=True)
(settings.room_images_dir).mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(_storage_root)), name="storage")

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
