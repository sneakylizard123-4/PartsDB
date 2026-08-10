"""add attachment source_url

Revision ID: 0002_attachment_source_url
Revises: 0001_initial
Create Date: 2026-08-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_attachment_source_url"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attachments",
        sa.Column("source_url", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_attachments_source_url", "attachments", ["source_url"])


def downgrade() -> None:
    op.drop_index("ix_attachments_source_url", table_name="attachments")
    op.drop_column("attachments", "source_url")
