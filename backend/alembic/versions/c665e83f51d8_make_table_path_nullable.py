"""make table_path nullable

Revision ID: c665e83f51d8
Revises: f56f0a5dab2f
Create Date: 2025-09-11 10:32:14.846357

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c665e83f51d8"
down_revision: Union[str, Sequence[str], None] = "f56f0a5dab2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support ALTER COLUMN, so we need to rebuild the table

    # Create new table with nullable table_path
    op.create_table(
        "table_metrics_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.String(length=100), nullable=False),
        sa.Column("table_name", sa.String(length=200), nullable=False),
        sa.Column("table_path", sa.String(length=500), nullable=True),  # Now nullable
        sa.Column("table_type", sa.String(length=50), nullable=True),
        sa.Column("storage_format", sa.String(length=50), nullable=True),
        sa.Column("input_format", sa.String(length=200), nullable=True),
        sa.Column("output_format", sa.String(length=200), nullable=True),
        sa.Column("serde_lib", sa.String(length=200), nullable=True),
        sa.Column("table_owner", sa.String(length=100), nullable=True),
        sa.Column("table_create_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("partition_columns", sa.String(length=500), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=True),
        sa.Column("small_files", sa.Integer(), nullable=True),
        sa.Column("total_size", sa.BigInteger(), nullable=True),
        sa.Column("avg_file_size", sa.Float(), nullable=True),
        sa.Column("is_partitioned", sa.Integer(), nullable=True),
        sa.Column("partition_count", sa.Integer(), nullable=True),
        sa.Column("scan_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_duration", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["clusters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Copy data from old table to new table
    op.execute(
        """
        INSERT INTO table_metrics_new 
        SELECT id, cluster_id, database_name, table_name, table_path, 
               table_type, storage_format, input_format, output_format, serde_lib,
               table_owner, table_create_time, partition_columns,
               total_files, small_files, total_size, avg_file_size,
               is_partitioned, partition_count, scan_time, scan_duration
        FROM table_metrics
    """
    )

    # Drop old table and rename new table
    op.drop_table("table_metrics")
    op.rename_table("table_metrics_new", "table_metrics")

    # Recreate indexes
    op.create_index(
        op.f("ix_table_metrics_cluster_id"),
        "table_metrics",
        ["cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_table_metrics_database_name"),
        "table_metrics",
        ["database_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_table_metrics_table_name"),
        "table_metrics",
        ["table_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_table_metrics_scan_time"), "table_metrics", ["scan_time"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # This would recreate the table with NOT NULL constraint
    # For simplicity, we'll just pass since this is a development database
    pass
