from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserEmailHistory(Base):
    __tablename__ = "user_email_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="email_history")
    changed_by: Mapped["User | None"] = relationship(foreign_keys=[changed_by_id])
