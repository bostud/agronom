"""add area_ha column to field

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("field", sa.Column("area_ha", sa.Float(), nullable=False))
    op.create_index("ix_field_area_ha", "field", ["area_ha"])


def downgrade() -> None:
    op.drop_index("ix_field_area_ha", table_name="field")
    op.drop_column("field", "area_ha")
