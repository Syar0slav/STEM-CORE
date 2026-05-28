"""Додано staff_scope «support» (служба підтримки школи).

Revision ID: 008_support_scope
Revises: 007_class_school_name_uq
Create Date: 2026-05-11

"""

from typing import Sequence, Union

from alembic import op

revision: str = "008_support_scope"
down_revision: Union[str, None] = "007_class_school_name_uq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_staff_scope_check")
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT users_staff_scope_check
        CHECK (
            staff_scope IS NULL OR staff_scope IN (
                'parallel_a', 'parallel_b', 'school', 'support'
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_staff_scope_check")
    op.execute("UPDATE users SET staff_scope = NULL WHERE staff_scope = 'support'")
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT users_staff_scope_check
        CHECK (
            staff_scope IS NULL OR staff_scope IN ('parallel_a', 'parallel_b', 'school')
        )
        """
    )
