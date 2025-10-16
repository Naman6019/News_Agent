"""
RSS Feed Parser and Aggregator Service
Fetches and processes RSS feeds from multiple sources
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import StructuredLogger

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------
@dataclass
class Article:
    """Represents a news article from RSS feed."""

    title: str
    description: str
    link: str
    published_date: datetime
    source_url: str
    source_name: str
    category: str
    article_id: str = field(init=False)
    content: Optional[str] = None
    summary: Optional[str] = None

    def __post_init__(self):
        """Generate unique article ID."""
        content_for_hash = f"{self.title}{self.link}{self.published_date.isoformat()}"
        self.article_id = hashlib.md5(content_for_hash.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------
# Feed Parser
# ---------------------------------------------------------------------
class RSSFeedParser:
    """Service for parsing RSS feeds and extracting articles."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; NewsAgentBot/1.0; +https://newsagent.ai)"
        })
        self.timeout = getattr(settings, "RSS_FETCH_TIMEOUT", 15)

    async def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch RSS feed from URL with SSL-safe fallback.
        CNN and some other sources occasionally break TLS handshakes,
        so we use requests(verify=False) + feedparser fallback.
        """
        try:
            self.logger.info(f"Fetching RSS feed: {url}")

            def _fetch():
                # Ignore SSL verification to avoid EOF handshake bug
                return self.session.get(url, timeout=self.timeout, verify=False)

            response = await asyncio.get_event_loop().run_in_executor(None, _fetch)

            if response.status_code != 200:
                self.logger.warning(f"Feed fetch failed [{response.status_code}] for {url}")
                return None

            feed = await asyncio.get_event_loop().run_in_executor(
                None, lambda: feedparser.parse(response.content)
            )

            if feed.bozo:
                self.logger.warning(f"Feed parsing issue for {url}: {feed.bozo_exception}")
                return None

            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {url}")
                return None

            self.logger.info(f"Fetched {len(feed.entries)} entries from {url}")
            return feed

        except Exception as e:
            # fallback: use feedparser directly
            self.logger.error(f"Error fetching feed {url}, retrying with feedparser directly", exc=e)
            try:
                feed = await asyncio.get_event_loop().run_in_executor(None, lambda: feedparser.parse(url))
                if feed.entries:
                    self.logger.info(
                        f"Recovered {len(feed.entries)} entries via feedparser fallback for {url}"
                    )
                    return feed
            except Exception as e2:
                self.logger.error(f"Fallback also failed for {url}", exc=e2)
            return None

    async def extract_article_content(self, article_url: str) -> Optional[str]:
        """Extract full article content from the original article URL."""
        try:
            def _fetch_article():
                return self.session.get(article_url, timeout=self.timeout, verify=False)

            response = await asyncio.get_event_loop().run_in_executor(None, _fetch_article)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Try to find main content
            for selector in [
                "article",
                '[class*="content"]',
                '[class*="article"]',
                "main",
                ".post",
                ".entry-content",
            ]:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(strip=True)
                    if content:
                        return content[:2000]

            # Fallback to body text
            body = soup.find("body")
            if body:
                return body.get_text(strip=True)[:2000]

            return None

        except Exception as e:
            self.logger.error(f"Error extracting content from {article_url}", exc=e)
            return None

    def parse_article(self, entry: dict, source_url: str, category: str) -> Optional[Article]:
        """Parse a feed entry into an Article object."""
        try:
            title = entry.get("title", "").strip()
            if not title:
                return None

            description = entry.get("summary", entry.get("description", "")).strip()
            link = entry.get("link", "")
            if not link and hasattr(entry, "links") and entry.links:
                link = entry.links[0].get("href", "")

            if not link:
                return None

            # Parse published date
            if entry.get("published_parsed"):
                published_date = datetime(*entry.published_parsed[:6])
            elif entry.get("updated_parsed"):
                published_date = datetime(*entry.updated_parsed[:6])
            else:
                published_date = datetime.now()

            # Skip old articles (>36 hours)
            if published_date < datetime.now() - timedelta(hours=36):
                return None

            source_name = urlparse(source_url).netloc.replace("www.", "")

            return Article(
                title=title,
                description=description,
                link=link,
                published_date=published_date,
                source_url=source_url,
                source_name=source_name,
                category=category,
            )

        except Exception as e:
            self.logger.error(f"Error parsing article entry for {source_url}", exc=e)
            return None


# ---------------------------------------------------------------------
# News Aggregator
# ---------------------------------------------------------------------
class NewsAggregator:
    """Service for aggregating news from multiple RSS feeds."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.parser = RSSFeedParser()

    async def fetch_category_news(self, category: str) -> List[Article]:
        """Fetch news articles for one category."""
        if category not in settings.NEWS_CATEGORIES:
            self.logger.warning(f"Unknown category: {category}")
            return []

        feed_urls = settings.NEWS_CATEGORIES[category]
        self.logger.info(f"Fetching category '{category}' from {len(feed_urls)} feeds")

        all_articles = []
        for feed_url in feed_urls:
            articles = await self._fetch_feed_articles(feed_url, category)
            self.logger.info(f"{len(articles)} articles fetched from {feed_url}")
            all_articles.extend(articles)

        if not all_articles:
            self.logger.warning(f"No articles found in category: {category}")

        all_articles.sort(key=lambda x: x.published_date, reverse=True)
        return all_articles[:settings.RSS_MAX_ARTICLES_PER_FEED]

    async def _fetch_feed_articles(self, feed_url: str, category: str) -> List[Article]:
        """Fetch and parse all articles from one feed."""
        feed = await self.parser.fetch_feed(feed_url)
        if not feed:
            return []

        articles = []
        for entry in feed.entries:
            article = self.parser.parse_article(entry, feed_url, category)
            if article:
                articles.append(article)

        return articles

    async def fetch_all_news(self, categories: Optional[List[str]] = None) -> Dict[str, List[Article]]:
        """Fetch all categories concurrently."""
        categories = categories or list(settings.NEWS_CATEGORIES.keys())
        self.logger.info(f"Fetching all news for categories: {categories}")

        tasks = [self.fetch_category_news(cat) for cat in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news = {}
        for i, cat in enumerate(categories):
            if isinstance(results[i], Exception):
                self.logger.error(f"Error fetching category {cat}", exc=results[i])
                all_news[cat] = []
            else:
                all_news[cat] = results[i]

        total = sum(len(v) for v in all_news.values())
        self.logger.info(f"Total articles fetched: {total}")
        return all_news


# ---------------------------------------------------------------------
# Manual Test Runner
# ---------------------------------------------------------------------
if __name__ == "__main__":
    async def run_test():
        aggregator = NewsAggregator()
        all_news = await aggregator.fetch_all_news()
        print("\n==== Fetch Summary ====")
        for category, articles in all_news.items():
            print(f"{category:15} → {len(articles)} articles")
        print("========================\n")

    asyncio.run(run_test())
