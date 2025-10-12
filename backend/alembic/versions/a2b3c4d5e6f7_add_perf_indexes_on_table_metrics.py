"""
add performance indexes on table_metrics

Revision ID: a2b3c4d5e6f7
Revises: cae1488b11f0
Create Date: 2025-09-13 17:10:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "cae1488b11f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite indexes to speed up latest-metrics queries and scans
    op.create_index(
        "ix_table_metrics_cdt_scan_time",
        "table_metrics",
        ["cluster_id", "database_name", "table_name", "scan_time"],
        unique=False,
    )
    op.create_index(
        "ix_table_metrics_cdt_id",
        "table_metrics",
        ["cluster_id", "database_name", "table_name", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_table_metrics_cdt_id", table_name="table_metrics")
    op.drop_index("ix_table_metrics_cdt_scan_time", table_name="table_metrics")
