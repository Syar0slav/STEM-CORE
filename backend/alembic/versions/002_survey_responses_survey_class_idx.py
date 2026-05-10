"""Index survey_responses (survey_id, class_id) for analytics queries.

Revision ID: 002_resp_class_ix (короткий id: alembic_version.version_num VARCHAR(32))
Revises: 001_initial
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002_resp_class_ix"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_survey_responses_survey_id_class_id",
        "survey_responses",
        ["survey_id", "class_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_survey_responses_survey_id_class_id", table_name="survey_responses")
