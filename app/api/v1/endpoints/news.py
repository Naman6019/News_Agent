"""
News endpoints for manual operations and testing
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from app.core.config import settings
from app.services.news_service import NewsService
from app.services.rss_parser import Article

router = APIRouter()
news_service = NewsService()


@router.get("/digest")
async def get_news_digest(delivery_time: str = "morning"):
    """Generate and return a news digest manually."""
    try:
        if delivery_time not in ["morning", "evening"]:
            raise HTTPException(
                status_code=400,
                detail="delivery_time must be 'morning' or 'evening'"
            )

        digest = await news_service.generate_daily_digest(delivery_time)

        if not digest:
            raise HTTPException(
                status_code=404,
                detail="No news content available"
            )

        return {
            "digest": digest,
            "delivery_time": delivery_time,
            "timestamp": datetime.now().isoformat(),
            "categories": list(settings.NEWS_CATEGORIES.keys()),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating digest: {str(e)}")


@router.get("/categories")
async def get_news_by_category(category: str):
    """Get news articles for a specific category."""
    try:
        from app.services.rss_parser import NewsAggregator
        aggregator = NewsAggregator()

        articles = await aggregator.fetch_category_news(category)

        if not articles:
            raise HTTPException(
                status_code=404,
                detail=f"No articles found for category: {category}"
            )

        return {
            "category": category,
            "articles_count": len(articles),
            "articles": [
                {
                    "title": article.title,
                    "description": article.description,
                    "link": article.link,
                    "published_date": article.published_date.isoformat(),
                    "source_name": article.source_name,
                    "article_id": article.article_id,
                }
                for article in articles[:10]  # Limit to 10 articles
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching {category} news: {str(e)}")


@router.get("/categories/{category}/summary")
async def get_category_summary(category: str):
    """Get AI-generated summary for a specific category."""
    try:
        from app.services.rss_parser import NewsAggregator
        from app.services.summarizer import NewsSummarizer

        aggregator = NewsAggregator()
        summarizer = NewsSummarizer()

        # Fetch articles for the category
        articles = await aggregator.fetch_category_news(category)

        if not articles:
            raise HTTPException(
                status_code=404,
                detail=f"No articles found for category: {category}"
            )

        # Generate summary
        summary = await summarizer.summarize_articles_batch(articles, category)

        if not summary:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate summary for category: {category}"
            )

        return {
            "category": category,
            "summary": summary,
            "articles_count": len(articles),
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating {category} summary: {str(e)}")


@router.post("/test")
async def test_news_services():
    """Test all news services."""
    try:
        test_results = await news_service.test_services()

        return {
            "test_results": test_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing services: {str(e)}")


@router.get("/sources")
async def get_news_sources():
    """Get list of configured RSS feed sources."""
    return {
        "categories": settings.NEWS_CATEGORIES,
        "total_feeds": sum(len(feeds) for feeds in settings.NEWS_CATEGORIES.values()),
        "timestamp": datetime.now().isoformat(),
    }