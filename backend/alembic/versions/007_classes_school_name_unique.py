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
    op.create_unique_constraint(
        "uq_classes_school_id_name",
        "classes",
        ["school_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_classes_school_id_name", "classes", type_="unique")
