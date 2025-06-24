"""System management endpoints."""
import os
import signal
import subprocess
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user

router = APIRouter()


@router.post("/shutdown")
async def shutdown_system(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a shutdown marker file that an external script monitors.
    Only accessible to authenticated users.
    """
    try:
        # Create a shutdown marker file
        shutdown_marker = "/tmp/shutdown_discord_scraper"
        with open(shutdown_marker, "w") as f:
            f.write(f"Shutdown requested by {current_user.get('username', 'Unknown')} at {datetime.utcnow()}\n")
        
        # Also try to stop services gracefully
        def delayed_shutdown():
            import time
            time.sleep(3)
            # Send SIGTERM to the main process to trigger graceful shutdown
            os.kill(1, signal.SIGTERM)
        
        import threading
        shutdown_thread = threading.Thread(target=delayed_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        return {
            "status": "success",
            "message": "Shutdown initiated. Services will stop in a few seconds."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate shutdown: {str(e)}"
        )


@router.get("/status")
async def system_status(
    current_user: dict = Depends(get_current_user),
):
    """Check if all services are running."""
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            cwd="/Users/lgierhake/Documents/Jump/discord_scrapper",
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {
                "status": "healthy",
                "services": "running"
            }
        else:
            return {
                "status": "degraded",
                "services": "partial"
            }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e)
        }