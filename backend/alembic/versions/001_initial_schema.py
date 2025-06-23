"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bot_tokens table
    op.create_table('bot_tokens',
        sa.Column('token_id', sa.Integer(), nullable=False),
        sa.Column('token_name', sa.String(length=255), nullable=False),
        sa.Column('token_encrypted', sa.Text(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('token_id')
    )

    # Create scraping_jobs table
    op.create_table('scraping_jobs',
        sa.Column('job_id', sa.String(length=50), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('channel_name', sa.String(length=255), nullable=True),
        sa.Column('job_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('messages_scraped', sa.Integer(), nullable=True, default=0),
        sa.Column('export_path', sa.Text(), nullable=True),
        sa.Column('export_format', sa.String(length=10), nullable=True, default='json'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('date_range_start', sa.DateTime(), nullable=True),
        sa.Column('date_range_end', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('job_id')
    )

    # Create channel_sync_state table
    op.create_table('channel_sync_state',
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('channel_name', sa.String(length=255), nullable=True),
        sa.Column('last_message_id', sa.BigInteger(), nullable=True),
        sa.Column('last_message_timestamp', sa.DateTime(), nullable=True),
        sa.Column('first_message_id', sa.BigInteger(), nullable=True),
        sa.Column('first_message_timestamp', sa.DateTime(), nullable=True),
        sa.Column('total_messages', sa.Integer(), nullable=True, default=0),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('channel_id')
    )

    # Create messages table (optional - for storing message content)
    op.create_table('messages',
        sa.Column('message_id', sa.BigInteger(), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('author_id', sa.BigInteger(), nullable=False),
        sa.Column('author_name', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('message_id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_messages_channel_id'), 'messages', ['channel_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_channel_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_table('channel_sync_state')
    op.drop_table('scraping_jobs')
    op.drop_table('bot_tokens')