#!/usr/bin/env python3
"""
URL Fetcher Agent

Fetches content from URLs and summarizes them using LM Studio.
"""

import re
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, Any
import sys
import os

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from config import LM_STUDIO_URL, LM_STUDIO_MODEL, MAX_CONTENT_LENGTH, REQUEST_TIMEOUT, SUMMARY_MAX_TOKENS, SUMMARY_TEMPERATURE

logger = logging.getLogger(__name__)


class URLFetcherAgent(BaseAgent):
    """Agent that fetches and summarizes web content."""

    def get_name(self) -> str:
        return "url_fetcher"

    def get_description(self) -> str:
        return "Fetches content from URLs and provides summaries"

    def get_trigger_patterns(self) -> list:
        return [
            r'https?://[^\s<>"{}|\\^`\[\]]+',  # Any URL
            r'summarize.*https?://',
            r'fetch.*https?://',
        ]

    def get_usage_example(self) -> str:
        return "Please summarize https://example.com/article"

    def can_handle(self, message: str) -> bool:
        """Check if message contains a URL."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return bool(re.search(url_pattern, message))

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """Fetch URL and return summary."""
        # Extract URL
        url = self._extract_url(message)
        if not url:
            return "I couldn't find a valid URL in your message. Please provide a URL like: https://example.com/article"

        logger.info(f"URL Fetcher Agent: Processing URL: {url}")

        # Fetch content
        content = self._fetch_website_content(url)

        # Summarize
        summary = self._summarize_with_lm_studio(content)

        return f"Summary of {url}:\n\n{summary}"

    def _extract_url(self, text: str) -> str:
        """Extract URL from text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls[0] if urls else None

    def _fetch_website_content(self, url: str) -> str:
        """Fetch and extract text content from a URL."""
        try:
            logger.info(f"Fetching URL: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            # Parse HTML and extract text
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            # Limit to avoid token limits
            if len(text) > MAX_CONTENT_LENGTH:
                text = text[:MAX_CONTENT_LENGTH] + "...\n[Content truncated]"

            return text
        except Exception as e:
            logger.error(f"Error fetching URL: {e}")
            return f"Error fetching URL: {str(e)}"

    def _summarize_with_lm_studio(self, content: str) -> str:
        """Send content to LM Studio for summarization."""
        try:
            prompt = f"Please provide a concise summary of the following content:\n\n{content}"

            payload = {
                "model": LM_STUDIO_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise, informative summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": SUMMARY_TEMPERATURE,
                "max_tokens": SUMMARY_MAX_TOKENS
            }

            logger.info("Sending to LM Studio for summarization...")
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            summary = result['choices'][0]['message']['content']
            return summary
        except Exception as e:
            logger.error(f"Error calling LM Studio: {e}")
            return f"Error generating summary: {str(e)}"
