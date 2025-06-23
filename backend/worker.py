"""
Worker process for handling scraping jobs
"""
import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rq import Worker, Queue
from redis import Redis

# Add parent directory to path to import discord_export
sys.path.append(str(Path(__file__).parent.parent))

from config import settings
from database import ScrapingJob, ChannelSyncState, Message
from models import JobStatus, JobType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup for worker
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def scrape_channel(
    job_id: str,
    channel_id: int,
    bot_token: str,
    job_type: str,
    export_format: str,
    date_range_start: Optional[datetime] = None,
    date_range_end: Optional[datetime] = None
):
    """Execute a channel scraping job"""
    logger.info(f"Starting scraping job {job_id} for channel {channel_id}")
    
    db = SessionLocal()
    try:
        # Update job status to running
        job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return
        
        job.status = JobStatus.RUNNING.value
        db.commit()
        
        # Get channel sync state for incremental scraping
        sync_state = None
        if job_type == JobType.INCREMENTAL.value:
            sync_state = db.query(ChannelSyncState).filter(
                ChannelSyncState.channel_id == channel_id
            ).first()
        
        # Prepare discord_export.py command
        cmd = [
            sys.executable,
            "../discord_export.py",
            "-c", str(channel_id),
            "-t", bot_token,
            "-f", export_format,
            "-o", settings.exports_dir
        ]
        
        # Add date filters based on job type
        if job_type == JobType.INCREMENTAL.value and sync_state and sync_state.last_message_timestamp:
            # For incremental, start after the last synced message
            cmd.extend(["--after", sync_state.last_message_timestamp.strftime("%Y-%m-%d")])
        elif job_type == JobType.DATE_RANGE.value:
            if date_range_start:
                cmd.extend(["--after", date_range_start.strftime("%Y-%m-%d")])
            if date_range_end:
                cmd.extend(["--before", date_range_end.strftime("%Y-%m-%d")])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Execute discord_export.py
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        # Monitor progress by reading stdout
        message_count = 0
        for line in process.stdout:
            logger.info(f"DCE output: {line.strip()}")
            
            # Try to parse progress from DCE output
            # Look for patterns like "Exported 1000 messages"
            if "Exported" in line and "messages" in line:
                try:
                    parts = line.split()
                    idx = parts.index("Exported")
                    if idx + 1 < len(parts):
                        message_count = int(parts[idx + 1])
                        # Update job progress
                        job.messages_scraped = message_count
                        db.commit()
                except (ValueError, IndexError):
                    pass
        
        # Wait for process to complete
        return_code = process.wait()
        stderr_output = process.stderr.read()
        
        if return_code == 0:
            # Success!
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()
            
            # Find the export file (most recent file in exports directory)
            export_dir = Path(settings.exports_dir)
            export_files = list(export_dir.glob(f"{channel_id}_*.{export_format}"))
            if export_files:
                latest_file = max(export_files, key=lambda f: f.stat().st_mtime)
                job.export_path = str(latest_file)
                
                # Update channel sync state
                update_sync_state(db, channel_id, job.server_id, job.channel_name, message_count)
                
                # Optionally parse and store messages if enabled
                if settings.store_message_content and export_format == "json":
                    store_messages_from_export(db, latest_file, channel_id, job.server_id)
            
            logger.info(f"Job {job_id} completed successfully. Scraped {message_count} messages")
        else:
            # Failed
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.utcnow()
            job.error_message = stderr_output or "Unknown error"
            logger.error(f"Job {job_id} failed: {job.error_message}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in job {job_id}: {e}", exc_info=True)
        if job:
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


def update_sync_state(db, channel_id: int, server_id: int, channel_name: str, message_count: int):
    """Update or create channel sync state after successful scraping"""
    sync_state = db.query(ChannelSyncState).filter(
        ChannelSyncState.channel_id == channel_id
    ).first()
    
    if not sync_state:
        sync_state = ChannelSyncState(
            channel_id=channel_id,
            server_id=server_id,
            channel_name=channel_name
        )
        db.add(sync_state)
    
    # Update sync state
    sync_state.total_messages = (sync_state.total_messages or 0) + message_count
    sync_state.last_sync_at = datetime.utcnow()
    
    # In a real implementation, we'd parse the export to get actual message IDs/timestamps
    # For now, just update the timestamp
    sync_state.last_message_timestamp = datetime.utcnow()
    
    db.commit()


def store_messages_from_export(db, export_file: Path, channel_id: int, server_id: int):
    """Parse and store messages from JSON export (optional feature)"""
    try:
        with open(export_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Assuming DCE JSON format has messages array
        messages = data.get('messages', [])
        
        for msg_data in messages[-100:]:  # Only store last 100 messages for now
            # Check if message already exists
            existing = db.query(Message).filter(
                Message.message_id == int(msg_data['id'])
            ).first()
            
            if not existing:
                message = Message(
                    message_id=int(msg_data['id']),
                    channel_id=channel_id,
                    server_id=server_id,
                    author_id=int(msg_data['author']['id']),
                    author_name=msg_data['author']['name'],
                    content=msg_data.get('content', ''),
                    created_at=datetime.fromisoformat(msg_data['timestamp'].replace('Z', '+00:00'))
                )
                db.add(message)
        
        db.commit()
        logger.info(f"Stored {len(messages)} messages from export")
        
    except Exception as e:
        logger.error(f"Failed to store messages from export: {e}")


def main():
    """Main worker entry point"""
    logger.info("Starting Discord Scraper Worker")
    
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