"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal
from enum import Enum


class JobType(str, Enum):
    """Types of scraping jobs"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DATE_RANGE = "date_range"


class JobStatus(str, Enum):
    """Status of scraping jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ExportFormat(str, Enum):
    """Export formats supported by DiscordChatExporter"""
    JSON = "json"
    HTML = "html"
    CSV = "csv"
    TXT = "txt"


# Request models
class CreateScrapingJobRequest(BaseModel):
    """Request to create a new scraping job"""
    server_id: int = Field(..., description="Discord server ID")
    channel_id: int = Field(..., description="Discord channel ID")
    channel_name: Optional[str] = Field(None, description="Channel name for display")
    job_type: JobType = Field(JobType.INCREMENTAL, description="Type of scraping job")
    export_format: ExportFormat = Field(ExportFormat.JSON, description="Export format")
    date_range_start: Optional[datetime] = Field(None, description="Start date for date range scraping")
    date_range_end: Optional[datetime] = Field(None, description="End date for date range scraping")
    bot_token: Optional[str] = Field(None, description="Bot token to use (if not using saved token)")


class CheckUpdatesRequest(BaseModel):
    """Request to check channels for updates"""
    channel_ids: List[int] = Field(..., description="List of channel IDs to check")


# Response models
class ScrapingJobResponse(BaseModel):
    """Response for a scraping job"""
    job_id: str
    server_id: int
    channel_id: int
    channel_name: Optional[str]
    job_type: JobType
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime]
    messages_scraped: int
    export_path: Optional[str]
    export_format: ExportFormat
    error_message: Optional[str]
    progress_percent: Optional[int] = Field(None, description="Progress percentage (0-100)")
    
    class Config:
        from_attributes = True


class ChannelSyncStateResponse(BaseModel):
    """Response for channel sync state"""
    channel_id: int
    server_id: int
    channel_name: Optional[str]
    last_message_id: Optional[int]
    last_message_timestamp: Optional[datetime]
    total_messages: int
    last_sync_at: Optional[datetime]
    needs_update: bool = Field(False, description="Whether channel has new messages")
    
    class Config:
        from_attributes = True


class ServerResponse(BaseModel):
    """Discord server information"""
    server_id: int
    name: str
    icon_url: Optional[str]
    member_count: Optional[int]
    channel_count: Optional[int] = Field(None, description="Number of accessible channels")


class ChannelResponse(BaseModel):
    """Discord channel information"""
    channel_id: int
    server_id: int
    name: str
    type: str
    category_id: Optional[int]
    position: int
    topic: Optional[str]
    is_nsfw: bool = False
    last_sync: Optional[ChannelSyncStateResponse] = None


class BotTokenResponse(BaseModel):
    """Bot token information (without exposing the actual token)"""
    token_id: int
    token_name: str
    server_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Dashboard statistics"""
    total_servers: int
    total_channels: int
    total_messages: int
    total_jobs: int
    active_jobs: int
    last_sync: Optional[datetime]


class HealthResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime
    services: dict[str, str]