"""
Scheduler endpoints for managing news delivery schedules
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.services.scheduler import NewsScheduler

router = APIRouter()

# Global scheduler instance - will be set by the main app
news_scheduler: NewsScheduler = None


def set_scheduler(scheduler: NewsScheduler):
    """Set the global scheduler instance."""
    global news_scheduler
    news_scheduler = scheduler


@router.get("/status")
async def get_scheduler_status():
    """Get current scheduler status."""
    if not news_scheduler:
        return {
            "scheduler_status": {
                "is_running": False,
                "error": "Scheduler not initialized - check configuration",
                "jobs": [],
                "timezone": "Asia/Calcutta",
                "next_runs": {"morning": None, "evening": None}
            },
            "timestamp": datetime.now().isoformat(),
        }

    try:
        status = news_scheduler.get_scheduler_status()
        return {
            "scheduler_status": status,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting scheduler status: {str(e)}")


@router.post("/trigger/{delivery_type}")
async def trigger_manual_delivery(delivery_type: str):
    """Manually trigger a news delivery."""
    if delivery_type not in ["morning", "evening"]:
        raise HTTPException(
            status_code=400,
            detail="Delivery type must be 'morning' or 'evening'"
        )

    if not news_scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        success = await news_scheduler.trigger_manual_delivery(delivery_type)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger {delivery_type} delivery"
            )

        return {
            "message": f"{delivery_type.title()} news delivery triggered successfully",
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering delivery: {str(e)}")


@router.get("/next-runs")
async def get_next_run_times():
    """Get next scheduled run times."""
    if not news_scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        next_runs = news_scheduler.get_next_run_times()

        return {
            "next_runs": {
                "morning": next_runs["morning"].isoformat() if next_runs["morning"] else None,
                "evening": next_runs["evening"].isoformat() if next_runs["evening"] else None,
            },
            "timezone": "Asia/Calcutta",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting next run times: {str(e)}")


@router.get("/jobs")
async def get_scheduler_jobs():
    """Get list of scheduled jobs."""
    if not news_scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        status = news_scheduler.get_scheduler_status()

        return {
            "jobs": status.get("jobs", []),
            "is_running": status.get("is_running", False),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting scheduler jobs: {str(e)}")