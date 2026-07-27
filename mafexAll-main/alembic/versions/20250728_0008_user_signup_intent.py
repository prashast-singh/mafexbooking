"""User signup_intent for registration questionnaire.

Revision ID: 20250728_0008
Revises: 20250713_0007
Create Date: 2026-07-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250728_0008"
down_revision: Union[str, None] = "20250713_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("signup_intent", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "signup_intent")
