"""
Credential Manager - Secure API key and secret storage

Loads credentials from .env file and provides fuzzy matching for natural language lookups.

Usage:
    from credential_manager import get_credential

    # Natural language lookup
    api_key = get_credential("airtable")  # Matches "Airtable personal access token"
    token = get_credential("discord bot")  # Matches "Discord bot token"

    # Exact match
    key = get_credential("OPENAI_API_KEY")
"""

import os
import re
import logging
from typing import Optional, Dict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file if it exists
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
    logger.info(f"Loaded environment variables from {ENV_FILE}")
else:
    logger.info("No .env file found, using system environment variables only")

# Cache for parsed credentials
_credential_cache: Optional[Dict[str, str]] = None


def _parse_env_file() -> Dict[str, str]:
    """
    Parse .env file to extract credentials in both standard and natural language formats.

    Supports:
    - Standard: OPENAI_API_KEY=sk-...
    - Natural: OpenAI API key: sk-...
    - Natural: Airtable personal access token: pat...

    Returns:
        Dict mapping normalized keys to their values
    """
    credentials = {}

    # First, get all environment variables (already loaded by dotenv)
    for key, value in os.environ.items():
        if value and not key.startswith('_'):  # Skip empty and private vars
            credentials[key.lower()] = value

    # Additionally parse .env file for natural language format
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Check for natural language format: "Name: value"
                    natural_match = re.match(r'^([^:=]+?):\s*(.+)$', line)
                    if natural_match:
                        key_name = natural_match.group(1).strip()
                        value = natural_match.group(2).strip()

                        if value:  # Only store non-empty values
                            # Normalize key: lowercase, remove special chars except underscore
                            normalized_key = re.sub(r'[^\w\s]', '', key_name.lower())
                            normalized_key = re.sub(r'\s+', '_', normalized_key)
                            credentials[normalized_key] = value
                            logger.debug(f"Loaded credential: {key_name} -> {normalized_key}")

                    # Standard format: KEY=value (already handled by dotenv, but normalize)
                    elif '=' in line and not line.startswith('export'):
                        key_name = line.split('=')[0].strip()
                        value = line.split('=', 1)[1].strip()

                        if value:
                            credentials[key_name.lower()] = value
                            logger.debug(f"Loaded standard credential: {key_name}")

        except Exception as e:
            logger.error(f"Error parsing .env file: {e}")

    logger.info(f"Loaded {len(credentials)} credentials from environment")
    return credentials


def _get_credentials() -> Dict[str, str]:
    """Get cached credentials or parse .env file."""
    global _credential_cache
    if _credential_cache is None:
        _credential_cache = _parse_env_file()
    return _credential_cache


def _normalize_search_term(term: str) -> str:
    """
    Normalize search term for fuzzy matching.

    Examples:
        "Airtable" -> "airtable"
        "discord bot" -> "discord_bot"
        "GitHub-Token" -> "github_token"
    """
    normalized = re.sub(r'[^\w\s]', '', term.lower())
    normalized = re.sub(r'\s+', '_', normalized)
    return normalized


def _fuzzy_match(search_term: str, credentials: Dict[str, str]) -> Optional[str]:
    """
    Fuzzy match search term against credential keys.

    Matching strategy:
    1. Exact match (case-insensitive)
    2. Partial match (search term in key)
    3. Keyword match (all words in search term appear in key)

    Args:
        search_term: The term to search for (e.g., "airtable", "discord bot")
        credentials: Dict of normalized keys to values

    Returns:
        The credential value if found, None otherwise
    """
    normalized_search = _normalize_search_term(search_term)

    # Strategy 1: Exact match
    if normalized_search in credentials:
        logger.debug(f"Exact match found for '{search_term}'")
        return credentials[normalized_search]

    # Strategy 2: Partial match - search term is substring of key
    for key, value in credentials.items():
        if normalized_search in key:
            logger.debug(f"Partial match found: '{search_term}' matches '{key}'")
            return value

    # Strategy 3: Keyword match - all words in search term appear in key
    search_words = normalized_search.split('_')
    if len(search_words) > 1:
        for key, value in credentials.items():
            if all(word in key for word in search_words):
                logger.debug(f"Keyword match found: '{search_term}' matches '{key}'")
                return value

    # Strategy 4: Reverse partial - key is substring of search term
    for key, value in credentials.items():
        if key in normalized_search:
            logger.debug(f"Reverse partial match: '{key}' in '{search_term}'")
            return value

    return None


def get_credential(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get credential by name using fuzzy matching.

    Supports natural language lookups:
    - "airtable" matches "Airtable personal access token"
    - "discord bot" matches "Discord bot token" or "Discord bot key"
    - "github" matches "GitHub personal access token"
    - "OPENAI_API_KEY" matches exact environment variable

    Args:
        name: The credential name to search for
        default: Default value if credential not found

    Returns:
        The credential value, or default if not found

    Examples:
        >>> get_credential("airtable")
        'pat_abc123...'

        >>> get_credential("discord bot")
        'MTk4...'

        >>> get_credential("nonexistent", default="fallback")
        'fallback'
    """
    if not name:
        logger.warning("Empty credential name provided")
        return default

    credentials = _get_credentials()

    # Try fuzzy match
    value = _fuzzy_match(name, credentials)

    if value:
        logger.info(f"Found credential for '{name}' (value masked)")
        return value
    else:
        logger.debug(f"No credential found for '{name}'")
        return default


def has_credential(name: str) -> bool:
    """
    Check if a credential exists without retrieving it.

    Args:
        name: The credential name to check

    Returns:
        True if credential exists, False otherwise
    """
    return get_credential(name) is not None


def list_credential_names() -> list:
    """
    List all available credential names (keys only, not values).
    Useful for debugging.

    Returns:
        List of credential key names
    """
    credentials = _get_credentials()
    return sorted(credentials.keys())


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    Mask a secret for logging purposes.

    Args:
        secret: The secret to mask
        visible_chars: Number of characters to show at start/end

    Returns:
        Masked secret (e.g., "sk-a...xyz")

    Examples:
        >>> mask_secret("sk-abc123xyz789")
        'sk-a...789'

        >>> mask_secret("pat_verylongtoken123456", visible_chars=6)
        'pat_ve...123456'
    """
    if not secret or len(secret) <= visible_chars * 2:
        return "***"

    start = secret[:visible_chars]
    end = secret[-visible_chars:]
    return f"{start}...{end}"


def get_credential_masked(name: str) -> Optional[str]:
    """
    Get credential and return masked version for logging.

    Args:
        name: The credential name to search for

    Returns:
        Masked credential value for safe logging
    """
    value = get_credential(name)
    if value:
        return mask_secret(value)
    return None


# Reload credentials (useful if .env file is modified at runtime)
def reload_credentials():
    """
    Reload credentials from .env file.
    Call this if the .env file is modified while the application is running.
    """
    global _credential_cache
    _credential_cache = None
    load_dotenv(ENV_FILE, override=True)
    logger.info("Credentials reloaded from .env file")


# Initialize on import
logger.info("Credential manager initialized")
