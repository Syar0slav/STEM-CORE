"""UNIQUE (school_id, name) для classes — потрібно для ON CONFLICT у сидах/імпорті.

Revision ID: 007_class_school_name_uq
Revises: 006_portal_links
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "007_class_school_name_uq"
down_revision: Union[str, None] = "006_portal_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 001_initial уже створює це з моделі Class (UniqueConstraint з тим самим ім’ям).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_classes_school_id_name'
            ) THEN
                ALTER TABLE classes
                ADD CONSTRAINT uq_classes_school_id_name UNIQUE (school_id, name);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE classes DROP CONSTRAINT IF EXISTS uq_classes_school_id_name"
    )
