from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.house_rules import HouseRules
from app.models.user import User


async def get_or_create_house_rules(db: AsyncSession) -> HouseRules:
    r = await db.execute(select(HouseRules).order_by(HouseRules.id.asc()).limit(1))
    row = r.scalar_one_or_none()
    if row is None:
        row = HouseRules(content="", version=1)
        db.add(row)
        await db.flush()
        await db.refresh(row)
    return row


def house_rules_published(rules: HouseRules) -> bool:
    return bool((rules.content or "").strip())


def user_must_accept_house_rules(user: User, rules: HouseRules) -> bool:
    if not house_rules_published(rules):
        return False
    return user.accepted_house_rules_version != rules.version


async def update_house_rules(db: AsyncSession, *, content: str) -> HouseRules:
    rules = await get_or_create_house_rules(db)
    new_content = content if content is not None else ""
    if new_content != (rules.content or ""):
        rules.content = new_content
        rules.version = int(rules.version or 1) + 1
    await db.flush()
    await db.refresh(rules)
    return rules


async def accept_house_rules(db: AsyncSession, *, user: User) -> HouseRules:
    rules = await get_or_create_house_rules(db)
    if not house_rules_published(rules):
        return rules
    user.accepted_house_rules_version = rules.version
    await db.flush()
    return rules
