"""
News Service — Fetches, summarizes, and sends news digests based on delivery time.
Supports time-window filtering (morning/evening) and deduplication.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
import pytz

from app.services.rss_parser import NewsAggregator
from app.services.summarizer import Summarizer
from app.services.whatsapp import WhatsAppService
from app.core.config import settings
from app.core.logging import StructuredLogger

SENT_ARTICLES_FILE = "data/sent_articles.json"
IST = pytz.timezone("Asia/Calcutta")


class NewsService:
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.aggregator = NewsAggregator()
        self.summarizer = Summarizer()
        self.whatsapp = WhatsAppService()

    # ----------------------------- #
    #  TIME WINDOW CALCULATION
    # ----------------------------- #
    def get_time_window(self, delivery_time: str):
        """Determine start and end time for news fetching."""
        now = datetime.now(IST)
        if delivery_time == "morning":
            # News from previous evening → morning
            start = (now - timedelta(hours=12)).replace(minute=0, second=0)
        elif delivery_time == "evening":
            # News from morning → evening
            start = (now - timedelta(hours=12)).replace(minute=0, second=0)
        else:
            start = now - timedelta(hours=24)
        return start, now

    # ----------------------------- #
    #  SENT ARTICLES TRACKING
    # ----------------------------- #
    def _load_sent_articles(self):
        if not os.path.exists(SENT_ARTICLES_FILE):
            return set()
        try:
            with open(SENT_ARTICLES_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()

    def _save_sent_articles(self, article_ids):
        try:
            existing = self._load_sent_articles()
            all_ids = list(set(existing.union(article_ids)))
            os.makedirs(os.path.dirname(SENT_ARTICLES_FILE), exist_ok=True)
            with open(SENT_ARTICLES_FILE, "w") as f:
                json.dump(all_ids, f)
        except Exception as e:
            self.logger.error("Error saving sent article IDs", exc=e)

    def _filter_unsent(self, articles):
        sent = self._load_sent_articles()
        filtered = [a for a in articles if a.article_id not in sent]
        self.logger.info(f"Filtered {len(articles) - len(filtered)} already-sent articles")
        return filtered

    # ----------------------------- #
    #  MAIN DIGEST GENERATION
    # ----------------------------- #
    async def generate_digest(self, delivery_time: str):
        """Fetch, summarize, and format digest."""
        start_time, end_time = self.get_time_window(delivery_time)
        self.logger.info(f"Fetching {delivery_time} news from {start_time} → {end_time}")

        all_news = await self.aggregator.fetch_all_news_since(start_time)
        all_articles = [article for cat in all_news.values() for article in cat]
        all_articles = self._filter_unsent(all_articles)

        if not all_articles:
            self.logger.warning("No new articles found in this time window.")
            return "No new articles found."

        # Summarize concurrently
        summaries = await asyncio.gather(
            *[self.summarizer.summarize_article(article) for article in all_articles]
        )

        for article, summary in zip(all_articles, summaries):
            article.summary = summary or article.description

        # Save sent IDs
        self._save_sent_articles([a.article_id for a in all_articles])

        # Format digest message
        return self._format_digest_message(all_articles, delivery_time)

    # ----------------------------- #
    #  DIGEST MESSAGE FORMATTING
    # ----------------------------- #
    def _format_digest_message(self, articles, delivery_time):
        """Create formatted WhatsApp digest message."""
        date_str = datetime.now(IST).strftime("%d/%m/%Y")
        greeting = "Good morning" if delivery_time == "morning" else "Good evening"
        header = f"📰 {greeting}! Here's your {delivery_time.capitalize()} News Digest\n📅 {date_str}\n\n"

        message = header
        for i, a in enumerate(articles[:settings.RSS_MAX_ARTICLES_PER_FEED], 1):
            summary = (a.summary[:settings.MAX_SUMMARY_LENGTH] + "...") if a.summary else a.description[:150]
            message += f"{i}. *{a.title.strip()}*\n_{summary.strip()}_\n🔗 {a.link}\n\n"

        message += "_Powered by Gemma 3 & AI News Agent_"
        return message

    # ----------------------------- #
    #  SEND DIGEST VIA WHATSAPP
    # ----------------------------- #
    async def process_and_send_news(self, delivery_time: str):
        """Generate and send digest."""
        message = await self.generate_digest(delivery_time)
        if "No new articles" in message:
            self.logger.info("Skipping send — no new articles.")
            return
        await self.whatsapp.send_message(message)
        self.logger.info(f"{delivery_time.capitalize()} digest sent successfully.")
