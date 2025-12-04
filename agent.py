#!/usr/bin/env python3
"""
Flask Agent for URL Fetching and Summarization via LM Studio
Receives requests from LM Studio, extracts URLs from messages, fetches content, and summarizes.
"""

import re
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import logging
from config import (
    LM_STUDIO_URL,
    LM_STUDIO_MODEL,
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    MAX_CONTENT_LENGTH,
    REQUEST_TIMEOUT,
    SUMMARY_MAX_TOKENS,
    SUMMARY_TEMPERATURE
)

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Log all incoming requests
@app.before_request
def log_request_info():
    logger.info('=' * 80)
    logger.info(f'Incoming Request: {request.method} {request.path}')
    logger.info(f'Headers: {dict(request.headers)}')
    if request.data:
        logger.info(f'Body: {request.data.decode("utf-8")[:500]}...' if len(request.data) > 500 else f'Body: {request.data.decode("utf-8")}')
    logger.info('=' * 80)

def extract_url_from_text(text):
    """Extract URL from text using regex."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    return urls[0] if urls else None

def extract_search_query(text):
    """Extract search query from text like 'Search X on Y'."""
    # Patterns like "Search Trump on Telegram"
    search_pattern = r'[Ss]earch\s+(.+?)\s+on\s+(\w+)'
    match = re.search(search_pattern, text)
    if match:
        query = match.group(1).strip()
        platform = match.group(2).strip()
        return query, platform
    return None, None

def fetch_website_content(url):
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

def summarize_with_lm_studio(content, query=None):
    """Send content to LM Studio for summarization."""
    try:
        if query:
            prompt = f"Please summarize the following content in relation to '{query}':\n\n{content}"
        else:
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

@app.route('/', methods=['GET', 'POST'])
def root():
    """Root endpoint - redirects to correct endpoint."""
    if request.method == 'POST':
        # User sent POST to root, redirect to the correct handler
        logger.warning(f"Received POST to root path. Forwarding to /v1/chat/completions")
        return chat_completions()
    else:
        return jsonify({
            "service": "url-fetch-summarize-agent",
            "status": "running",
            "endpoints": {
                "chat_completions": "/v1/chat/completions (POST)",
                "health": "/health (GET)"
            },
            "usage": "Send POST requests to /v1/chat/completions with OpenAI-compatible format"
        })

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Main endpoint that mimics OpenAI chat completions API."""
    try:
        data = request.json
        logger.info(f"Processing chat completion request with {len(data.get('messages', []))} messages")

        # Extract the last message
        messages = data.get('messages', [])
        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        last_message = messages[-1]
        content = last_message.get('content', '')

        # Try to extract URL from the message
        url = extract_url_from_text(content)

        if url:
            # We have a direct URL, fetch and summarize
            logger.info(f"Found URL in message: {url}")
            website_content = fetch_website_content(url)
            summary = summarize_with_lm_studio(website_content)
            response_text = f"Summary of {url}:\n\n{summary}"
        else:
            # Check if it's a search query
            query, platform = extract_search_query(content)
            if query and platform:
                # This is a search request, not a direct URL
                response_text = (
                    f"I detected a search request for '{query}' on {platform}. "
                    f"However, I need a direct URL to fetch and summarize content. "
                    f"\n\nPlease provide a URL like: https://example.com/article"
                )
            else:
                # No URL or search pattern found
                response_text = (
                    "I couldn't find a URL in your message. "
                    "Please provide a URL to fetch and summarize, for example: "
                    "https://example.com/article"
                )

        # Return response in OpenAI format
        response = {
            "id": "chatcmpl-agent",
            "object": "chat.completion",
            "created": 1234567890,
            "model": data.get('model', 'agent'),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

        logger.info(f"Returning response with {len(response_text)} characters")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "url-fetch-summarize-agent"})

if __name__ == '__main__':
    logger.info("Starting Flask Agent Server...")
    logger.info(f"LM Studio URL: {LM_STUDIO_URL}")
    logger.info(f"Flask Server: http://{FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
