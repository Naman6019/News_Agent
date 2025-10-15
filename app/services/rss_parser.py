"""
RSS Feed Parser and Aggregator Service
Fetches and processes RSS feeds from multiple sources
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import StructuredLogger


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


class RSSFeedParser:
    """Service for parsing RSS feeds and extracting articles."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.session = requests.Session()
        self.session.timeout = settings.RSS_FETCH_TIMEOUT

    async def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch RSS feed from URL with error handling."""
        try:
            self.logger.info(f"Fetching RSS feed: {url}")
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.session.get(url)
            )

            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch feed {url}: HTTP {response.status_code}")
                return None

            # Parse the feed
            feed = await asyncio.get_event_loop().run_in_executor(
                None, lambda: feedparser.parse(response.content)
            )

            if feed.bozo:
                self.logger.warning(f"Error parsing feed {url}: {feed.bozo_exception}")
                return None

            return feed

        except Exception as e:
            self.logger.error(f"Error fetching feed {url}", exc=e)
            return None

    async def extract_article_content(self, article_url: str) -> Optional[str]:
        """Extract full article content from URL."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.session.get(article_url)
            )

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Try to find the main content
            content_selectors = [
                'article',
                '[class*="content"]',
                '[class*="article"]',
                'main',
                '.post',
                '.entry-content'
            ]

            content = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content = content_element.get_text(strip=True)
                    break

            # Fallback to body text if no specific content found
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text(strip=True)

            return content[:2000] if content else None  # Limit content length

        except Exception as e:
            self.logger.error(f"Error extracting content from {article_url}", exc=e)
            return None

    def parse_article(self, entry: dict, source_url: str, category: str) -> Optional[Article]:
        """Parse RSS entry into Article object."""
        try:
            # Extract title
            title = entry.get('title', '').strip()
            if not title:
                return None

            # Extract description/summary
            description = ""
            if entry.get('summary'):
                description = entry.summary.strip()
            elif entry.get('description'):
                description = entry.description.strip()

            # Extract link
            link = entry.get('link', '')
            if not link and hasattr(entry, 'links') and entry.links:
                link = entry.links[0].get('href', '')

            if not link:
                return None

            # Parse publication date
            published_date = None
            if entry.get('published_parsed'):
                published_date = datetime(*entry.published_parsed[:6])
            elif entry.get('updated_parsed'):
                published_date = datetime(*entry.updated_parsed[:6])
            else:
                # Use current time if no date available
                published_date = datetime.now()

            # Skip articles older than 24 hours
            if published_date < datetime.now() - timedelta(hours=24):
                return None

            # Extract source name from URL
            parsed_url = urlparse(source_url)
            source_name = parsed_url.netloc.replace('www.', '')

            return Article(
                title=title,
                description=description,
                link=link,
                published_date=published_date,
                source_url=source_url,
                source_name=source_name,
                category=category
            )

        except Exception as e:
            self.logger.error(f"Error parsing article entry", exc=e)
            return None


class NewsAggregator:
    """Service for aggregating news from multiple RSS feeds."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.parser = RSSFeedParser()

    async def fetch_category_news(self, category: str) -> List[Article]:
        """Fetch news articles for a specific category."""
        if category not in settings.NEWS_CATEGORIES:
            self.logger.warning(f"Unknown category: {category}")
            return []

        feed_urls = settings.NEWS_CATEGORIES[category]
        self.logger.info(f"Fetching news for category: {category}")

        all_articles = []

        # Fetch from all feeds in the category
        for feed_url in feed_urls:
            feed_articles = await self._fetch_feed_articles(feed_url, category)
            all_articles.extend(feed_articles)

        # Sort by publication date (newest first) and limit
        all_articles.sort(key=lambda x: x.published_date, reverse=True)
        limited_articles = all_articles[:settings.RSS_MAX_ARTICLES_PER_FEED]

        self.logger.info(f"Fetched {len(limited_articles)} articles for category {category}")
        return limited_articles

    async def _fetch_feed_articles(self, feed_url: str, category: str) -> List[Article]:
        """Fetch articles from a single RSS feed."""
        articles = []

        # Fetch the feed
        feed = await self.parser.fetch_feed(feed_url)
        if not feed:
            return articles

        # Parse articles from feed
        for entry in feed.entries:
            article = self.parser.parse_article(entry, feed_url, category)
            if article:
                articles.append(article)

        return articles

    async def fetch_all_news(self, categories: Optional[List[str]] = None) -> Dict[str, List[Article]]:
        """Fetch news from all categories or specified categories."""
        if categories is None:
            categories = list(settings.NEWS_CATEGORIES.keys())

        self.logger.info(f"Fetching news for categories: {categories}")

        # Fetch news for all categories concurrently
        tasks = [self.fetch_category_news(category) for category in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        all_news = {}
        for i, category in enumerate(categories):
            if isinstance(results[i], Exception):
                self.logger.error(f"Error fetching {category} news", exc=results[i])
                all_news[category] = []
            else:
                all_news[category] = results[i]

        total_articles = sum(len(articles) for articles in all_news.values())
        self.logger.info(f"Fetched total of {total_articles} articles")

        return all_news

    async def enrich_articles_with_content(self, articles: List[Article]) -> List[Article]:
        """Enrich articles with full content for better summarization."""
        self.logger.info(f"Enriching {len(articles)} articles with content")

        # Limit concurrent requests to avoid overwhelming servers
        semaphore = asyncio.Semaphore(5)

        async def enrich_single_article(article: Article) -> Article:
            async with semaphore:
                content = await self.parser.extract_article_content(article.link)
                if content:
                    article.content = content
                return article

        # Enrich articles concurrently
        tasks = [enrich_single_article(article) for article in articles]
        enriched_articles = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any that failed and return successful ones
        successful_articles = []
        for i, result in enumerate(enriched_articles):
            if isinstance(result, Exception):
                self.logger.error(f"Error enriching article {articles[i].title}", exc=result)
                successful_articles.append(articles[i])  # Keep original article
            else:
                successful_articles.append(result)

        return successful_articles