"""
AI News Summarization Service
Uses Ollama (local LLM) to create concise news summaries
"""

import asyncio
import json
import re
import time
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

    # -------------------------------------------------------
    # Wait for Ollama backend readiness
    # -------------------------------------------------------
    def _wait_for_ollama_ready(self, retries: int = 12, delay: int = 5) -> bool:
        """Wait until Ollama /api/tags responds with a valid model list."""
        for attempt in range(retries):
            try:
                r = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if "models" in data and data["models"]:
                        self.logger.info("✅ Ollama backend is ready.")
                        return True
            except requests.RequestException:
                pass

            self.logger.info(f"⏳ Waiting for Ollama backend... ({attempt + 1}/{retries})")
            time.sleep(delay)

        self.logger.error("❌ Ollama backend not ready after waiting.")
        return False

    # -------------------------------------------------------
    # Core Ollama call with readiness check, retry + long timeout
    # -------------------------------------------------------
    def _call_ollama_api(self, prompt: str) -> Optional[str]:
        """Call Ollama API with retry, readiness check, and long timeout."""
        # Wait until backend responds
        if not self._wait_for_ollama_ready():
            return None

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

        for attempt in range(3):
            try:
                self.logger.debug(f"Ollama attempt {attempt + 1}/3 with model: {self.model}")
                response = requests.post(url, json=payload, timeout=60)

                if response.status_code != 200:
                    self.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    time.sleep(3)
                    continue

                result = response.json()
                raw_text = str(result)[:120].replace("\n", " ")
                self.logger.debug(f"Ollama raw response preview: {raw_text}")

                if "response" not in result:
                    self.logger.error(f"Invalid response from Ollama: {result}")
                    time.sleep(3)
                    continue

                return result["response"].strip()

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error calling Ollama API: {e}")
                if attempt < 2:
                    time.sleep(5)
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error calling Ollama API", exc=e)
                if attempt < 2:
                    time.sleep(5)
                continue

        self.logger.error("Ollama API failed after 3 attempts.")
        return None

    # -------------------------------------------------------
    # Prompt builders and summarization logic (unchanged)
    # -------------------------------------------------------
    def _create_summary_prompt(self, article: Article) -> str:
        content = article.content or article.description or ""
        if len(content) > 2000:
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
        articles_text = ""
        for i, article in enumerate(articles[:3], 1):
            content = article.content or article.description or ""
            if len(content) > 300:
                content = content[:300] + "..."
            articles_text += f"\n{i}. {article.title}\n   {content}\n"

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
        try:
            self.logger.info(f"Summarizing article: {article.title[:50]}...")
            prompt = self._create_summary_prompt(article)
            summary = await asyncio.get_event_loop().run_in_executor(None, self._call_ollama_api, prompt)
            if not summary:
                return None
            summary = self._clean_summary(summary)
            if len(summary) > settings.MAX_SUMMARY_LENGTH:
                summary = summary[:settings.MAX_SUMMARY_LENGTH - 3] + "..."
            self.logger.info(f"Generated summary: {summary[:50]}...")
            return summary
        except Exception as e:
            self.logger.error(f"Error summarizing article {article.title}", exc=e)
            return None

    async def summarize_articles_batch(self, articles: List[Article], category: str) -> Optional[str]:
        if not articles:
            return None
        try:
            self.logger.info(f"Creating batch summary for {len(articles)} {category} articles")
            prompt = self._create_batch_summary_prompt(articles, category)
            summary = await asyncio.get_event_loop().run_in_executor(None, self._call_ollama_api, prompt)
            if not summary:
                return None
            summary = self._clean_summary(summary)
            self.logger.info(f"Generated batch summary for {category}")
            return summary
        except Exception as e:
            self.logger.error(f"Error creating batch summary for {category}", exc=e)
            return None

    def _clean_summary(self, summary: str) -> str:
        summary = re.sub(r'^(Summary:|Here\'s a summary:|In summary:|News Digest:)', '', summary, flags=re.IGNORECASE)
        summary = summary.strip('"\'"')
        summary = re.sub(r'\s+', ' ', summary)
        if summary and summary[0].islower():
            summary = summary[0].upper() + summary[1:]
        return summary.strip()

    async def summarize_all_articles(self, articles_by_category: dict) -> dict:
        self.logger.info("Starting summarization of all articles")
        summary_tasks = []
        for category, articles in articles_by_category.items():
            if not articles:
                continue
            task = self.summarize_articles_batch(articles, category)
            summary_tasks.append((category, task))
        results = await asyncio.gather(*[task for _, task in summary_tasks], return_exceptions=True)
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
        self.logger.info(f"Generating {delivery_time} news digest")
        current_date = datetime.datetime.now().strftime('%d/%m/%Y')
        greeting = "Good morning" if delivery_time.lower() == "morning" else "Good evening"
        summaries = await self.summarize_all_articles(articles_by_category)

        digest_parts = [f"📰 *{greeting}! Here's your {delivery_time.title()} News Digest*", f"📅 {current_date}", ""]
        for category in settings.NEWS_CATEGORIES.keys():
            if category in summaries and summaries[category]:
                digest_parts.append(f"*{category.title()} News:*")
                digest_parts.append(summaries[category])
                if articles_with_links and category in articles_with_links:
                    source_links = []
                    for article in articles_with_links[category][:2]:
                        source_links.append(f"🔗 {article.source_name}: {article.link}")
                    if source_links:
                        digest_parts.append("*Sources:*")
                        digest_parts.extend(source_links)
                        digest_parts.append("")
        digest_parts.append("_Powered by Ollama & AI News Agent_")
        full_digest = "\n".join(digest_parts)
        if len(full_digest) > 4000:
            full_digest = full_digest[:3997] + "..."
        return full_digest

    def test_ollama_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                self.logger.error(f"Ollama not accessible: {response.status_code}")
                return False
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