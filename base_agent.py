#!/usr/bin/env python3
"""
Base Agent Pattern for LM Studio Agent Toolkit

This module provides the base class for creating new agents.
All agents should inherit from BaseAgent and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the toolkit.

    To create a new agent:
    1. Create a new file (e.g., my_agent.py)
    2. Import BaseAgent: from base_agent import BaseAgent
    3. Create a class that inherits from BaseAgent
    4. Implement all @abstractmethod methods
    5. Register your agent in agent.py

    Example:
        class MyCustomAgent(BaseAgent):
            def get_name(self) -> str:
                return "my_custom_agent"

            def get_description(self) -> str:
                return "Does something custom"

            def get_trigger_patterns(self) -> list:
                return [r'do custom thing', r'custom:']

            def can_handle(self, message: str) -> bool:
                import re
                for pattern in self.get_trigger_patterns():
                    if re.search(pattern, message, re.IGNORECASE):
                        return True
                return False

            def process(self, message: str, full_context: Dict[str, Any]) -> str:
                # Your custom logic here
                return "Result from custom agent"
    """

    @abstractmethod
    def get_name(self) -> str:
        """
        Return the unique name/identifier for this agent.
        Should be lowercase with underscores (snake_case).

        Returns:
            str: Agent name (e.g., "url_fetcher", "file_reader")
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Return a human-readable description of what this agent does.

        Returns:
            str: Brief description of the agent's functionality
        """
        pass

    @abstractmethod
    def get_trigger_patterns(self) -> list:
        """
        Return a list of regex patterns or keywords that trigger this agent.

        Returns:
            list: List of regex patterns (strings) that identify when this agent should handle a request
        """
        pass

    @abstractmethod
    def get_usage_example(self) -> str:
        """
        Return an example of how to use this agent.

        Returns:
            str: Example usage string
        """
        pass

    @abstractmethod
    def can_handle(self, message: str) -> bool:
        """
        Determine if this agent can handle the given message.

        Args:
            message (str): The user's message content

        Returns:
            bool: True if this agent should handle the message, False otherwise
        """
        pass

    @abstractmethod
    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """
        Process the message and return the result.

        Args:
            message (str): The user's message content
            full_context (dict): Full request context including all messages, model, etc.

        Returns:
            str: The agent's response
        """
        pass

    def get_help_text(self) -> str:
        """
        Generate help text for this agent (default implementation).
        Can be overridden for custom help text.

        Returns:
            str: Formatted help text
        """
        return f"""
**{self.get_name()}**
{self.get_description()}

Example: {self.get_usage_example()}

Triggers: {', '.join(self.get_trigger_patterns())}
"""
