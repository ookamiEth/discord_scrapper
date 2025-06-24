"""
Database configuration and models
"""
from sqlalchemy import create_engine, Column, BigInteger, String, DateTime, Integer, Boolean, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from datetime import datetime
from typing import Generator

from config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,  # Disable pooling for simplicity
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


# Models
class BotToken(Base):
    """Bot tokens for different servers"""
    __tablename__ = "bot_tokens"
    
    token_id = Column(Integer, primary_key=True)
    token_name = Column(String(255), nullable=False)
    token_encrypted = Column(Text, nullable=False)  # We'll add encryption later
    server_id = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScrapingJob(Base):
    """Track scraping jobs"""
    __tablename__ = "scraping_jobs"
    
    job_id = Column(String(50), primary_key=True)  # RQ job ID
    server_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    channel_name = Column(String(255))
    job_type = Column(String(20), nullable=False)  # 'full', 'incremental', 'date_range'
    status = Column(String(20), nullable=False)  # 'pending', 'running', 'completed', 'failed'
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    messages_scraped = Column(Integer, default=0)
    export_path = Column(Text)
    export_format = Column(String(10), default='json')
    error_message = Column(Text)
    progress_percent = Column(Integer, default=0)  # Real progress tracking
    
    # Self-bot specific fields
    scraping_method = Column(String(20), default='bot')
    session_id = Column(String(50), nullable=True)
    
    # Date range for date-based scraping
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)


class ChannelSyncState(Base):
    """Track channel sync state for incremental updates"""
    __tablename__ = "channel_sync_state"
    
    channel_id = Column(BigInteger, primary_key=True)
    server_id = Column(BigInteger, nullable=False)
    channel_name = Column(String(255))
    last_message_id = Column(BigInteger)
    last_message_timestamp = Column(DateTime)
    first_message_id = Column(BigInteger)
    first_message_timestamp = Column(DateTime)
    total_messages = Column(Integer, default=0)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    """Optional: Store message metadata or content"""
    __tablename__ = "messages"
    
    message_id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    server_id = Column(BigInteger, nullable=False)
    author_id = Column(BigInteger, nullable=False)
    author_name = Column(String(255))
    content = Column(Text)  # Only stored if store_message_content is True
    created_at = Column(DateTime, nullable=False, index=True)
    
    # Indexes are created automatically for indexed columns


# Database utilities
def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


class ScrapingSession(Base):
    """Track scraping sessions for anti-detection"""
    __tablename__ = "scraping_sessions"
    
    session_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    messages_scraped = Column(Integer, default=0)
    breaks_taken = Column(Integer, default=0)
    detection_score = Column(Float, default=0.0)