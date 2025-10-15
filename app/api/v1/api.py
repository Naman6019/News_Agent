"""
Main API router for AI News Agent
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, news, scheduler, whatsapp


api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)
api_router.include_router(
    news.router,
    prefix="/news",
    tags=["news"]
)
api_router.include_router(
    scheduler.router,
    prefix="/scheduler",
    tags=["scheduler"]
)
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["whatsapp"]
)