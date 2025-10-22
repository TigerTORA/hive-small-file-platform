"""Add Kerberos configuration fields to clusters

Revision ID: c7b1f0d3ad4a
Revises: 0145c7e28cc9
Create Date: 2025-10-13 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7b1f0d3ad4a"
down_revision: Union[str, Sequence[str], None] = "0145c7e28cc9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clusters",
        sa.Column("kerberos_principal", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "clusters",
        sa.Column("kerberos_keytab_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "clusters", sa.Column("kerberos_realm", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "clusters",
        sa.Column("kerberos_ticket_cache", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clusters", "kerberos_ticket_cache")
    op.drop_column("clusters", "kerberos_realm")
    op.drop_column("clusters", "kerberos_keytab_path")
    op.drop_column("clusters", "kerberos_principal")
