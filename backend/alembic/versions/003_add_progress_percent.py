"""Add progress_percent to scraping_jobs

Revision ID: 002
Revises: 001
Create Date: 2025-06-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scraping_jobs', 
        sa.Column('progress_percent', sa.Integer(), nullable=True, server_default='0')
    )


def downgrade():
    op.drop_column('scraping_jobs', 'progress_percent')