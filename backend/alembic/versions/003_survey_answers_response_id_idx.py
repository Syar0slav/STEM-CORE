"""Index survey_answers(response_id) for joins with survey_responses.

Revision ID: 003_sa_resp_ix (короткий id: alembic_version.version_num VARCHAR(32))
Revises: 002_resp_class_ix
Create Date: 2026-04-19

У `database/schema.sql` вже може бути `idx_survey_answers_response` — тоді дубль не створюємо.

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

revision: str = "003_sa_resp_ix"
down_revision: Union[str, None] = "002_resp_class_ix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_response_id_index(inspector, table: str) -> bool:
    for ix in inspector.get_indexes(table):
        cols = ix.get("column_names") or []
        if cols == ["response_id"]:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if _has_response_id_index(insp, "survey_answers"):
        return
    op.create_index(
        "ix_survey_answers_response_id",
        "survey_answers",
        ["response_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    names = {ix["name"] for ix in insp.get_indexes("survey_answers") if ix.get("name")}
    if "ix_survey_answers_response_id" in names:
        op.drop_index("ix_survey_answers_response_id", table_name="survey_answers")
