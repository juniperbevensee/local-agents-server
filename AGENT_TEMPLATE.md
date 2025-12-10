# Creating a New Agent

This guide shows you how to create a new agent for the LM Studio Agent Toolkit.

## Quick Start

1. Copy the template below to `agents/your_agent_name.py`
2. Implement the required methods
3. Register your agent in `agent.py`
4. Test it!

## Template

```python
#!/usr/bin/env python3
"""
Your Agent Name

Brief description of what your agent does.
"""

import re
import logging
from typing import Dict, Any
import sys
import os

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from config import LM_STUDIO_URL, LM_STUDIO_MODEL, SUMMARY_MAX_TOKENS, SUMMARY_TEMPERATURE

logger = logging.getLogger(__name__)


class YourAgentName(BaseAgent):
    """Brief description of your agent."""

    def get_name(self) -> str:
        """Return agent name (lowercase, snake_case)."""
        return "your_agent_name"

    def get_description(self) -> str:
        """Return what this agent does."""
        return "Does something cool with data"

    def get_trigger_patterns(self) -> list:
        """Return regex patterns that trigger this agent."""
        return [
            r'keyword1',
            r'keyword2',
            r'special:',  # Prefix-based trigger
        ]

    def get_usage_example(self) -> str:
        """Return example usage."""
        return "special:process my data"

    def can_handle(self, message: str) -> bool:
        """
        Check if this agent should handle the message.

        Args:
            message: User's message content

        Returns:
            True if agent can handle, False otherwise
        """
        # Check if any trigger pattern matches
        for pattern in self.get_trigger_patterns():
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """
        Process the message and return result.

        Args:
            message: User's message content
            full_context: Full request context (all messages, model, etc.)

        Returns:
            Agent's response as a string
        """
        logger.info(f"Your Agent: Processing message: {message[:100]}...")

        # 1. Extract relevant data from message
        data = self._extract_data(message)

        # 2. Process the data
        result = self._do_processing(data)

        # 3. (Optional) Summarize with LM Studio
        if result:
            summary = self._summarize_with_lm_studio(result)
            return f"Result:\n\n{summary}"
        else:
            return "Could not process your request."

    # Helper methods below

    def _extract_data(self, message: str):
        """Extract relevant data from the message."""
        # Your extraction logic here
        # Example: extract file path, URL, search query, etc.
        match = re.search(r'special:(.+)', message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _do_processing(self, data):
        """Do the main processing work."""
        # Your main logic here
        # Example: fetch data, read files, call APIs, etc.
        try:
            # Process the data
            result = f"Processed: {data}"
            return result
        except Exception as e:
            logger.error(f"Error processing: {e}")
            return None

    def _summarize_with_lm_studio(self, content: str) -> str:
        """
        (Optional) Send content to LM Studio for summarization.

        You can customize this or skip it entirely if summarization isn't needed.
        """
        import requests

        try:
            prompt = f"Please analyze the following:\n\n{content}"

            payload = {
                "model": LM_STUDIO_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": SUMMARY_TEMPERATURE,
                "max_tokens": SUMMARY_MAX_TOKENS
            }

            logger.info("Sending to LM Studio...")
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Error calling LM Studio: {e}")
            # Fall back to returning raw content if LM Studio fails
            return content
```

## Registering Your Agent

After creating your agent file, register it in `agent.py`:

```python
# Import your agent
from agents.your_agent_name import YourAgentName

# Add to AGENTS list
AGENTS = [
    URLFetcherAgent(),
    FileReaderAgent(),
    YourAgentName(),  # Add your agent here
]
```

## Testing Your Agent

1. Start the server:
   ```bash
   python agent.py
   ```

2. Send a test request:
   ```bash
   curl -X POST http://localhost:5000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [
         {"role": "user", "content": "special:test my agent"}
       ]
     }'
   ```

3. Check the logs to see if your agent is triggered

## Agent Method Reference

### Required Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_name()` | `str` | Unique agent identifier (snake_case) |
| `get_description()` | `str` | Human-readable description |
| `get_trigger_patterns()` | `list` | Regex patterns that trigger agent |
| `get_usage_example()` | `str` | Example of how to use the agent |
| `can_handle(message)` | `bool` | Check if agent should handle message |
| `process(message, context)` | `str` | Main processing logic |

### Optional Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_help_text()` | `str` | Custom help text (auto-generated by default) |

## Best Practices

1. **Specific Triggers**: Use specific trigger patterns to avoid false matches
2. **Error Handling**: Always wrap risky operations in try/except
3. **Logging**: Use `logger.info()` and `logger.error()` liberally
4. **Clear Messages**: Return helpful error messages to users
5. **Test Edge Cases**: Test with empty input, invalid data, etc.

## Examples

See existing agents for reference:
- `agents/url_fetcher.py` - Fetches and summarizes URLs
- `agents/file_reader.py` - Reads and summarizes files

## Common Patterns

### Pattern 1: Data Extractor
Agent extracts specific data from message and processes it.

### Pattern 2: File Processor
Agent reads files and summarizes/analyzes content.

### Pattern 3: API Caller
Agent calls external APIs and formats results.

### Pattern 4: Data Transformer
Agent transforms data from one format to another.

## Need Help?

1. Check existing agents in `agents/` directory
2. Read `base_agent.py` for the base class documentation
3. Look at the logs when testing to debug issues
4. Visit `/help` endpoint to see all registered agents
