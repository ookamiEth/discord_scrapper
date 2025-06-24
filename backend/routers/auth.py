"""
Simplified authentication for local-only mode
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets
import os
from pydantic import BaseModel

from auth import create_access_token, get_current_user
from config import settings

router = APIRouter()

# Simple local token for authentication
LOCAL_ACCESS_TOKEN = secrets.token_urlsafe(32)

# Store user tokens in memory (in production, use database)
user_discord_tokens: Dict[str, str] = {}

class TokenRequest(BaseModel):
    token: str

@router.post("/local-login")
async def local_login():
    """Simple login that returns a token for local use"""
    # Create a token for local user
    access_token = create_access_token(
        data={
            "sub": "local-user",
            "user_id": "local-user",
            "username": "Local User"
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": "local-user",
            "username": "Local User"
        }
    }

@router.get("/me")
async def get_current_user_info():
    """Return local user info"""
    return {
        "user_id": "local-user",
        "username": "Local User",
        "discord_id": "local"
    }

@router.post("/discord/set-token")
async def set_discord_token(
    request: TokenRequest,
    current_user: dict = Depends(get_current_user)
):
    """Store the user's Discord token for self-bot usage"""
    user_id = current_user.get("user_id", "local-user")
    token = request.token
    
    # Basic validation - Discord tokens are usually 59+ characters
    if len(token) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Discord token format"
        )
    
    # Store token (in production, encrypt and store in database)
    user_discord_tokens[user_id] = token
    
    # Also store in environment for the self-bot to use
    os.environ["DISCORD_USER_TOKEN"] = token
    
    return {"status": "success", "message": "Discord token saved successfully"}

@router.get("/discord/token-status")
async def get_discord_token_status(
    current_user: dict = Depends(get_current_user)
):
    """Check if user has a Discord token configured"""
    user_id = current_user.get("user_id", "local-user")
    
    # Check if token exists
    has_token = user_id in user_discord_tokens or os.environ.get("DISCORD_USER_TOKEN") is not None
    
    return {
        "has_token": has_token,
        "user_id": user_id
    }