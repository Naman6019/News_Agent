"""
AI News Agent - Main FastAPI Application
Sends daily news summaries via WhatsApp using RSS feeds and AI
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.services.scheduler import NewsScheduler
from app.api.v1.endpoints.scheduler import set_scheduler


# Global scheduler instance
news_scheduler: NewsScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    global news_scheduler

    # Setup logging
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Starting AI News Agent...")

    # Initialize and start the news scheduler
    try:
        logger.info("Initializing news scheduler...")
        news_scheduler = NewsScheduler()
        logger.info("News scheduler initialized, attempting to start...")
        await news_scheduler.start()
        logger.info("News scheduler started successfully")

        # Set the global scheduler instance for API endpoints
        set_scheduler(news_scheduler)
        logger.info("Scheduler registered with API endpoints")
    except Exception as e:
        logger.error(f"Failed to start news scheduler: {e}")
        logger.warning("Application will continue without automated scheduling")
        logger.info("API will still work for manual operations")
        news_scheduler = None  # Keep as None if initialization fails

    yield

    # Shutdown
    logger.info("Shutting down AI News Agent...")
    if news_scheduler:
        await news_scheduler.stop()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered news agent that delivers daily summaries via WhatsApp",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "scheduler_running": news_scheduler.is_running if news_scheduler else False,
        "scheduler_initialized": news_scheduler is not None,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI News Agent API",
        "docs": "/docs",
        "version": settings.VERSION,
    }


# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Cloud Run sets this automatically
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
