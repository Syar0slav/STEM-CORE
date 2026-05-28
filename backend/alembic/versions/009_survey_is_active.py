"""Поле is_active для опитувань (архів / активне).

Revision ID: 009_survey_is_active
Revises: 008_support_scope

"""

from typing import Sequence, Union

from alembic import op

revision: str = "009_survey_is_active"
down_revision: Union[str, None] = "008_support_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 001_initial уже може створити цю колонку з моделі Survey (is_active).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'surveys'
                  AND column_name = 'is_active'
            ) THEN
                ALTER TABLE surveys
                ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        UPDATE surveys SET is_active = FALSE
        WHERE closed_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE surveys DROP COLUMN IF EXISTS is_active")
