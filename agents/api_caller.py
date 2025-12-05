#!/usr/bin/env python3
"""
API Caller Agent

Intelligently calls APIs by reading their documentation and forming requests based on human language.

Usage:
    api_call: docs=https://api.example.com/docs endpoint=https://api.example.com Get the list of users
    api_call: docs=https://stripe.com/docs/api Create a new customer with email test@example.com
"""

import re
import requests
import json
from bs4 import BeautifulSoup
import logging
from typing import Dict, Any, Optional, Tuple
import sys
import os

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from config import (
    LM_STUDIO_URL,
    LM_STUDIO_MODEL,
    MAX_CONTENT_LENGTH,
    REQUEST_TIMEOUT,
    SUMMARY_MAX_TOKENS,
    SUMMARY_TEMPERATURE
)

logger = logging.getLogger(__name__)


class APICallerAgent(BaseAgent):
    """Agent that calls APIs intelligently using LLM to parse documentation."""

    def get_name(self) -> str:
        return "api_caller"

    def get_description(self) -> str:
        return "Calls APIs by reading documentation and forming requests from natural language"

    def get_trigger_patterns(self) -> list:
        return [
            r'api_call:',
            r'call api',
            r'api request',
            r'docs=https?://',
        ]

    def get_usage_example(self) -> str:
        return "api_call: docs=https://api.example.com/docs endpoint=https://api.example.com Get all users"

    def can_handle(self, message: str) -> bool:
        """Check if message is an API call request."""
        # Check for api_call: prefix
        if 'api_call:' in message.lower():
            return True

        # Check for docs= pattern
        if re.search(r'docs=https?://', message, re.IGNORECASE):
            return True

        return False

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """Process API call request."""
        logger.info(f"API Caller Agent: Processing request")

        # Extract components from message
        docs_url, api_base_url, request_text = self._extract_request_components(message)

        if not docs_url:
            return (
                "I need the API documentation URL. Format:\n"
                "api_call: docs=https://api.example.com/docs endpoint=https://api.example.com Your request here\n\n"
                "Or:\n"
                "api_call: docs=https://api.example.com/docs Get all users (I'll try to find the API endpoint)"
            )

        if not request_text:
            return "Please specify what you want to do with the API (e.g., 'Get all users', 'Create a new customer')"

        logger.info(f"Docs URL: {docs_url}")
        logger.info(f"API Base URL: {api_base_url or 'Will extract from docs'}")
        logger.info(f"Request: {request_text}")

        # Step 1: Fetch documentation
        logger.info("Step 1: Fetching API documentation...")
        docs_content = self._fetch_documentation(docs_url)
        if docs_content.startswith("Error"):
            return docs_content

        # Step 2: Use LLM to understand the request and form API call
        logger.info("Step 2: Using LLM to parse documentation and form API call...")
        api_call_info = self._form_api_call_with_llm(
            docs_content,
            request_text,
            api_base_url
        )

        if not api_call_info or 'error' in api_call_info:
            return f"Error forming API call: {api_call_info.get('error', 'Unknown error')}"

        # Step 3: Execute the API call
        logger.info("Step 3: Executing API call...")
        logger.info(f"  Method: {api_call_info.get('method')}")
        logger.info(f"  URL: {api_call_info.get('url')}")

        result = self._execute_api_call(api_call_info)

        # Step 4: Format and return response
        return self._format_response(api_call_info, result)

    def _extract_request_components(self, message: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract docs URL, API base URL, and request text from message.

        Returns:
            (docs_url, api_base_url, request_text)
        """
        docs_url = None
        api_base_url = None
        request_text = None

        # Extract docs URL
        docs_match = re.search(r'docs=(https?://[^\s]+)', message, re.IGNORECASE)
        if docs_match:
            docs_url = docs_match.group(1)

        # Extract endpoint/API base URL
        endpoint_match = re.search(r'endpoint=(https?://[^\s]+)', message, re.IGNORECASE)
        if endpoint_match:
            api_base_url = endpoint_match.group(1)

        # Extract request text (everything after the URLs)
        # Remove the api_call: prefix and URL parameters
        text = message
        text = re.sub(r'api_call:\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'docs=https?://[^\s]+\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'endpoint=https?://[^\s]+\s*', '', text, flags=re.IGNORECASE)

        request_text = text.strip()

        return docs_url, api_base_url, request_text

    def _fetch_documentation(self, url: str) -> str:
        """Fetch and extract text from documentation URL."""
        try:
            logger.info(f"Fetching documentation from: {url}")
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

            # Limit size for LLM processing
            if len(text) > MAX_CONTENT_LENGTH:
                text = text[:MAX_CONTENT_LENGTH] + "\n\n[Documentation truncated - showing first portion]"

            logger.info(f"Successfully fetched {len(text)} characters of documentation")
            return text

        except Exception as e:
            logger.error(f"Error fetching documentation: {e}")
            return f"Error fetching documentation: {str(e)}"

    def _form_api_call_with_llm(
        self,
        docs_content: str,
        request_text: str,
        api_base_url: Optional[str]
    ) -> Dict[str, Any]:
        """
        Use LLM to parse documentation and form an API call.

        Returns dict with: method, url, headers, body, params
        """
        try:
            # Build a detailed prompt for the LLM
            prompt = f"""You are an API expert. Based on the API documentation below, I need you to form a valid API request.

API Documentation:
{docs_content}

{'Base API URL: ' + api_base_url if api_base_url else 'Please extract the base API URL from the documentation.'}

User Request: {request_text}

Please analyze the documentation and provide ONLY a JSON response (no other text) with the following structure:
{{
    "method": "GET/POST/PUT/DELETE/PATCH",
    "url": "complete URL for the API call",
    "headers": {{"Header-Name": "value"}},
    "body": {{"key": "value"}} or null,
    "params": {{"param": "value"}} or null,
    "explanation": "brief explanation of what this API call does"
}}

Important:
- Provide the complete, absolute URL
- Include all required headers (like Content-Type, Authorization if needed)
- If authentication is required, note it in headers with a placeholder like "YOUR_API_KEY"
- Return ONLY valid JSON, no markdown formatting or code blocks
"""

            payload = {
                "model": LM_STUDIO_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an API expert that reads documentation and forms valid API requests. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower temperature for more precise API call formation
                "max_tokens": 1000
            }

            logger.info("Calling LLM to form API request...")
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            llm_response = result['choices'][0]['message']['content']

            logger.info(f"LLM Response: {llm_response[:200]}...")

            # Try to parse JSON from the response
            # Sometimes LLM wraps JSON in markdown code blocks, so clean that up
            llm_response = llm_response.strip()

            # Remove markdown code block markers if present
            if llm_response.startswith('```'):
                # Remove ```json or ``` at start
                llm_response = re.sub(r'^```(?:json)?\s*', '', llm_response)
                # Remove ``` at end
                llm_response = re.sub(r'\s*```$', '', llm_response)
                llm_response = llm_response.strip()

            # Parse JSON
            api_call_info = json.loads(llm_response)

            logger.info("Successfully formed API call:")
            logger.info(f"  Method: {api_call_info.get('method')}")
            logger.info(f"  URL: {api_call_info.get('url')}")

            return api_call_info

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM Response was: {llm_response}")
            return {"error": f"LLM did not return valid JSON. Response: {llm_response[:200]}"}
        except Exception as e:
            logger.error(f"Error forming API call with LLM: {e}")
            return {"error": str(e)}

    def _execute_api_call(self, api_call_info: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the API call based on the formed request."""
        try:
            method = api_call_info.get('method', 'GET').upper()
            url = api_call_info.get('url')
            headers = api_call_info.get('headers', {})
            body = api_call_info.get('body')
            params = api_call_info.get('params')

            logger.info(f"Executing {method} {url}")

            # Make the API call
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                params=params if params else None,
                timeout=REQUEST_TIMEOUT
            )

            # Try to parse response as JSON, otherwise return text
            try:
                response_data = response.json()
            except:
                response_data = response.text

            return {
                "status_code": response.status_code,
                "success": response.ok,
                "data": response_data,
                "headers": dict(response.headers)
            }

        except Exception as e:
            logger.error(f"Error executing API call: {e}")
            return {
                "status_code": 0,
                "success": False,
                "error": str(e)
            }

    def _format_response(self, api_call_info: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Format the API response for the user."""
        response = "API Call Result\n" + "="*60 + "\n\n"

        # Show what was called
        response += f"**Request Made:**\n"
        response += f"  Method: {api_call_info.get('method')}\n"
        response += f"  URL: {api_call_info.get('url')}\n"

        if api_call_info.get('explanation'):
            response += f"  Purpose: {api_call_info.get('explanation')}\n"

        response += "\n"

        # Show result
        if result.get('success'):
            response += f"**Status:** ✓ Success ({result.get('status_code')})\n\n"
            response += f"**Response:**\n"

            # Pretty print the data
            data = result.get('data')
            if isinstance(data, (dict, list)):
                response += "```json\n"
                response += json.dumps(data, indent=2)
                response += "\n```\n"
            else:
                response += str(data)[:1000]  # Limit text responses
                if len(str(data)) > 1000:
                    response += "\n\n[Response truncated]"

        else:
            response += f"**Status:** ✗ Failed ({result.get('status_code', 'N/A')})\n\n"
            response += f"**Error:**\n{result.get('error', 'Unknown error')}\n"

            if result.get('data'):
                response += f"\n**Response:**\n{json.dumps(result.get('data'), indent=2)[:500]}\n"

        # Add helpful notes
        response += "\n" + "="*60 + "\n"

        # Check for auth placeholders
        if api_call_info.get('headers', {}).get('Authorization') == 'YOUR_API_KEY':
            response += "\n⚠️  Note: This API requires authentication. The placeholder 'YOUR_API_KEY' was used.\n"

        return response
