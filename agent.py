#!/usr/bin/env python3
"""
LM Studio Agent Toolkit - Main Server

A modular Flask server that routes requests to specialized agents.
Agents can fetch URLs, read files, and more - all summarized via LM Studio.
"""

import logging
from flask import Flask, request, jsonify
from typing import List, Dict, Any
from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
)

# Import agents
from agents.url_fetcher import URLFetcherAgent
from agents.file_reader import FileReaderAgent
from agents.api_caller import APICallerAgent

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Register all available agents here
# IMPORTANT: Order matters! Most specific agents first, general ones last.
# APICallerAgent checks for "api_call:" or "docs=" (specific)
# FileReaderAgent checks for "file:" or file extensions (specific)
# URLFetcherAgent checks for any URL (general - catches everything)
AGENTS = [
    APICallerAgent(),      # Most specific - api_call: or docs=
    FileReaderAgent(),     # Specific - file: or extensions
    URLFetcherAgent(),     # General - any URL
]


class AgentRouter:
    """Routes requests to the appropriate agent."""

    def __init__(self, agents: List):
        self.agents = agents
        logger.info(f"Initialized AgentRouter with {len(agents)} agents")
        for agent in agents:
            logger.info(f"  - {agent.get_name()}: {agent.get_description()}")

    def route(self, message: str, full_context: Dict[str, Any]) -> str:
        """
        Route message to appropriate agent.

        Args:
            message: The user's message
            full_context: Full request context

        Returns:
            Agent's response
        """
        logger.info(f"Routing message: {message[:100]}...")

        # Try each agent in order
        for agent in self.agents:
            if agent.can_handle(message):
                logger.info(f"Routing to agent: {agent.get_name()}")
                try:
                    return agent.process(message, full_context)
                except Exception as e:
                    logger.error(f"Error in agent {agent.get_name()}: {e}", exc_info=True)
                    return f"Error in {agent.get_name()}: {str(e)}"

        # No agent could handle it
        return self._get_no_handler_message()

    def _get_no_handler_message(self) -> str:
        """Return helpful message when no agent can handle the request."""
        return (
            "I couldn't determine what you're asking for. Here are the available tools:\n\n"
            + self.get_help_text() +
            "\n\nOr send a request to /help for more details."
        )

    def get_help_text(self) -> str:
        """Generate help text for all agents."""
        help_text = "Available Tools:\n" + "=" * 60 + "\n\n"

        for i, agent in enumerate(self.agents, 1):
            help_text += f"{i}. {agent.get_name().upper()}\n"
            help_text += f"   {agent.get_description()}\n"
            help_text += f"   Example: {agent.get_usage_example()}\n"
            help_text += "\n"

        help_text += "=" * 60 + "\n"
        help_text += "\nTip: Just send your request naturally, and I'll route it to the right tool!"

        return help_text


# Initialize router
router = AgentRouter(AGENTS)


# Log all incoming requests
@app.before_request
def log_request_info():
    logger.info('=' * 80)
    logger.info(f'Incoming Request: {request.method} {request.path}')
    logger.info(f'Headers: {dict(request.headers)}')
    if request.data:
        logger.info(f'Body: {request.data.decode("utf-8")[:500]}...' if len(request.data) > 500 else f'Body: {request.data.decode("utf-8")}')
    logger.info('=' * 80)


@app.route('/', methods=['GET', 'POST'])
def root():
    """Root endpoint - redirects to correct endpoint or shows help."""
    if request.method == 'POST':
        # User sent POST to root, redirect to the correct handler
        logger.warning(f"Received POST to root path. Forwarding to /v1/chat/completions")
        return chat_completions()
    else:
        return jsonify({
            "service": "lm-studio-agent-toolkit",
            "status": "running",
            "version": "2.0",
            "agents": [
                {
                    "name": agent.get_name(),
                    "description": agent.get_description(),
                    "example": agent.get_usage_example()
                }
                for agent in AGENTS
            ],
            "endpoints": {
                "chat": "/v1/chat/completions (POST)",
                "help": "/help (GET)",
                "health": "/health (GET)"
            }
        })


@app.route('/help', methods=['GET'])
def help_endpoint():
    """HELP endpoint - returns list of all available tools."""
    help_text = router.get_help_text()

    return jsonify({
        "service": "lm-studio-agent-toolkit",
        "help": help_text,
        "agents": [
            {
                "name": agent.get_name(),
                "description": agent.get_description(),
                "example": agent.get_usage_example(),
                "triggers": agent.get_trigger_patterns()
            }
            for agent in AGENTS
        ]
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

        # Route to appropriate agent
        response_text = router.route(content, data)

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
    return jsonify({
        "status": "healthy",
        "service": "lm-studio-agent-toolkit",
        "agents_loaded": len(AGENTS),
        "agents": [agent.get_name() for agent in AGENTS]
    })


if __name__ == '__main__':
    logger.info("="*80)
    logger.info("Starting LM Studio Agent Toolkit Server...")
    logger.info("="*80)
    logger.info(f"Flask Server: http://{FLASK_HOST}:{FLASK_PORT}")
    logger.info(f"Available agents: {', '.join([a.get_name() for a in AGENTS])}")
    logger.info("="*80)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
