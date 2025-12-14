"""
LLM Client - Unified interface for LLM providers

Supports:
- LM Studio (default, local inference)
- LiteLLM (provider-agnostic, supports OpenAI, Anthropic, Azure, etc.)

Configuration via environment variables:
- LLM_PROVIDER: "lm_studio" (default) or "litellm"
- For LiteLLM, set additional env vars as per provider requirements
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Import config
from config import (
    LM_STUDIO_URL,
    LM_STUDIO_MODEL,
    SUMMARY_TEMPERATURE,
    SUMMARY_MAX_TOKENS
)

# Determine LLM provider
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'lm_studio').lower()

# Try to import LiteLLM if configured
if LLM_PROVIDER == 'litellm':
    try:
        import litellm
        LITELLM_AVAILABLE = True
        logger.info("LiteLLM imported successfully")
    except ImportError:
        LITELLM_AVAILABLE = False
        logger.warning("LiteLLM not available. Install with: pip install litellm")
        logger.warning("Falling back to LM Studio")
        LLM_PROVIDER = 'lm_studio'
else:
    LITELLM_AVAILABLE = False

# Import requests for LM Studio fallback
import requests


class LLMClient:
    """
    Unified LLM client that supports multiple providers.

    Usage:
        client = LLMClient()
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=500
        )
    """

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            provider: Override provider ("lm_studio" or "litellm").
                     If None, uses LLM_PROVIDER env var.
        """
        self.provider = provider or LLM_PROVIDER

        # LiteLLM configuration
        if self.provider == 'litellm' and LITELLM_AVAILABLE:
            # Get LiteLLM model from env (e.g., "gpt-4", "claude-3-opus", "azure/gpt-4")
            self.model = os.getenv('LITELLM_MODEL', 'gpt-3.5-turbo')

            # Optional: Set LiteLLM API base if needed
            self.api_base = os.getenv('LITELLM_API_BASE')

            # Optional: Set API key (provider-specific)
            # LiteLLM reads from standard env vars like OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

            logger.info(f"LiteLLM initialized with model: {self.model}")
        else:
            # LM Studio configuration
            self.provider = 'lm_studio'  # Force to lm_studio if litellm not available
            self.model = LM_STUDIO_MODEL
            self.lm_studio_url = LM_STUDIO_URL
            logger.info(f"LM Studio initialized: {self.lm_studio_url}")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 60,
        **kwargs
    ) -> str:
        """
        Call LLM for chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific parameters

        Returns:
            str: The LLM's response content

        Raises:
            Exception: If LLM call fails
        """
        # Use defaults from config if not specified
        if temperature is None:
            temperature = SUMMARY_TEMPERATURE
        if max_tokens is None:
            max_tokens = SUMMARY_MAX_TOKENS

        if self.provider == 'litellm':
            return self._call_litellm(messages, temperature, max_tokens, **kwargs)
        else:
            return self._call_lm_studio(messages, temperature, max_tokens, timeout, **kwargs)

    def _call_litellm(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Call LiteLLM for completion."""
        try:
            logger.info(f"Calling LiteLLM with model: {self.model}")

            # Prepare kwargs for LiteLLM
            litellm_kwargs = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
            }

            # Add API base if configured
            if self.api_base:
                litellm_kwargs['api_base'] = self.api_base

            # Add any additional kwargs
            litellm_kwargs.update(kwargs)

            # Call LiteLLM
            response = litellm.completion(**litellm_kwargs)

            # Extract content from response
            content = response.choices[0].message.content
            logger.info("LiteLLM call successful")
            return content

        except Exception as e:
            logger.error(f"LiteLLM call failed: {e}")
            raise Exception(f"LiteLLM error: {str(e)}")

    def _call_lm_studio(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: int,
        **kwargs
    ) -> str:
        """Call LM Studio for completion."""
        try:
            logger.info(f"Calling LM Studio: {self.lm_studio_url}")

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # Add any additional kwargs
            payload.update(kwargs)

            response = requests.post(
                self.lm_studio_url,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']
            logger.info("LM Studio call successful")
            return content

        except Exception as e:
            logger.error(f"LM Studio call failed: {e}")
            raise Exception(f"LM Studio error: {str(e)}")


# Global client instance
_global_client = None


def get_llm_client() -> LLMClient:
    """
    Get the global LLM client instance (singleton pattern).

    Returns:
        LLMClient: Configured LLM client
    """
    global _global_client
    if _global_client is None:
        _global_client = LLMClient()
    return _global_client


def chat_completion(
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: int = 60,
    **kwargs
) -> str:
    """
    Convenience function for chat completion using global client.

    Args:
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds
        **kwargs: Additional provider-specific parameters

    Returns:
        str: The LLM's response content
    """
    client = get_llm_client()
    return client.chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs
    )
