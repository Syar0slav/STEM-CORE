"""STEM-спеціалізація вчителя та таблиця teacher_class_assignments.

Revision ID: 010_teacher_assignments
Revises: 009_survey_is_active
"""

from typing import Sequence, Union

from alembic import op

revision: str = "010_teacher_assignments"
down_revision: Union[str, None] = "009_survey_is_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'users' AND column_name = 'stem_specialty'
            ) THEN
                ALTER TABLE users ADD COLUMN stem_specialty VARCHAR(1);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_stem_specialty_check
        """
    )
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT users_stem_specialty_check CHECK (
            stem_specialty IS NULL OR stem_specialty IN ('S', 'T', 'E', 'M')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_class_assignments (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, class_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO teacher_class_assignments (user_id, class_id)
        SELECT teacher_id, id FROM classes WHERE teacher_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS teacher_class_assignments")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_stem_specialty_check")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS stem_specialty")
