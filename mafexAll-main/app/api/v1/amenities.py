from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.amenity import Amenity
from app.schemas.amenity import AmenityOut

router = APIRouter(prefix="/amenities", tags=["amenities"])


@router.get("", response_model=list[AmenityOut])
async def list_amenities(db: Annotated[AsyncSession, Depends(get_db)]) -> list[AmenityOut]:
    r = await db.execute(select(Amenity).order_by(Amenity.name.asc()))
    rows = r.scalars().all()
    return [AmenityOut.model_validate(a) for a in rows]
