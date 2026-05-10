"""Колонки email_verified та email_verification_token у users.

Revision ID: 004_email_ver
Revises: 003_sa_resp_ix
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "004_email_ver"
down_revision: Union[str, None] = "003_sa_resp_ix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ідемпотентно: 001_initial може вже створити ці колонки через create_all із поточних моделей;
    # без IF NOT EXISTS друга спроба add_column падає й ламає деплой.
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT true
        """
    )
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(128)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verification_token")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
