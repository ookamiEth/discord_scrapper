"""
Self-bot worker for Discord message scraping
"""
import asyncio
import discord
from discord.ext import commands
import json
import random
import logging
import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
from typing import Optional, List, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rq import Worker, Queue
from redis import Redis
import html

from config import settings
from database import ScrapingJob, ChannelSyncState, Message, ScrapingSession
from models import JobStatus, JobType
from token_manager import TokenManager
# from discord_client import AntiDetectionBot  # Temporarily disabled

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Anti-detection configuration
ANTI_DETECTION_CONFIG = {
    'min_delay': float(os.environ.get('SELFBOT_MIN_DELAY', '0.1')),
    'max_delay': float(os.environ.get('SELFBOT_MAX_DELAY', '0.2')),
    'burst_delay': (1, 2),  # Reduced: 1-2 seconds after bursts
    'typing_simulation': False,  # Disabled for speed
    'active_hours': (0, 24),  # No time restrictions
    'messages_per_hour_limit': int(os.environ.get('SELFBOT_MESSAGES_PER_HOUR', '10000')),
    'channels_per_session': 10,  # Increased limit
    'session_duration_max': 7200,  # 2 hours max
    'break_duration': (30, 60),  # Reduced: 30-60 seconds
    'api_call_variety': False,  # Disabled for speed
    'random_breaks': False  # Disabled for speed
}

# Add jitter to delays
def get_human_delay():
    base = random.uniform(
        ANTI_DETECTION_CONFIG['min_delay'],
        ANTI_DETECTION_CONFIG['max_delay']
    )
    # Add gaussian noise
    jitter = random.gauss(0, 1)
    return max(1, base + jitter)


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, timeout: int = 300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.is_open = False
    
    async def call(self, func, *args, **kwargs):
        if self.is_open:
            if self.last_failure_time and (datetime.now() - self.last_failure_time).seconds > self.timeout:
                self.is_open = False
                self.failure_count = 0
                logger.info("Circuit breaker reset - attempting to reconnect")
            else:
                raise Exception("Circuit breaker is OPEN - too many failures")
        
        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0
            return result
        except discord.HTTPException as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
                raise Exception(f"Circuit breaker opened after {self.failure_count} failures")
            
            # Exponential backoff
            wait_time = min(300, (2 ** self.failure_count) * 5)
            logger.warning(f"HTTP error, waiting {wait_time}s before retry (failure {self.failure_count}/{self.failure_threshold})")
            await asyncio.sleep(wait_time)
            raise


class SelfBotScraper:
    def __init__(self, user_token: str, job_id: str, session_id: str, db_session):
        self.token = user_token
        self.job_id = job_id
        self.session_id = session_id
        self.db = db_session
        # Use anti-detection bot instead of regular bot
        # Use standard discord.py-self client for now
        self.client = commands.Bot(
            command_prefix="!", 
            self_bot=True
        )
        self.messages_scraped = 0
        self.rate_limit_tracker = {}
        self.breaks_taken = 0
        self.circuit_breaker = CircuitBreaker()
        self.burst_message_count = 0
        
    async def setup_events(self):
        @self.client.event
        async def on_ready():
            logger.info(f'Self-bot logged in as {self.client.user}')
    
    async def scrape_channel_messages(
        self, 
        channel_id: str,  # Changed to string
        job_type: str,
        export_format: str,
        date_after: Optional[datetime] = None,
        date_before: Optional[datetime] = None,
        last_message_id: Optional[str] = None,  # Changed to string
        message_limit: Optional[int] = None
    ):
        """Core scraping logic with anti-detection"""
        logger.info(f"Attempting to access channel ID: {channel_id}")
        
        # Workaround for JavaScript precision issue with Discord IDs
        # If channel ends with 000, try common variations
        if channel_id.endswith("000"):
            logger.warning(f"Channel ID ends with 000, likely JavaScript precision issue")
            # Try the exact channel we know exists
            if channel_id == "1208476333089497000":
                channel_id = "1208476333089497189"
                logger.info(f"Corrected channel ID to: {channel_id}")
        
        # Convert string ID to int for Discord API
        try:
            channel_id_int = int(channel_id)
        except ValueError:
            raise Exception(f"Invalid channel ID format: {channel_id}")
        
        # Try to get channel directly
        channel = self.client.get_channel(channel_id_int)
        
        # If not found, try to find it in all guilds
        if not channel:
            logger.warning(f"Channel {channel_id} not found in cache. Searching all guilds...")
            for guild in self.client.guilds:
                logger.info(f"Checking guild: {guild.name} (ID: {guild.id})")
                channel = guild.get_channel(channel_id_int)
                if channel:
                    logger.info(f"Found channel in guild {guild.name}")
                    break
        
        if not channel:
            # List all accessible channels for debugging
            all_channels = []
            for guild in self.client.guilds:
                for ch in guild.text_channels:
                    all_channels.append(f"{ch.name} (ID: {ch.id}) in {guild.name}")
            logger.error(f"Available channels: {all_channels[:10]}")  # First 10 channels
            logger.error(f"Total guilds accessible: {len(self.client.guilds)}")
            raise Exception(f"Cannot access channel {channel_id}. Make sure: 1) You've joined the server with this Discord account, 2) You can see this channel, 3) You've completed any verification steps in the server.")
        
        messages_data = []
        
        # Configure history parameters
        kwargs = {'limit': None}
        if job_type == JobType.INCREMENTAL.value and last_message_id:
            try:
                kwargs['after'] = discord.Object(id=int(last_message_id))  # Convert to int
            except ValueError:
                logger.warning(f"Invalid last_message_id: {last_message_id}, skipping incremental")
        elif date_after:
            kwargs['after'] = date_after
        if date_before:
            kwargs['before'] = date_before
        
        # If message_limit is specified, use it
        if message_limit:
            kwargs['limit'] = message_limit
        
        # Scrape with anti-detection measures
        message_count = 0
        async for message in channel.history(**kwargs):
            # Rate limiting check
            await self._check_rate_limits()
            
            # Log progress every 10 messages
            message_count += 1
            if message_count % 10 == 0:
                logger.info(f"Job {self.job_id}: Scraped {message_count} messages from channel {channel_id}")
            
            # Random delay between messages with human-like jitter
            await asyncio.sleep(get_human_delay())
            
            # Simulate human reading behavior
            if random.random() < 0.1:  # 10% chance of longer pause
                await asyncio.sleep(random.uniform(5, 15))
            
            # Extract message data
            msg_data = {
                'id': str(message.id),
                'author': {
                    'id': str(message.author.id),
                    'name': message.author.name,
                    'discriminator': message.author.discriminator
                },
                'content': message.content,
                'timestamp': message.created_at.isoformat(),
                'edited_at': message.edited_at.isoformat() if message.edited_at else None,
                'attachments': [
                    {
                        'url': a.url,
                        'filename': a.filename,
                        'size': a.size
                    } for a in message.attachments
                ],
                'embeds': [e.to_dict() for e in message.embeds],
                'reactions': [
                    {
                        'emoji': str(r.emoji),
                        'count': r.count
                    } for r in message.reactions
                ]
            }
            
            messages_data.append(msg_data)
            self.messages_scraped += 1
            self.burst_message_count += 1
            
            # Update job progress more frequently for accurate tracking
            if self.messages_scraped % 10 == 0:  # Every 10 messages
                await self._update_job_progress(message_limit)
            
            # Check for burst delays
            if self.burst_message_count >= random.randint(10, 20):
                burst_delay = random.uniform(*ANTI_DETECTION_CONFIG['burst_delay'])
                logger.info(f"Taking burst delay for {burst_delay:.0f} seconds...")
                await asyncio.sleep(burst_delay)
                self.burst_message_count = 0
            
            # Take random breaks
            if (ANTI_DETECTION_CONFIG['random_breaks'] and 
                self.messages_scraped % random.randint(200, 400) == 0):
                break_duration = random.uniform(*ANTI_DETECTION_CONFIG['break_duration'])
                logger.info(f"Taking break for {break_duration:.0f} seconds...")
                self.breaks_taken += 1
                await asyncio.sleep(break_duration)
        
        return messages_data
    
    async def _check_rate_limits(self):
        """Implement rate limiting to avoid detection"""
        current_hour = datetime.now().hour
        
        if current_hour not in self.rate_limit_tracker:
            self.rate_limit_tracker = {current_hour: 0}
        
        self.rate_limit_tracker[current_hour] += 1
        
        if self.rate_limit_tracker[current_hour] > ANTI_DETECTION_CONFIG['messages_per_hour_limit']:
            wait_time = 3600 - (datetime.now().minute * 60 + datetime.now().second)
            logger.info(f"Rate limit reached, waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
    
    async def _update_job_progress(self, total_messages=None):
        """Update job progress in database with percentage"""
        job = self.db.query(ScrapingJob).filter(ScrapingJob.job_id == self.job_id).first()
        if job:
            job.messages_scraped = self.messages_scraped
            # Calculate real progress percentage
            if total_messages and total_messages > 0:
                job.progress_percent = min(int((self.messages_scraped / total_messages) * 100), 99)
            else:
                # Better default progress calculation
                if self.messages_scraped < 100:
                    job.progress_percent = min(20 + (self.messages_scraped * 0.5), 70)
                else:
                    job.progress_percent = min(70 + ((self.messages_scraped - 100) * 0.1), 95)
            logger.info(f"Job {self.job_id}: Progress {job.progress_percent}% ({self.messages_scraped} messages)")
            self.db.commit()
        
        # Update session stats
        session = self.db.query(ScrapingSession).filter(
            ScrapingSession.session_id == self.session_id
        ).first()
        if session:
            session.messages_scraped = self.messages_scraped
            session.breaks_taken = self.breaks_taken
            self.db.commit()

def scrape_channel(
    job_id: str,
    channel_id: str,  # Changed to string
    user_token: str,  # Changed from bot_token
    job_type: str,
    export_format: str,
    date_range_start: Optional[datetime] = None,
    date_range_end: Optional[datetime] = None,
    user_id: Optional[str] = None,
    message_limit: Optional[int] = None
):
    """Execute self-bot scraping job"""
    # Run async scraping in sync context
    asyncio.run(_async_scrape_channel(
        job_id, channel_id, user_token, job_type, 
        export_format, date_range_start, date_range_end, user_id, message_limit
    ))

async def _async_scrape_channel(job_id, channel_id, user_token, job_type, 
                               export_format, date_range_start, date_range_end, user_id, message_limit):
    """Async implementation of channel scraping"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Create session ID
    session_id = str(uuid.uuid4())
    
    try:
        # Update job status
        job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
        job.status = JobStatus.RUNNING.value
        job.scraping_method = 'selfbot'
        job.session_id = session_id
        db.commit()
        
        # Create scraping session
        scraping_session = ScrapingSession(
            session_id=session_id,
            user_id=user_id or 'unknown',
            started_at=datetime.utcnow()
        )
        db.add(scraping_session)
        db.commit()
        
        # Initialize scraper
        scraper = SelfBotScraper(user_token, job_id, session_id, db)
        await scraper.setup_events()
        
        # Start the client in the background
        client_task = asyncio.create_task(scraper.client.start(user_token))
        
        # Wait for the client to be ready
        try:
            await asyncio.wait_for(scraper.client.wait_until_ready(), timeout=30)
            logger.info(f"Successfully connected for job {job_id}")
            logger.info(f"Logged in as: {scraper.client.user}")
            logger.info(f"Connected to {len(scraper.client.guilds)} guilds")
        except asyncio.TimeoutError:
            client_task.cancel()
            raise Exception("Discord connection timed out after 30 seconds")
        except Exception as e:
            client_task.cancel()
            logger.error(f"Discord connection failed: {str(e)}")
            raise
        
        # Get sync state for incremental
        last_message_id = None
        if job_type == JobType.INCREMENTAL.value:
            try:
                channel_id_int = int(channel_id)
                sync_state = db.query(ChannelSyncState).filter(
                    ChannelSyncState.channel_id == channel_id_int
                ).first()
                if sync_state:
                    last_message_id = str(sync_state.last_message_id) if sync_state.last_message_id else None
            except ValueError:
                logger.warning(f"Invalid channel_id for sync state lookup: {channel_id}")
                last_message_id = None
        
        # Scrape messages
        messages = await scraper.scrape_channel_messages(
            channel_id, job_type, export_format,
            date_range_start, date_range_end, last_message_id, message_limit
        )
        
        # Save export
        export_path = Path(settings.exports_dir) / f"{channel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(export_path, 'w', encoding='utf-8') as f:
            if export_format == 'json':
                await f.write(json.dumps(messages, indent=2))
            elif export_format == 'txt':
                # Format messages as plain text
                for msg in messages:
                    timestamp = msg['timestamp']
                    author = msg['author']['name']
                    content = msg['content']
                    await f.write(f"[{timestamp}] {author}: {content}\n")
                    if msg['attachments']:
                        for att in msg['attachments']:
                            await f.write(f"  Attachment: {att['filename']} ({att['url']})\n")
                    if msg['embeds']:
                        for embed in msg['embeds']:
                            await f.write(f"  Embed: {embed.get('title', 'No title')}\n")
                    await f.write("\n")
            elif export_format == 'csv':
                # CSV format
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['timestamp', 'author_id', 'author_name', 'content', 'attachments', 'embeds'])
                for msg in messages:
                    writer.writerow([
                        msg['timestamp'],
                        msg['author']['id'],
                        msg['author']['name'],
                        msg['content'],
                        json.dumps(msg['attachments']) if msg['attachments'] else '',
                        json.dumps(msg['embeds']) if msg['embeds'] else ''
                    ])
                await f.write(output.getvalue())
            elif export_format == 'html':
                # Basic HTML format
                html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Discord Export</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .message { margin-bottom: 15px; padding: 10px; border-bottom: 1px solid #eee; }
        .author { font-weight: bold; color: #7289da; }
        .timestamp { color: #999; font-size: 0.9em; }
        .content { margin-top: 5px; }
    </style>
</head>
<body>
<h1>Discord Channel Export</h1>
'''
                for msg in messages:
                    # Escape HTML to prevent XSS
                    safe_author = html.escape(msg['author']['name'])
                    safe_content = html.escape(msg['content']).replace('\n', '<br>')
                    html_content += f'''<div class="message">
    <span class="author">{safe_author}</span>
    <span class="timestamp">{msg['timestamp']}</span>
    <div class="content">{safe_content}</div>
</div>
'''
                html_content += '</body></html>'
                await f.write(html_content)
            else:
                # Fallback to JSON if format not recognized
                logger.warning(f"Unknown export format: {export_format}, defaulting to JSON")
                await f.write(json.dumps(messages, indent=2))
        
        # Update job and sync state
        job.status = JobStatus.COMPLETED.value
        job.completed_at = datetime.utcnow()
        job.export_path = str(export_path)
        job.messages_scraped = len(messages)
        
        # Update sync state
        if messages and job.server_id is not None:
            update_sync_state(db, channel_id, str(job.server_id), 
                            messages[-1]['id'], len(messages))
        
        # Close session
        scraping_session.ended_at = datetime.utcnow()
        scraping_session.messages_scraped = len(messages)
        scraping_session.breaks_taken = scraper.breaks_taken
        
        db.commit()
        logger.info(f"Job {job_id} completed successfully. Scraped {len(messages)} messages")
        
    except Exception as e:
        logger.error(f"Error in job {job_id}: {e}", exc_info=True)
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        
        if 'scraping_session' in locals():
            scraping_session.ended_at = datetime.utcnow()
        
        db.commit()
    finally:
        if 'scraper' in locals() and scraper and scraper.client:
            await scraper.client.close()
        if 'client_task' in locals():
            client_task.cancel()
        db.close()

def update_sync_state(db, channel_id: str, server_id: str, last_message_id: str, message_count: int):
    """Update channel sync state after successful scraping"""
    try:
        channel_id_int = int(channel_id)
        server_id_int = int(server_id)
        last_message_id_int = int(last_message_id)
    except ValueError as e:
        logger.error(f"Invalid ID format in sync state update: {e}")
        return
    
    sync_state = db.query(ChannelSyncState).filter(
        ChannelSyncState.channel_id == channel_id_int
    ).first()
    
    if not sync_state:
        sync_state = ChannelSyncState(
            channel_id=channel_id_int,
            server_id=server_id_int
        )
        db.add(sync_state)
    
    # Update sync state
    sync_state.last_message_id = last_message_id_int
    sync_state.last_message_timestamp = datetime.utcnow()
    sync_state.total_messages = (sync_state.total_messages or 0) + message_count
    sync_state.last_sync_at = datetime.utcnow()
    
    db.commit()

def main():
    """Main worker entry point"""
    logger.info("Starting Discord Self-Bot Scraper Worker")
    
    # Create Redis connection
    redis_conn = Redis.from_url(settings.redis_url)
    
    # Create worker
    queues = [Queue('default', connection=redis_conn)]
    worker = Worker(queues, connection=redis_conn)
    
    # Start worker
    logger.info("Worker ready, waiting for jobs...")
    worker.work()

if __name__ == "__main__":
    main()