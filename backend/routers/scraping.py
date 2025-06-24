"""
Scraping job management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import uuid
from rq import Queue
from redis import Redis
import logging
import os
from pathlib import Path

from config import settings
from database import get_db, ScrapingJob, ChannelSyncState
from auth import get_current_user
from models import (
    CreateScrapingJobRequest, ScrapingJobResponse, 
    CheckUpdatesRequest, ChannelSyncStateResponse,
    JobStatus, StatsResponse
)
from queue_manager import get_redis_queue, enqueue_scraping_job

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/jobs", response_model=ScrapingJobResponse)
async def create_scraping_job(
    request: CreateScrapingJobRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new scraping job"""
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Get user token for self-bot mode
    user_token = os.environ.get("DISCORD_USER_TOKEN")
    if not user_token:
        # Try to get from stored tokens
        from routers.auth import user_discord_tokens
        user_id = current_user.get("user_id", "local-user")
        user_token = user_discord_tokens.get(user_id)
    
    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discord user token is required. Please set up your token first."
        )
    
    # Create job record - note: database might still expect integers
    job = ScrapingJob(
        job_id=job_id,
        server_id=int(request.server_id),  # Convert to int for database
        channel_id=int(request.channel_id),  # Convert to int for database
        channel_name=request.channel_name,
        job_type=request.job_type.value,
        status=JobStatus.PENDING.value,
        export_format=request.export_format.value,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end
    )
    db.add(job)
    db.commit()
    
    # Enqueue job
    try:
        queue = get_redis_queue()
        enqueue_scraping_job(
            queue=queue,
            job_id=job_id,
            channel_id=request.channel_id,  # Keep as string
            bot_token=user_token,  # Actually user_token for self-bot
            job_type=request.job_type.value,
            export_format=request.export_format.value,
            date_range_start=request.date_range_start,
            date_range_end=request.date_range_end,
            message_limit=request.message_limit
        )
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_id}: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start scraping job"
        )
    
    # Convert to response with string IDs
    # Create dict with string IDs
    job_dict = {
        'job_id': job.job_id,
        'server_id': str(job.server_id),
        'channel_id': str(job.channel_id),
        'channel_name': job.channel_name,
        'job_type': job.job_type,
        'status': job.status,
        'started_at': job.started_at,
        'completed_at': job.completed_at,
        'messages_scraped': job.messages_scraped,
        'export_path': job.export_path,
        'export_format': job.export_format,
        'error_message': job.error_message,
        'progress_percent': None
    }
    return ScrapingJobResponse(**job_dict)


@router.get("/jobs", response_model=List[ScrapingJobResponse])
async def list_scraping_jobs(
    skip: int = 0,
    limit: int = 50,
    status: Optional[JobStatus] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List scraping jobs with optional filtering"""
    query = db.query(ScrapingJob)
    
    if status:
        query = query.filter(ScrapingJob.status == status.value)
    
    jobs = query.order_by(ScrapingJob.started_at.desc()).offset(skip).limit(limit).all()
    
    # Calculate progress for running jobs
    responses = []
    for job in jobs:
        # Create dict with string IDs
        job_dict = {
            'job_id': job.job_id,
            'server_id': str(job.server_id),
            'channel_id': str(job.channel_id),
            'channel_name': job.channel_name,
            'job_type': job.job_type,
            'status': job.status,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'messages_scraped': job.messages_scraped,
            'export_path': job.export_path,
            'export_format': job.export_format,
            'error_message': job.error_message,
            'progress_percent': None
        }
        response = ScrapingJobResponse(**job_dict)
        
        # Use real progress from database
        if job.status == JobStatus.RUNNING.value:
            # Use actual progress_percent from database
            response.progress_percent = job.progress_percent or 0
        elif job.status == JobStatus.COMPLETED.value:
            response.progress_percent = 100
        else:
            response.progress_percent = 0
        
        responses.append(response)
    
    return responses


@router.get("/jobs/{job_id}", response_model=ScrapingJobResponse)
async def get_scraping_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific scraping job"""
    job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Create dict with string IDs
    job_dict = {
        'job_id': job.job_id,
        'server_id': str(job.server_id),
        'channel_id': str(job.channel_id),
        'channel_name': job.channel_name,
        'job_type': job.job_type,
        'status': job.status,
        'started_at': job.started_at,
        'completed_at': job.completed_at,
        'messages_scraped': job.messages_scraped,
        'export_path': job.export_path,
        'export_format': job.export_format,
        'error_message': job.error_message,
        'progress_percent': None
    }
    return ScrapingJobResponse(**job_dict)


@router.put("/jobs/{job_id}/cancel")
async def cancel_scraping_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a scraping job"""
    job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status not in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    # Update job status
    job.status = JobStatus.FAILED.value
    job.error_message = "Cancelled by user"
    job.completed_at = datetime.utcnow()
    db.commit()
    
    # TODO: Actually cancel the RQ job
    
    return {"message": "Job cancelled successfully"}


@router.post("/check-updates", response_model=List[ChannelSyncStateResponse])
async def check_channel_updates(
    request: CheckUpdatesRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if channels have new messages since last sync"""
    # Get sync states for requested channels (convert string IDs to int for DB query)
    sync_states = db.query(ChannelSyncState).filter(
        ChannelSyncState.channel_id.in_([int(cid) for cid in request.channel_ids])
    ).all()
    
    responses = []
    for state in sync_states:
        response = ChannelSyncStateResponse.from_orm(state)
        # Convert IDs to strings
        response.channel_id = str(state.channel_id)
        response.server_id = str(state.server_id)
        if state.last_message_id:
            response.last_message_id = str(state.last_message_id)
        
        # In real implementation, we'd check Discord API for new messages
        # For now, just mark channels older than 1 day as needing update
        if state.last_sync_at:
            hours_since_sync = (datetime.utcnow() - state.last_sync_at).total_seconds() / 3600
            response.needs_update = hours_since_sync > 24
        else:
            response.needs_update = True
        
        responses.append(response)
    
    # Add entries for channels not yet synced
    synced_ids = {state.channel_id for state in sync_states}
    for channel_id in request.channel_ids:
        if channel_id not in synced_ids:
            responses.append(ChannelSyncStateResponse(
                channel_id=channel_id,
                server_id="0",  # String ID
                channel_name=None,
                last_message_id=None,
                last_message_timestamp=None,
                total_messages=0,
                last_sync_at=None,
                needs_update=True
            ))
    
    return responses


@router.get("/history/{channel_id}", response_model=List[ScrapingJobResponse])
async def get_channel_scraping_history(
    channel_id: str,  # Changed to string
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get scraping history for a specific channel"""
    jobs = db.query(ScrapingJob).filter(
        ScrapingJob.channel_id == int(channel_id)  # Convert to int for DB query
    ).order_by(ScrapingJob.started_at.desc()).limit(20).all()
    
    # Convert IDs to strings in responses
    responses = []
    for job in jobs:
        job_dict = {
            'job_id': job.job_id,
            'server_id': str(job.server_id),
            'channel_id': str(job.channel_id),
            'channel_name': job.channel_name,
            'job_type': job.job_type,
            'status': job.status,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'messages_scraped': job.messages_scraped,
            'export_path': job.export_path,
            'export_format': job.export_format,
            'error_message': job.error_message,
            'progress_percent': None
        }
        responses.append(ScrapingJobResponse(**job_dict))
    
    return responses


@router.get("/stats", response_model=StatsResponse)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    # Count unique servers and channels
    total_servers = db.query(ScrapingJob.server_id).distinct().count()
    total_channels = db.query(ScrapingJob.channel_id).distinct().count()
    
    # Count total messages (sum from all jobs)
    total_messages = db.query(
        func.sum(ScrapingJob.messages_scraped)
    ).scalar() or 0
    
    # Count jobs
    total_jobs = db.query(ScrapingJob).count()
    active_jobs = db.query(ScrapingJob).filter(
        ScrapingJob.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
    ).count()
    
    # Get last sync time
    last_job = db.query(ScrapingJob).filter(
        ScrapingJob.status == JobStatus.COMPLETED.value
    ).order_by(ScrapingJob.completed_at.desc()).first()
    
    return StatsResponse(
        total_servers=total_servers,
        total_channels=total_channels,
        total_messages=total_messages,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        last_sync=last_job.completed_at if last_job else None
    )


@router.get("/exports/{job_id}/download")
async def download_export(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Download the export file for a completed job"""
    # Get job from database
    job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if job is completed and has export path
    if job.status != JobStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not completed yet"
        )
    
    if not job.export_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found"
        )
    
    # Check if export exists
    export_path = Path(job.export_path)
    if not export_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export no longer exists"
        )
    
    # If it's a directory (split export), create a zip file
    if export_path.is_dir():
        import zipfile
        import tempfile
        from fastapi.background import BackgroundTask
        
        # Create temporary zip file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            zip_path = tmp.name
            
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files in the directory
            for file_path in export_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(export_path)
                    zipf.write(file_path, arcname)
        
        # Return zip file
        filename = f"discord_export_{job.channel_name}_{job.job_id[:8]}.zip"
        return FileResponse(
            path=zip_path,
            filename=filename,
            media_type='application/zip',
            background=BackgroundTask(lambda: os.unlink(zip_path))  # Clean up temp file
        )
    else:
        # Single file export
        filename = f"discord_export_{job.channel_name}_{job.job_id[:8]}.{job.export_format}"
        
        # Set appropriate content type based on format
        content_types = {
            'json': 'application/json',
            'html': 'text/html',
            'csv': 'text/csv',
            'txt': 'text/plain'
        }
        media_type = content_types.get(job.export_format, 'application/octet-stream')
        
        return FileResponse(
            path=str(export_path),
            filename=filename,
            media_type=media_type
        )