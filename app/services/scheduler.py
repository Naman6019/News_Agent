"""
News Delivery Scheduler
Manages scheduled delivery of news digests via WhatsApp
"""

import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError as e:
    APSCHEDULER_AVAILABLE = False
    print(f"Warning: APScheduler not available: {e}")

try:
    from pytz import timezone
    PYTZ_AVAILABLE = True
except ImportError as e:
    PYTZ_AVAILABLE = False
    print(f"Warning: pytz not available: {e}")

from app.core.config import settings
from app.core.logging import StructuredLogger
from app.services.news_service import NewsService


class NewsScheduler:
    """Scheduler for automated news delivery."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        try:
            # Check if APScheduler is available
            if not APSCHEDULER_AVAILABLE:
                self.logger.error("APScheduler not available - scheduler disabled")
                self.scheduler = None
                self.news_service = None
                self.is_running = False
                return

            # Initialize scheduler with error handling
            try:
                self.logger.info(f"Initializing AsyncIOScheduler with timezone: {settings.DELIVERY_TIMEZONE}")
                self.scheduler = AsyncIOScheduler(timezone=settings.DELIVERY_TIMEZONE)
                self.logger.info("AsyncIOScheduler initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize AsyncIOScheduler: {e}")
                self.logger.error(f"Timezone setting: {settings.DELIVERY_TIMEZONE}")
                self.scheduler = None
                raise

            # Try to initialize news service, but don't fail if Twilio is not configured
            try:
                self.news_service = NewsService()
                self.logger.info("NewsScheduler initialized successfully with all services")
            except Exception as e:
                self.logger.warning(f"NewsService initialization failed: {e}")
                self.logger.info("Scheduler will work for testing, but WhatsApp delivery will be disabled")
                self.news_service = None

            self.is_running = False
            self.logger.info("NewsScheduler initialization completed")

        except Exception as e:
            self.logger.error(f"Failed to initialize NewsScheduler: {e}")
            # Create dummy objects for graceful degradation
            self.scheduler = None
            self.news_service = None
            self.is_running = False

    async def start(self) -> None:
        """Start the news scheduler."""
        try:
            if not self.scheduler:
                self.logger.error("Scheduler not properly initialized")
                return

            self.logger.info("Starting news scheduler...")

            # Schedule morning delivery (8 AM IST)
            try:
                morning_trigger = CronTrigger(
                    hour=settings.MORNING_DELIVERY_HOUR,
                    minute=0,
                    timezone=settings.DELIVERY_TIMEZONE
                )

                # Schedule evening delivery (6 PM IST)
                evening_trigger = CronTrigger(
                    hour=settings.EVENING_DELIVERY_HOUR,
                    minute=0,
                    timezone=settings.DELIVERY_TIMEZONE
                )

                # Add jobs to scheduler (only if news_service is available)
                if self.news_service:
                    self.scheduler.add_job(
                        func=self._deliver_morning_news,
                        trigger=morning_trigger,
                        id="morning_news",
                        name="Morning News Delivery",
                        replace_existing=True
                    )

                    self.scheduler.add_job(
                        func=self._deliver_evening_news,
                        trigger=evening_trigger,
                        id="evening_news",
                        name="Evening News Delivery",
                        replace_existing=True
                    )

                    self.logger.info(
                        f"News scheduler started with WhatsApp delivery - Morning: {settings.MORNING_DELIVERY_HOUR}:00, "
                        f"Evening: {settings.EVENING_DELIVERY_HOUR}:00 ({settings.DELIVERY_TIMEZONE})"
                    )
                else:
                    self.logger.info(
                        f"News scheduler started for testing - Morning: {settings.MORNING_DELIVERY_HOUR}:00, "
                        f"Evening: {settings.EVENING_DELIVERY_HOUR}:00 ({settings.DELIVERY_TIMEZONE})"
                    )
                    self.logger.warning("WhatsApp delivery disabled - configure Twilio credentials to enable")

                # Start the scheduler
                self.logger.info("Starting APScheduler...")
                try:
                    self.scheduler.start()
                    self.is_running = True
                    self.logger.info("APScheduler started successfully")
                except Exception as e:
                    self.logger.error(f"Failed to start APScheduler: {e}")
                    self.is_running = False
                    raise

            except Exception as e:
                self.logger.error(f"Failed to schedule jobs: {e}")
                raise

        except Exception as e:
            self.logger.error(f"Failed to start news scheduler", exc=e)
            raise

    async def stop(self) -> None:
        """Stop the news scheduler."""
        try:
            self.logger.info("Stopping news scheduler...")
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            self.logger.info("News scheduler stopped")
        except Exception as e:
            self.logger.error(f"Error stopping news scheduler", exc=e)

    async def _deliver_morning_news(self) -> None:
        """Deliver morning news digest."""
        await self._deliver_news("morning")

    async def _deliver_evening_news(self) -> None:
        """Deliver evening news digest."""
        await self._deliver_news("evening")

    async def _deliver_news(self, delivery_type: str) -> None:
        """Deliver news digest for the specified time."""
        try:
            self.logger.info(f"Starting {delivery_type} news delivery")

            # Generate news digest with delivery time
            digest = await self.news_service.generate_daily_digest(delivery_type)

            if not digest:
                error_msg = f"No news content available for {delivery_type} delivery"
                self.logger.error(error_msg)

                # Send error notification via WhatsApp
                await self.news_service.whatsapp_service.send_error_notification(error_msg)
                return

            # Send via WhatsApp
            success = await self.news_service.whatsapp_service.send_news_digest(
                digest, delivery_type
            )

            if success:
                self.logger.info(f"{delivery_type.title()} news delivered successfully")

                # Send delivery confirmation
                article_count = await self._count_articles_in_digest(digest)
                await self.news_service.whatsapp_service.send_delivery_confirmation(
                    delivery_type, article_count
                )
            else:
                error_msg = f"Failed to send {delivery_type} news via WhatsApp"
                self.logger.error(error_msg)

                # Send error notification
                await self.news_service.whatsapp_service.send_error_notification(error_msg)

        except Exception as e:
            error_msg = f"Error in {delivery_type} news delivery: {str(e)}"
            self.logger.error(error_msg, exc=e)

            # Send error notification via WhatsApp
            try:
                await self.news_service.whatsapp_service.send_error_notification(error_msg)
            except Exception as whatsapp_error:
                self.logger.error(f"Failed to send error notification via WhatsApp", exc=whatsapp_error)

    async def _count_articles_in_digest(self, digest: str) -> int:
        """Count approximate number of articles in a digest."""
        # Simple heuristic: count bullet points and numbered items
        lines = digest.split('\n')
        count = 0

        for line in lines:
            line = line.strip()
            # Count bullet points, numbered items, and category headers
            if (line.startswith('•') or
                line.startswith('-') or
                (line and line[0].isdigit() and '. ' in line) or
                line.endswith('News:*')):
                count += 1

        return max(count, 1)  # At least 1 if we have a digest

    async def trigger_manual_delivery(self, delivery_type: str) -> bool:
        """Manually trigger a news delivery (for testing)."""
        try:
            self.logger.info(f"Manual trigger for {delivery_type} news delivery")

            if delivery_type == "morning":
                await self._deliver_morning_news()
            elif delivery_type == "evening":
                await self._deliver_evening_news()
            else:
                self.logger.error(f"Invalid delivery type: {delivery_type}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error in manual {delivery_type} delivery", exc=e)
            return False

    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """Get the next scheduled run times for both deliveries."""
        try:
            morning_job = self.scheduler.get_job("morning_news")
            evening_job = self.scheduler.get_job("evening_news")

            return {
                "morning": morning_job.next_run_time if morning_job else None,
                "evening": evening_job.next_run_time if evening_job else None,
            }
        except Exception as e:
            self.logger.error(f"Error getting next run times", exc=e)
            return {"morning": None, "evening": None}

    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status."""
        try:
            if not self.scheduler or not self.news_service:
                return {
                    "is_running": False,
                    "error": "Scheduler not properly initialized",
                    "jobs": [],
                    "timezone": settings.DELIVERY_TIMEZONE,
                    "next_runs": {"morning": None, "evening": None}
                }

            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })

            return {
                "is_running": self.is_running,
                "jobs": jobs,
                "timezone": settings.DELIVERY_TIMEZONE,
                "next_runs": self.get_next_run_times()
            }
        except Exception as e:
            self.logger.error(f"Error getting scheduler status", exc=e)
            return {
                "is_running": False,
                "error": str(e)
            }