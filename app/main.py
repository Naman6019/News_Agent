"""
AI News Agent - Main FastAPI Application
Sends daily news summaries via WhatsApp using RSS feeds and AI
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

from fastapi import FastAPI
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

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting AI News Agent...")
    logger.info(f"Render environment detected, PORT = {os.getenv('PORT')}")

    try:
        logger.info("Initializing news scheduler...")
        news_scheduler = NewsScheduler()
        set_scheduler(news_scheduler)
        logger.info("News scheduler initialized")

        # ✅ Run scheduler startup in background (non-blocking)
        async def start_scheduler_background():
            try:
                await news_scheduler.start()
                logger.info("News scheduler started successfully in background")
            except Exception as e:
                logger.error(f"Failed to start news scheduler in background: {e}")

        asyncio.create_task(start_scheduler_background())
        logger.info("Background scheduler startup task launched")
    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")
        news_scheduler = None

    yield  # Allow app startup to continue immediately

    # On shutdown
    logger.info("Shutting down AI News Agent...")
    if news_scheduler:
        try:
            await news_scheduler.stop()
            logger.info("Scheduler stopped cleanly")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")
    logger.info("Shutdown complete")


# Create FastAPI app
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


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Root endpoint (supports GET & HEAD for uptime monitors)."""
    return {
        "message": "AI News Agent API",
        "docs": "/docs",
        "version": settings.VERSION,
    }



# Include all routers
app.include_router(api_router, prefix=settings.API_V1_STR)


# Only used when running locally (Render overrides this with Docker CMD)
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
