"""
Simplified authentication for local-only mode
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
from typing import Optional
import secrets

from auth import create_access_token
from config import settings

router = APIRouter()

# Simple local token for authentication
LOCAL_ACCESS_TOKEN = secrets.token_urlsafe(32)

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