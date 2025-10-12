"""add use_ec flag to merge tasks

Revision ID: 2ab3f4c5d6e7
Revises: 1d273c8f4a90, bed10873d340
Create Date: 2025-09-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ab3f4c5d6e7"
down_revision: Union[str, Sequence[str], None] = ("1d273c8f4a90", "bed10873d340")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "merge_tasks",
        sa.Column(
            "use_ec",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("merge_tasks", "use_ec")
