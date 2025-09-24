"""add merge target format and compression fields

Revision ID: 1d273c8f4a90
Revises: f56f0a5dab2f
Create Date: 2025-09-23 10:15:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d273c8f4a90"
down_revision: Union[str, Sequence[str], None] = "f56f0a5dab2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding target format fields to merge tasks."""
    op.add_column(
        "merge_tasks",
        sa.Column("target_storage_format", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "merge_tasks",
        sa.Column("target_compression", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema by removing target format fields."""
    op.drop_column("merge_tasks", "target_compression")
    op.drop_column("merge_tasks", "target_storage_format")
