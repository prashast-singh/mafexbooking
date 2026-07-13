from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tag import Tag
from app.schemas.tag import TagOut

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
async def list_tags(db: Annotated[AsyncSession, Depends(get_db)]) -> list[TagOut]:
    r = await db.execute(select(Tag).order_by(Tag.name.asc()))
    rows = r.scalars().all()
    return [TagOut.model_validate(t) for t in rows]
