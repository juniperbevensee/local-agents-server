"""
Configuration file for the Flask Agent
Adjust these settings to match your LM Studio setup or LiteLLM provider
"""

import os

# ============================================================================
# LLM Provider Configuration
# ============================================================================
# Set LLM_PROVIDER to "lm_studio" (default) or "litellm"
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'lm_studio').lower()

# ============================================================================
# LM Studio Configuration (default local provider)
# ============================================================================
LM_STUDIO_HOST = os.getenv('LM_STUDIO_HOST', 'localhost')
LM_STUDIO_PORT = os.getenv('LM_STUDIO_PORT', '1234')
LM_STUDIO_URL = f"http://{LM_STUDIO_HOST}:{LM_STUDIO_PORT}/v1/chat/completions"

# Model name (LM Studio typically uses "local-model" or the actual model name)
LM_STUDIO_MODEL = os.getenv('LM_STUDIO_MODEL', 'local-model')

# ============================================================================
# LiteLLM Configuration (optional, for provider-agnostic LLM access)
# ============================================================================
# Set LITELLM_MODEL to your desired model:
#   - OpenAI: "gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"
#   - Anthropic: "claude-3-opus-20240229", "claude-3-sonnet-20240229"
#   - Azure: "azure/gpt-4"
#   - See: https://docs.litellm.ai/docs/providers
LITELLM_MODEL = os.getenv('LITELLM_MODEL', 'gpt-3.5-turbo')

# Optional: Custom API base URL for LiteLLM
LITELLM_API_BASE = os.getenv('LITELLM_API_BASE')

# API Keys (set these in your environment for the provider you're using):
# - OPENAI_API_KEY for OpenAI
# - ANTHROPIC_API_KEY for Anthropic
# - AZURE_API_KEY for Azure
# LiteLLM will automatically read these standard environment variables

# Flask Server Configuration
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')

# Content Fetching Configuration
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '4000'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))

# Summarization Configuration
SUMMARY_MAX_TOKENS = int(os.getenv('SUMMARY_MAX_TOKENS', '500'))
SUMMARY_TEMPERATURE = float(os.getenv('SUMMARY_TEMPERATURE', '0.7'))
