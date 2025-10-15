"""
AI News Summarization Service
Uses Ollama (local LLM) to create concise news summaries
"""

import asyncio
import json
import re
from typing import List, Optional
import datetime

import requests

from app.core.config import settings
from app.core.logging import StructuredLogger
from app.services.rss_parser import Article


class NewsSummarizer:
    """Service for summarizing news articles using Ollama (local LLM)."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.max_tokens = settings.OLLAMA_MAX_TOKENS
        self.temperature = settings.OLLAMA_TEMPERATURE

    def _call_ollama_api(self, prompt: str) -> Optional[str]:
        """Call Ollama API with a prompt."""
        try:
            url = f"{self.base_url}/api/generate"

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }

            self.logger.debug(f"Calling Ollama API with model: {self.model}")

            response = requests.post(url, json=payload, timeout=60)

            if response.status_code != 200:
                self.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None

            result = response.json()

            if "response" not in result:
                self.logger.error(f"Invalid response from Ollama: {result}")
                return None

            return result["response"].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error calling Ollama API: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error calling Ollama API", exc=e)
            return None

    def _create_summary_prompt(self, article: Article) -> str:
        """Create a prompt for summarizing a news article."""
        # Use full content if available, otherwise use description
        content = article.content or article.description or ""

        # Truncate content to fit within reasonable limits
        if len(content) > 2000:  # Limit content length
            content = content[:2000] + "..."

        prompt = f"""You are a professional news summarizer. Create a concise, engaging summary suitable for WhatsApp messaging.

Article Details:
- Title: {article.title}
- Source: {article.source_name}
- Category: {article.category.title()}

Content:
{content}

Requirements:
- Focus on key facts and main events
- Keep under {settings.MAX_SUMMARY_LENGTH} characters
- Make it engaging and easy to read
- Start directly with the summary (no prefixes)

Summary:"""

        return prompt.strip()

    def _create_batch_summary_prompt(self, articles: List[Article], category: str) -> str:
        """Create a prompt for summarizing multiple articles from the same category."""
        articles_text = ""
        for i, article in enumerate(articles[:3], 1):  # Limit to 3 articles for batch summary
            content = article.content or article.description or ""
            if len(content) > 300:  # Shorter for batch
                content = content[:300] + "..."

            articles_text += f"""
{i}. {article.title}
   {content}
"""

        prompt = f"""You are a professional news curator. Create a concise news digest for the {category.title()} category.

Articles to summarize:
{articles_text}

Requirements:
- Summarize the top {min(len(articles), 3)} stories
- Use bullet points for each story
- Focus on key facts only
- Keep each summary under {settings.MAX_SUMMARY_LENGTH // 2} characters
- Make it engaging and suitable for WhatsApp messaging
- Start directly with the bullet points (no prefixes)

News Digest:"""

        return prompt.strip()

    async def summarize_article(self, article: Article) -> Optional[str]:
        """Summarize a single news article."""
        try:
            self.logger.info(f"Summarizing article: {article.title[:50]}...")

            prompt = self._create_summary_prompt(article)

            # Run Ollama API call in executor to avoid blocking
            summary = await asyncio.get_event_loop().run_in_executor(
                None, self._call_ollama_api, prompt
            )

            if not summary:
                return None

            # Clean up the summary
            summary = self._clean_summary(summary)

            # Ensure summary isn't too long
            if len(summary) > settings.MAX_SUMMARY_LENGTH:
                summary = summary[:settings.MAX_SUMMARY_LENGTH - 3] + "..."

            self.logger.info(f"Generated summary: {summary[:50]}...")
            return summary

        except Exception as e:
            self.logger.error(f"Error summarizing article {article.title}", exc=e)
            return None

    async def summarize_articles_batch(self, articles: List[Article], category: str) -> Optional[str]:
        """Create a batch summary for multiple articles from the same category."""
        if not articles:
            return None

        try:
            self.logger.info(f"Creating batch summary for {len(articles)} {category} articles")

            prompt = self._create_batch_summary_prompt(articles, category)

            # Run Ollama API call in executor to avoid blocking
            summary = await asyncio.get_event_loop().run_in_executor(
                None, self._call_ollama_api, prompt
            )

            if not summary:
                return None

            # Clean up the summary
            summary = self._clean_summary(summary)

            self.logger.info(f"Generated batch summary for {category}")
            return summary

        except Exception as e:
            self.logger.error(f"Error creating batch summary for {category}", exc=e)
            return None

    def _clean_summary(self, summary: str) -> str:
        """Clean up AI-generated summary."""
        # Remove common AI prefixes
        summary = re.sub(r'^(Summary:|Here\'s a summary:|In summary:|News Digest:)', '', summary, flags=re.IGNORECASE)

        # Remove extra quotes
        summary = summary.strip('"\'"')

        # Remove excessive whitespace
        summary = re.sub(r'\s+', ' ', summary)

        # Ensure it starts with a capital letter
        if summary and summary[0].islower():
            summary = summary[0].upper() + summary[1:]

        return summary.strip()

    async def summarize_all_articles(self, articles_by_category: dict) -> dict:
        """Summarize all articles organized by category."""
        self.logger.info("Starting summarization of all articles")

        summary_tasks = []

        for category, articles in articles_by_category.items():
            if not articles:
                continue

            # For each category, create a batch summary
            task = self.summarize_articles_batch(articles, category)
            summary_tasks.append((category, task))

        # Execute all summarization tasks concurrently
        results = await asyncio.gather(*[task for _, task in summary_tasks], return_exceptions=True)

        # Process results
        summaries = {}
        for i, (category, _) in enumerate(summary_tasks):
            if isinstance(results[i], Exception):
                self.logger.error(f"Error summarizing {category}", exc=results[i])
                summaries[category] = None
            else:
                summaries[category] = results[i]

        self.logger.info(f"Completed summarization for {len([s for s in summaries.values() if s])} categories")
        return summaries

    async def generate_daily_digest(self, articles_by_category: dict, delivery_time: str = "morning", articles_with_links: dict = None) -> str:
        """Generate a complete daily news digest for WhatsApp."""
        self.logger.info(f"Generating {delivery_time} news digest")

        # Get current date in DD/MM/YYYY format
        current_date = datetime.datetime.now().strftime('%d/%m/%Y')

        # Determine greeting based on time
        greeting = "Good morning" if delivery_time.lower() == "morning" else "Good evening"

        # Get summaries for all categories
        summaries = await self.summarize_all_articles(articles_by_category)

        # Build the digest message
        digest_parts = []
        digest_parts.append(f"📰 *{greeting}! Here's your {delivery_time.title()} News Digest*")
        digest_parts.append(f"📅 {current_date}")
        digest_parts.append("")

        # Add summaries for each category that has content
        for category in settings.NEWS_CATEGORIES.keys():
            if category in summaries and summaries[category]:
                digest_parts.append(f"*{category.title()} News:*")
                digest_parts.append(summaries[category])

                # Add source links if available
                if articles_with_links and category in articles_with_links:
                    source_links = []
                    for article in articles_with_links[category][:2]:  # Limit to 2 sources per category
                        source_links.append(f"🔗 {article.source_name}: {article.link}")
                    if source_links:
                        digest_parts.append("*Sources:*")
                        digest_parts.extend(source_links)
                        digest_parts.append("")

        # Add footer
        digest_parts.append("_Powered by Ollama & AI News Agent_")

        full_digest = "\n".join(digest_parts)

        # Ensure total length is reasonable for WhatsApp
        if len(full_digest) > 4000:  # WhatsApp message limit
            # Truncate if too long
            full_digest = full_digest[:3997] + "..."

        return full_digest

    def test_ollama_connection(self) -> bool:
        """Test if Ollama is running and the model is available."""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)

            if response.status_code != 200:
                self.logger.error(f"Ollama not accessible: {response.status_code}")
                return False

            # Check if the model is available
            models = response.json().get("models", [])
            model_names = [model.get("name") for model in models]

            if self.model not in model_names:
                self.logger.error(f"Model {self.model} not found in Ollama. Available models: {model_names}")
                return False

            self.logger.info(f"Ollama connection successful. Model {self.model} is available.")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error connecting to Ollama: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error testing Ollama connection", exc=e)
            return False