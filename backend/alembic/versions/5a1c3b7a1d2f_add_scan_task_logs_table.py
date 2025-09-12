"""
add scan_task_logs table

Revision ID: 5a1c3b7a1d2f
Revises: ac4d3d3c8bd0
Create Date: 2025-09-12 03:15:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a1c3b7a1d2f'
down_revision = 'ac4d3d3c8bd0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scan_task_logs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('scan_task_id', sa.Integer(), sa.ForeignKey('scan_tasks.id'), nullable=False, index=True),
        sa.Column('level', sa.String(length=20), nullable=False, index=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('database_name', sa.String(length=255), nullable=True),
        sa.Column('table_name', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_table('scan_task_logs')

