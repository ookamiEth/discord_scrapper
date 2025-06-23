"""Add self-bot support tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001_initial_schema'

def upgrade():
    # Create user_tokens table
    op.create_table('user_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False, unique=True),
        sa.Column('encrypted_token', sa.Text(), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), default=True),
        sa.Column('last_validation', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add anti-detection tracking
    op.create_table('scraping_sessions',
        sa.Column('session_id', sa.String(50), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('messages_scraped', sa.Integer(), default=0),
        sa.Column('breaks_taken', sa.Integer(), default=0),
        sa.Column('detection_score', sa.Float(), default=0.0),
        sa.PrimaryKeyConstraint('session_id')
    )
    
    # Update scraping_jobs table
    op.add_column('scraping_jobs', 
        sa.Column('scraping_method', sa.String(20), server_default='bot'))
    op.add_column('scraping_jobs',
        sa.Column('session_id', sa.String(50), nullable=True))

def downgrade():
    op.drop_column('scraping_jobs', 'session_id')
    op.drop_column('scraping_jobs', 'scraping_method')
    op.drop_table('scraping_sessions')
    op.drop_table('user_tokens')