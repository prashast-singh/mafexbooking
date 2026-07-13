import os
import tempfile

# Configure test env before importing application modules that build the engine.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USERNAME", "")
os.environ.setdefault("SMTP_PASSWORD", "")
os.environ.setdefault("SMTP_FROM_EMAIL", "test@example.com")
os.environ.setdefault("OTP_EXPIRE_MINUTES", "10")
os.environ["STORAGE_ROOT"] = tempfile.mkdtemp()

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import clear_settings_cache
from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
def _clear_settings() -> None:
    clear_settings_cache()


@pytest.fixture(autouse=True)
async def prepare_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_headers() -> dict[str, str]:
    from app.core.enums import ApprovalStatus, UserRole, UserType
    from app.core.security import create_access_token
    from app.db.session import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        async with db.begin():
            u = User(
                email="admin@uni-marburg.de",
                full_name="Admin",
                role=UserRole.admin.value,
                user_type=UserType.internal.value,
                email_verified=True,
                approval_status=ApprovalStatus.approved.value,
                is_active=True,
            )
            db.add(u)
            await db.flush()
            uid = u.id
    token = create_access_token(str(uid))
    return {"Authorization": f"Bearer {token}"}
