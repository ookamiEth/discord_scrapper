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

# Add this model for manual server addition
from pydantic import BaseModel
import json
import os

# Store manually added servers persistently
SERVERS_FILE = "/tmp/discord_scraper_servers.json"

def load_servers():
    """Load servers from persistent storage"""
    if os.path.exists(SERVERS_FILE):
        try:
            with open(SERVERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_servers(servers):
    """Save servers to persistent storage"""
    with open(SERVERS_FILE, 'w') as f:
        json.dump(servers, f)

class ManualServerRequest(BaseModel):
    server_id: str
    server_name: str
    channel_id: str
    channel_name: str
    is_verified: bool = False


@router.post("/manual")
async def add_server_manually(
    request: ManualServerRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually add a server and channel for scraping (self-bot mode)"""
    if current_user.get("user_id") != "local-user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manual server addition is only available in self-bot mode"
        )
    
    # Store the server info in the database
    # For now, we'll store it in session/memory since we don't have a proper server table
    # In production, you'd want to create a proper database table for manually added servers
    
    # Create a mock server response - store IDs as strings to avoid JS precision issues
    server = {
        "server_id": request.server_id,  # Keep as string
        "name": request.server_name,
        "icon_url": None,
        "is_admin": True,  # Assume we have access
        "member_count": 0,
        "is_verified": request.is_verified,
        "channel_id": request.channel_id,  # Keep as string
        "channel_name": request.channel_name
    }
    
    # Load existing servers
    servers = load_servers()
    
    # Check if server already exists
    existing = next((s for s in servers if s['server_id'] == server['server_id']), None)
    if existing:
        # Update existing server
        existing.update(server)
    else:
        # Add new server
        servers.append(server)
    
    # Save to persistent storage
    save_servers(servers)
    
    return {"status": "success", "message": "Server added successfully", "server": server}


@router.get("/", response_model=List[ServerResponse])
async def get_user_servers(current_user: dict = Depends(get_current_user)):
    """Get list of Discord servers the user is in"""
    # In local mode, return manually added servers
    if current_user.get("user_id") == "local-user":
        # Return manually added servers from persistent storage
        servers = load_servers()
        # Return servers with string IDs
        result = []
        for s in servers:
            # Keep server_id as string
            server_id = str(s['server_id'])
            result.append(ServerResponse(
                server_id=server_id,
                name=s['name'],
                icon_url=s['icon_url'],
                is_admin=s['is_admin'],
                member_count=s['member_count']
            ))
        logger.info(f"Returning servers: {[s.server_id for s in result]}")
        return result
    
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
            server_id=guild["id"],  # Keep as string
            name=guild["name"],
            icon_url=f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png" if guild.get("icon") else None,
            member_count=None  # Not available from this endpoint
        ))
    
    return servers


@router.get("/{server_id}/channels", response_model=List[ChannelResponse])
async def get_server_channels(
    server_id: str,  # Changed to string
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of channels in a Discord server"""
    # In local mode, return the manually added channel for this server
    if current_user.get("user_id") == "local-user":
        logger.info(f"Getting channels for server {server_id} in local mode")
        servers = load_servers()
        
        # Find server by comparing the first 17 digits (to handle JS precision issues)
        server = None
        server_id_str = str(server_id)
        for s in servers:
            stored_id_str = str(s['server_id'])
            # Compare first 17 digits or exact match
            if stored_id_str == server_id_str or stored_id_str[:17] == server_id_str[:17]:
                server = s
                logger.info(f"Found matching server: {s['name']} (stored: {stored_id_str}, requested: {server_id_str})")
                break
        
        if not server:
            logger.warning(f"No server found for ID {server_id}. Available servers: {[str(s['server_id']) for s in servers]}")
        
        if server:
                return [
                    ChannelResponse(
                        channel_id=str(server['channel_id']),  # Keep as string
                        server_id=server_id,  # Already a string
                        name=server['channel_name'],
                        type="text",  # Text channel
                        position=0,
                        category_id=None,
                        topic=None,
                        is_nsfw=False,
                        last_sync=None
                    )
                ]
        return []
    
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
    channel_ids = [ch["id"] for ch in channels_data if ch["type"] in [0, 5]]  # Keep as strings
    # Note: This sync state query might need adjustment if database still uses integer IDs
    sync_states = db.query(ChannelSyncState).filter(
        ChannelSyncState.channel_id.in_([int(cid) for cid in channel_ids])  # Convert for DB query if needed
    ).all()
    sync_map = {str(state.channel_id): state for state in sync_states}  # Map with string keys
    
    # Convert to response model
    channels = []
    for channel in channels_data:
        # Only include text channels (type 0) and news channels (type 5)
        if channel["type"] not in [0, 5]:
            continue
        
        channel_id = channel["id"]  # Keep as string
        sync_state = sync_map.get(channel_id)
        
        channels.append(ChannelResponse(
            channel_id=channel_id,  # String
            server_id=server_id,    # String
            name=channel["name"],
            type="text" if channel["type"] == 0 else "news",
            category_id=channel.get("parent_id"),  # Keep as string if present
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
    server_id: str,  # Changed to string
    current_user: dict = Depends(get_current_user)
):
    """Refresh server data (placeholder for future enhancement)"""
    return {
        "message": "Server data refreshed",
        "server_id": server_id
    }