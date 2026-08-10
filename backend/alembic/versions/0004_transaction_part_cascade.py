"""cascade part deletion to inventory transactions

Revision ID: 0004_transaction_part_cascade
Revises: 0003_part_msl
Create Date: 2026-08-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_transaction_part_cascade"
down_revision: Union[str, None] = "0003_part_msl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "inventory_transactions_part_id_fkey",
        "inventory_transactions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "inventory_transactions_part_id_fkey",
        "inventory_transactions",
        "parts",
        ["part_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "inventory_transactions_part_id_fkey",
        "inventory_transactions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "inventory_transactions_part_id_fkey",
        "inventory_transactions",
        "parts",
        ["part_id"],
        ["id"],
        ondelete="RESTRICT",
    )
