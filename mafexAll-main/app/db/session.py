from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()

if settings.DATABASE_URL.startswith("postgresql+psycopg://"):
    async_database_url = settings.DATABASE_URL.replace(
        "postgresql+psycopg://", "postgresql+psycopg_async://", 1
    )
else:
    async_database_url = settings.DATABASE_URL

_engine_kwargs: dict = {"echo": False}
if async_database_url.startswith("sqlite"):
    _engine_kwargs["poolclass"] = StaticPool
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    async_database_url,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
