"""
Discord server and channel management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import logging

from config import settings
from database import get_db, ChannelSyncState
from auth import get_current_user
from models import ServerResponse, ChannelResponse, ChannelSyncStateResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ServerResponse])
async def get_user_servers(current_user: dict = Depends(get_current_user)):
    """Get list of Discord servers the user is in"""
    discord_token = current_user.get("discord_access_token")
    if not discord_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Discord access token not found"
        )
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://discord.com/api/users/@me/guilds",
            headers={
                "Authorization": f"Bearer {discord_token}"
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch guilds: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch Discord servers"
            )
        
        guilds = response.json()
    
    # Convert to our response model
    servers = []
    for guild in guilds:
        # Check if user has admin permissions (simplified check)
        permissions = int(guild.get("permissions", 0))
        is_admin = (permissions & 0x8) == 0x8  # Administrator permission
        
        servers.append(ServerResponse(
            server_id=int(guild["id"]),
            name=guild["name"],
            icon_url=f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png" if guild.get("icon") else None,
            member_count=None  # Not available from this endpoint
        ))
    
    return servers


@router.get("/{server_id}/channels", response_model=List[ChannelResponse])
async def get_server_channels(
    server_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of channels in a Discord server"""
    # For now, we'll need the user to have their bot in the server
    # In a real implementation, we'd use the bot token to fetch channels
    
    if not settings.discord_bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot token not configured"
        )
    
    # Fetch channels using bot token
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://discord.com/api/guilds/{server_id}/channels",
            headers={
                "Authorization": f"Bot {settings.discord_bot_token}"
            }
        )
        
        if response.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bot doesn't have access to this server. Please add the bot to the server first."
            )
        elif response.status_code != 200:
            logger.error(f"Failed to fetch channels: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch channels"
            )
        
        channels_data = response.json()
    
    # Get sync state for all channels
    channel_ids = [int(ch["id"]) for ch in channels_data if ch["type"] in [0, 5]]  # Text channels only
    sync_states = db.query(ChannelSyncState).filter(
        ChannelSyncState.channel_id.in_(channel_ids)
    ).all()
    sync_map = {state.channel_id: state for state in sync_states}
    
    # Convert to response model
    channels = []
    for channel in channels_data:
        # Only include text channels (type 0) and news channels (type 5)
        if channel["type"] not in [0, 5]:
            continue
        
        channel_id = int(channel["id"])
        sync_state = sync_map.get(channel_id)
        
        channels.append(ChannelResponse(
            channel_id=channel_id,
            server_id=server_id,
            name=channel["name"],
            type="text" if channel["type"] == 0 else "news",
            category_id=int(channel["parent_id"]) if channel.get("parent_id") else None,
            position=channel["position"],
            topic=channel.get("topic"),
            is_nsfw=channel.get("nsfw", False),
            last_sync=ChannelSyncStateResponse.from_orm(sync_state) if sync_state else None
        ))
    
    # Sort by position
    channels.sort(key=lambda x: x.position)
    
    return channels


@router.post("/{server_id}/refresh")
async def refresh_server_data(
    server_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Refresh server data (placeholder for future enhancement)"""
    return {
        "message": "Server data refreshed",
        "server_id": server_id
    }