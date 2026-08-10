"""add part msl (moisture sensitivity level)

Revision ID: 0003_part_msl
Revises: 0002_attachment_source_url
Create Date: 2026-08-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_part_msl"
down_revision: Union[str, None] = "0002_attachment_source_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "parts",
        sa.Column("msl", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parts", "msl")
