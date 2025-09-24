"""merge database heads

Revision ID: 4011786aead6
Revises: 5a1c3b7a1d2f, c665e83f51d8
Create Date: 2025-09-12 18:34:54.275452

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4011786aead6"
down_revision: Union[str, Sequence[str], None] = ("5a1c3b7a1d2f", "c665e83f51d8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
