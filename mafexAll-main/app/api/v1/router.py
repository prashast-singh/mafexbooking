from fastapi import APIRouter

from app.api.v1 import admin, amenities, auth, availability, bookings, rooms, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(amenities.router)
api_router.include_router(rooms.router)
api_router.include_router(availability.router)
api_router.include_router(bookings.router)
api_router.include_router(admin.router)
