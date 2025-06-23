"""
Scraping job management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from rq import Queue
from redis import Redis
import logging

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
    
    # Get bot token (from request or stored)
    bot_token = request.bot_token or settings.discord_bot_token
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot token is required"
        )
    
    # Create job record
    job = ScrapingJob(
        job_id=job_id,
        server_id=request.server_id,
        channel_id=request.channel_id,
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
            channel_id=request.channel_id,
            bot_token=bot_token,
            job_type=request.job_type.value,
            export_format=request.export_format.value,
            date_range_start=request.date_range_start,
            date_range_end=request.date_range_end
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
    
    return ScrapingJobResponse.from_orm(job)


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
        response = ScrapingJobResponse.from_orm(job)
        
        # Add progress calculation for running jobs
        if job.status == JobStatus.RUNNING.value:
            # Simple progress estimation based on time
            # In real implementation, we'd parse DCE output
            if job.started_at:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                # Estimate: 1000 messages per minute
                estimated_progress = min(int((elapsed / 60) * 10), 95)
                response.progress_percent = estimated_progress
        
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
    
    return ScrapingJobResponse.from_orm(job)


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
    # Get sync states for requested channels
    sync_states = db.query(ChannelSyncState).filter(
        ChannelSyncState.channel_id.in_(request.channel_ids)
    ).all()
    
    responses = []
    for state in sync_states:
        response = ChannelSyncStateResponse.from_orm(state)
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
                server_id=0,  # Would need to look this up
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
    channel_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get scraping history for a specific channel"""
    jobs = db.query(ScrapingJob).filter(
        ScrapingJob.channel_id == channel_id
    ).order_by(ScrapingJob.started_at.desc()).limit(20).all()
    
    return [ScrapingJobResponse.from_orm(job) for job in jobs]


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
        db.func.sum(ScrapingJob.messages_scraped)
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