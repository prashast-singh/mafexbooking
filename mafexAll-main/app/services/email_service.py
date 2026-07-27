import asyncio
import smtplib
from email.message import EmailMessage
from typing import TYPE_CHECKING, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.models.user import User

Attachment = tuple[str, bytes, str, str]  # filename, content, maintype, subtype


def _send_message(msg: EmailMessage) -> None:
    settings = get_settings()
    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(msg)


async def send_plain_email(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()

    def _send() -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg.set_content(body)
        _send_message(msg)

    await asyncio.to_thread(_send)


async def send_email_with_attachments(
    to_email: str,
    subject: str,
    body: str,
    attachments: Sequence[Attachment],
) -> None:
    settings = get_settings()

    def _send() -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg.set_content(body)
        for filename, content, maintype, subtype in attachments:
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
        _send_message(msg)

    await asyncio.to_thread(_send)


async def send_otp_email(to_email: str, otp: str, purpose: str) -> None:
    subject = "Your verification code"
    body = (
        f"Your verification code is: {otp}\n\n"
        f"Purpose: {purpose}\n"
        "If you did not request this, you can ignore this email."
    )
    await send_plain_email(to_email, subject, body)


async def notify_admins_pending_signup(db: AsyncSession, *, user: "User") -> None:
    """Best-effort: email all active global admins about a pending registration."""
    from sqlalchemy import select

    from app.core.enums import UserRole
    from app.models.user import User as UserModel
    from app.utils.frontend_urls import admin_approvals_url

    intent_line = ""
    intent = (getattr(user, "signup_intent", None) or "").strip()
    if intent:
        intent_line = f"Signup intent: {intent}\n"

    subject = "New user registration pending approval"
    body = (
        "A new user has verified their email and is awaiting approval.\n\n"
        f"Name: {user.full_name}\n"
        f"Email: {user.email}\n"
        f"{intent_line}"
        f"\nReview: {admin_approvals_url()}\n"
    )

    r = await db.execute(
        select(UserModel).where(
            UserModel.role == UserRole.admin.value,
            UserModel.is_active.is_(True),
            UserModel.email_verified.is_(True),
        )
    )
    admins = list(r.scalars().all())

    for admin in admins:
        try:
            await send_plain_email(admin.email, subject, body)
        except Exception:
            pass
