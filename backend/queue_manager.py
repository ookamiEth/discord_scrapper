"""
Redis Queue management utilities
"""
from rq import Queue
from redis import Redis
from datetime import datetime
from typing import Optional
import logging

from config import settings

logger = logging.getLogger(__name__)

# Global Redis connection
redis_conn = None


def get_redis_connection():
    """Get or create Redis connection"""
    global redis_conn
    if redis_conn is None:
        redis_conn = Redis.from_url(settings.redis_url)
    return redis_conn


def get_redis_queue(queue_name: str = "default") -> Queue:
    """Get RQ queue instance"""
    return Queue(queue_name, connection=get_redis_connection())


def enqueue_scraping_job(
    queue: Queue,
    job_id: str,
    channel_id: str,  # Changed to string
    bot_token: str,
    job_type: str,
    export_format: str,
    date_range_start: Optional[datetime] = None,
    date_range_end: Optional[datetime] = None,
    message_limit: Optional[int] = None
):
    """Enqueue a scraping job"""
    from worker import scrape_channel  # Import here to avoid circular imports
    
    job = queue.enqueue(
        scrape_channel,
        # Positional arguments in order
        job_id,
        channel_id,
        bot_token,  # user_token for self-bot
        job_type,
        export_format,
        date_range_start,
        date_range_end,
        None,  # user_id (optional)
        message_limit,
        job_timeout='2h',  # 2 hour timeout
        result_ttl=86400,  # Keep result for 24 hours
        failure_ttl=86400  # Keep failure info for 24 hours
    )
    
    logger.info(f"Enqueued job {job_id} for channel {channel_id}")
    return job