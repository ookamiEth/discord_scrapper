"""
Authentication routes - Discord OAuth2 flow
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
import secrets
from datetime import datetime, timedelta
from typing import Optional
import logging

from config import settings
from database import get_db
from auth import create_access_token, get_current_user_optional
from models import BotTokenResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Store OAuth state temporarily (in production, use Redis or database)
oauth_states = {}


@router.get("/discord/login")
async def discord_login():
    """Initiate Discord OAuth2 flow"""
    if not settings.discord_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Discord OAuth not configured"
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = datetime.utcnow()
    
    # Clean up old states (older than 10 minutes)
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    oauth_states_copy = oauth_states.copy()
    for old_state, timestamp in oauth_states_copy.items():
        if timestamp < cutoff:
            del oauth_states[old_state]
    
    # Build Discord OAuth URL
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state
    }
    
    oauth_url = "https://discord.com/api/oauth2/authorize?" + "&".join(
        f"{k}={v}" for k, v in params.items()
    )
    
    return {"url": oauth_url}


@router.get("/discord/callback")
async def discord_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Handle Discord OAuth2 callback"""
    # Verify state
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state"
        )
    
    del oauth_states[state]
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        if token_response.status_code != 200:
            logger.error(f"Discord token exchange failed: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        
        # Get user info
        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )
        
        user_data = user_response.json()
    
    # Create JWT token for our app
    jwt_token = create_access_token(
        data={
            "sub": user_data["id"],
            "discord_id": user_data["id"],
            "username": user_data["username"],
            "discord_access_token": access_token  # Store for API calls
        }
    )
    
    # Redirect to frontend with token
    redirect_url = f"{settings.frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=redirect_url)


@router.post("/logout")
async def logout():
    """Logout endpoint (mainly for frontend state management)"""
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user_optional)):
    """Get current user information"""
    if not current_user:
        return None
    
    return {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "discord_id": current_user["discord_id"]
    }