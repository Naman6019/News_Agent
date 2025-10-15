"""
Health check endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.config import settings
from app.services.news_service import NewsService

router = APIRouter()
news_service = NewsService()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME,
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check including service status."""
    try:
        # Get service status
        service_status = await news_service.get_service_status()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": settings.VERSION,
            "service": settings.PROJECT_NAME,
            "services": service_status,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@router.get("/readiness")
async def readiness_check():
    """Kubernetes-style readiness check."""
    try:
        # Test critical services
        test_results = await news_service.test_services()

        if not test_results.get("overall", False):
            raise HTTPException(
                status_code=503,
                detail="Services not ready"
            )

        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "tests": test_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Readiness check failed: {str(e)}")


@router.get("/liveness")
async def liveness_check():
    """Kubernetes-style liveness check."""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
    }