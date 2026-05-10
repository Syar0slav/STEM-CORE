"""Посилання на уроки (паралелі/школа) та прапор Moodle для класу.

Revision ID: 006_portal_links
Revises: 005_staff_scope
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op

revision: str = "006_portal_links"
down_revision: Union[str, None] = "005_staff_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for stmt in (
        "ALTER TABLE schools ADD COLUMN IF NOT EXISTS lessons_url_parallel_a TEXT",
        "ALTER TABLE schools ADD COLUMN IF NOT EXISTS lessons_url_parallel_b TEXT",
        "ALTER TABLE schools ADD COLUMN IF NOT EXISTS lessons_url_school TEXT",
        "ALTER TABLE classes ADD COLUMN IF NOT EXISTS moodle_survey_enabled BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE classes ADD COLUMN IF NOT EXISTS moodle_survey_url TEXT",
    ):
        op.execute(stmt)


def downgrade() -> None:
    op.execute("ALTER TABLE classes DROP COLUMN IF EXISTS moodle_survey_url")
    op.execute("ALTER TABLE classes DROP COLUMN IF EXISTS moodle_survey_enabled")
    op.execute("ALTER TABLE schools DROP COLUMN IF EXISTS lessons_url_school")
    op.execute("ALTER TABLE schools DROP COLUMN IF EXISTS lessons_url_parallel_b")
    op.execute("ALTER TABLE schools DROP COLUMN IF EXISTS lessons_url_parallel_a")
