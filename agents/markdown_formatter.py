#!/usr/bin/env python3
"""
Markdown Formatter Agent

Formats plain text or structured data into well-formatted Markdown.

Usage:
    format_markdown: Convert this text to markdown
    markdown: Make this a bulleted list
"""

import re
import requests
import logging
from typing import Dict, Any
import sys
import os

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from config import (
    LM_STUDIO_URL,
    LM_STUDIO_MODEL,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


class MarkdownFormatterAgent(BaseAgent):
    """Agent that formats text into well-structured Markdown."""

    def get_name(self) -> str:
        return "markdown_formatter"

    def get_description(self) -> str:
        return "Formats text and data into well-structured Markdown with proper headings, lists, tables, and code blocks"

    def get_trigger_patterns(self) -> list:
        return [
            r'format_markdown:',
            r'markdown:',
            r'to markdown',
            r'as markdown',
            r'convert to markdown',
        ]

    def get_usage_example(self) -> str:
        return "format_markdown: Convert this data into a nice table"

    def can_handle(self, message: str) -> bool:
        """Check if message is a markdown formatting request."""
        message_lower = message.lower()

        # Check for explicit triggers
        if 'format_markdown:' in message_lower or 'markdown:' in message_lower:
            return True

        # Check for conversion patterns
        if 'to markdown' in message_lower or 'as markdown' in message_lower:
            return True

        if 'convert to markdown' in message_lower:
            return True

        # Check for natural language formatting requests
        if 'format' in message_lower and 'markdown' in message_lower:
            return True

        if 'beautify' in message_lower and 'markdown' in message_lower:
            return True

        if 'clean up' in message_lower and ('markdown' in message_lower or 'md' in message_lower):
            return True

        return False

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """Process markdown formatting request using LLM."""
        logger.info(f"Markdown Formatter Agent: Processing request")

        # Extract the content to format
        content = self._extract_content(message)

        if not content:
            return (
                "Please provide content to format. Examples:\n"
                "  format_markdown: Here is my content...\n"
                "  markdown: Convert this to a table: Name, Age, City..."
            )

        logger.info(f"Formatting {len(content)} characters to markdown")

        # Use LLM to format the content
        formatted_markdown = self._format_with_llm(content)

        return formatted_markdown

    def _extract_content(self, message: str) -> str:
        """Extract the content to be formatted from the message."""
        # Remove the trigger patterns
        content = message

        # Remove format_markdown: prefix
        content = re.sub(r'format_markdown:\s*', '', content, flags=re.IGNORECASE)

        # Remove markdown: prefix
        content = re.sub(r'markdown:\s*', '', content, flags=re.IGNORECASE)

        # Remove conversion phrases
        content = re.sub(r'convert to markdown:\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'to markdown:\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'as markdown:\s*', '', content, flags=re.IGNORECASE)

        return content.strip()

    def _format_with_llm(self, content: str) -> str:
        """Use LLM to format content as Markdown."""
        try:
            prompt = f"""You are a markdown formatting expert. Format the following content into well-structured Markdown.

Content to format:
{content}

Instructions:
- Use appropriate Markdown syntax (headings, lists, tables, code blocks, bold, italic, etc.)
- Make it well-organized and easy to read
- Use proper hierarchy with headings (# ## ###)
- Create tables for tabular data
- Use code blocks for code or technical content
- Use bullet points or numbered lists where appropriate
- Make it visually appealing and well-formatted
- Return ONLY the formatted markdown, no explanations

Formatted Markdown:"""

            payload = {
                "model": LM_STUDIO_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a markdown formatting expert. Always respond with properly formatted Markdown syntax only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower for consistent formatting
                "max_tokens": 2000
            }

            logger.info("Calling LLM to format markdown...")
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            markdown_output = result['choices'][0]['message']['content']

            logger.info(f"Successfully formatted to markdown: {len(markdown_output)} characters")

            # Clean up the output
            markdown_output = markdown_output.strip()

            # Remove markdown code block markers if LLM added them
            if markdown_output.startswith('```markdown'):
                markdown_output = re.sub(r'^```markdown\s*', '', markdown_output)
                markdown_output = re.sub(r'\s*```$', '', markdown_output)
                markdown_output = markdown_output.strip()
            elif markdown_output.startswith('```'):
                markdown_output = re.sub(r'^```\s*', '', markdown_output)
                markdown_output = re.sub(r'\s*```$', '', markdown_output)
                markdown_output = markdown_output.strip()

            return markdown_output

        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            return f"Error: Request to LLM timed out. Please try again."
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling LLM: {e}")
            return f"Error formatting markdown: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"Error: {str(e)}"
