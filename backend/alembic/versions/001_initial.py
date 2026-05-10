"""Initial schema from SQLAlchemy models.

Revision ID: 001_initial
Revises:
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import models  # noqa: F401 — ensure model modules are loaded

    from models import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import models  # noqa: F401

    from models import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
