"""
News Service - Main orchestration service
Coordinates RSS parsing, summarization, and WhatsApp delivery
"""

from typing import Dict, List, Optional

from app.core.logging import StructuredLogger
from app.services.rss_parser import NewsAggregator, Article
from app.services.summarizer import NewsSummarizer
from app.services.whatsapp import WhatsAppService


class NewsService:
    """Main service for orchestrating news operations."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.aggregator = NewsAggregator()
        self.summarizer = NewsSummarizer()
        self.whatsapp_service = WhatsAppService()

    async def generate_daily_digest(self, delivery_time: str = "morning") -> Optional[str]:
        """Generate a complete daily news digest."""
        try:
            self.logger.info(f"Generating {delivery_time} news digest")

            # Fetch news from all categories
            articles_by_category = await self.aggregator.fetch_all_news()

            # Filter out empty categories
            articles_by_category = {
                category: articles
                for category, articles in articles_by_category.items()
                if articles
            }

            if not articles_by_category:
                self.logger.warning("No articles found for daily digest")
                return None

            # Prepare articles with their links for source attribution
            articles_with_links = articles_by_category.copy()

            # Generate the digest with enhanced formatting
            digest = await self.summarizer.generate_daily_digest(
                articles_by_category,
                delivery_time,
                articles_with_links
            )

            self.logger.info(f"{delivery_time.title()} news digest generated successfully")
            return digest

        except Exception as e:
            self.logger.error(f"Error generating {delivery_time} digest", exc=e)
            return None

    async def test_services(self) -> Dict[str, bool]:
        """Test all services to ensure they're working."""
        self.logger.info("Testing all news services")

        test_results = {}

        try:
            # Test RSS aggregator
            test_results["rss_aggregator"] = await self._test_rss_aggregator()

            # Test summarizer (requires RSS data)
            test_results["summarizer"] = await self._test_summarizer()

            # Test WhatsApp service
            test_results["whatsapp"] = await self.whatsapp_service.send_test_message()

            # Overall success
            test_results["overall"] = all(test_results.values())

            self.logger.info(f"Service tests completed: {test_results}")
            return test_results

        except Exception as e:
            self.logger.error(f"Error testing services", exc=e)
            return {"error": str(e)}

    async def _test_rss_aggregator(self) -> bool:
        """Test RSS aggregator service."""
        try:
            # Try to fetch from just one category for testing
            articles = await self.aggregator.fetch_category_news("technology")
            return len(articles) > 0
        except Exception:
            return False

    async def _test_summarizer(self) -> bool:
        """Test summarizer service."""
        try:
            # Fetch some articles and try to summarize them
            articles = await self.aggregator.fetch_category_news("technology")
            if not articles:
                return False

            # Try to summarize the first article
            summary = await self.summarizer.summarize_article(articles[0])
            return summary is not None and len(summary) > 0
        except Exception:
            return False

    async def get_service_status(self) -> Dict:
        """Get status of all services."""
        # Test Ollama connection
        ollama_healthy = self.summarizer.test_ollama_connection()

        return {
            "rss_aggregator": "healthy",
            "summarizer": "healthy" if ollama_healthy else "ollama_unavailable",
            "whatsapp_service": "healthy",
            "ollama_connection": "connected" if ollama_healthy else "disconnected",
            "phone_validation": self.whatsapp_service.validate_phone_numbers(),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }