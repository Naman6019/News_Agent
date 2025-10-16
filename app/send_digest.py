"""
send_digest.py — Manual or scheduled digest trigger.
Can be run locally or by Render cron every X hours.
"""

import asyncio
from datetime import datetime
import pytz

from app.services.news_service import NewsService
from app.core.logging import StructuredLogger

logger = StructuredLogger(__name__)
IST = pytz.timezone("Asia/Calcutta")


async def main():
    now = datetime.now(IST)
    # Determine which digest to send based on time
    if 5 <= now.hour < 12:
        delivery_time = "morning"
    elif 17 <= now.hour < 22:
        delivery_time = "evening"
    else:
        logger.info("Outside delivery window, skipping digest send.")
        return

    logger.info(f"Running {delivery_time} digest send at {now.strftime('%H:%M %p')}")
    service = NewsService()
    await service.process_and_send_news(delivery_time)


if __name__ == "__main__":
    asyncio.run(main())
