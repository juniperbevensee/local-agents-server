#!/usr/bin/env python3
"""
File Reader Agent

Reads local files (JSON, CSV, PDF, TXT) and summarizes them using LM Studio.
"""

import re
import requests
import json
import csv
import os
import logging
from typing import Dict, Any
import sys

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from config import LM_STUDIO_URL, LM_STUDIO_MODEL, SUMMARY_MAX_TOKENS, SUMMARY_TEMPERATURE

logger = logging.getLogger(__name__)


class FileReaderAgent(BaseAgent):
    """Agent that reads and summarizes local files."""

    SUPPORTED_EXTENSIONS = {'.json', '.csv', '.txt', '.pdf', '.md', '.log'}

    def __init__(self):
        """Initialize with the base directory for security."""
        # Get the base directory (where the Flask app is running)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logger.info(f"File Reader Agent: Base directory set to {self.base_dir}")

    def get_name(self) -> str:
        return "file_reader"

    def get_description(self) -> str:
        return "Reads and summarizes local files (JSON, CSV, PDF, TXT, MD, LOG)"

    def get_trigger_patterns(self) -> list:
        return [
            r'file:',
            r'read file',
            r'summarize file',
            r'analyze file',
            r'\.(json|csv|txt|pdf|md|log)\b',
        ]

    def get_usage_example(self) -> str:
        return "file:/path/to/document.pdf or Please summarize file:/Users/me/data.json"

    def can_handle(self, message: str) -> bool:
        """Check if message contains a file reference."""
        # Check for file: protocol
        if 'file:' in message.lower():
            return True

        # Check for file extensions
        for ext in self.SUPPORTED_EXTENSIONS:
            if ext in message.lower():
                return True

        return False

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """Read file and return summary."""
        # Extract file path
        file_path = self._extract_file_path(message)
        if not file_path:
            return f"I couldn't find a valid file path. Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}\nExample: file:/path/to/file.json"

        logger.info(f"File Reader Agent: Processing file: {file_path}")

        # Security check: Validate path is within allowed directory
        security_error = self._validate_file_path(file_path)
        if security_error:
            return security_error

        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found at '{file_path}'"

        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            return f"Error: Unsupported file type '{ext}'. Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}"

        # Read file content
        try:
            content = self._read_file(file_path, ext)
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return f"Error reading file: {str(e)}"

        # Summarize
        summary = self._summarize_with_lm_studio(content, file_path)

        return f"Summary of {os.path.basename(file_path)}:\n\n{summary}"

    def _extract_file_path(self, text: str) -> str:
        """Extract file path from message."""
        # Try file: protocol first
        file_protocol_pattern = r'file:/?/?([^\s]+)'
        match = re.search(file_protocol_pattern, text)
        if match:
            path = match.group(1)
            # Expand home directory if needed
            return os.path.expanduser(path)

        # Try to find path-like strings with supported extensions
        for ext in self.SUPPORTED_EXTENSIONS:
            # Look for patterns like /path/to/file.ext or ~/path/to/file.ext
            pattern = rf'([~/][^\s]+{re.escape(ext)})'
            match = re.search(pattern, text)
            if match:
                path = match.group(1)
                return os.path.expanduser(path)

            # Look for relative paths
            pattern = rf'([^\s]+{re.escape(ext)})'
            match = re.search(pattern, text)
            if match:
                path = match.group(1)
                # Remove any surrounding quotes
                path = path.strip('"\'')
                return os.path.expanduser(path)

        return None

    def _validate_file_path(self, file_path: str) -> str:
        """
        Validate that the file path is within the allowed directory.
        Returns error message if invalid, None if valid.
        """
        try:
            # Resolve the absolute path (handles relative paths, symlinks, .., etc.)
            absolute_path = os.path.realpath(os.path.expanduser(file_path))

            # Get the real base directory
            real_base_dir = os.path.realpath(self.base_dir)

            # Check if the file path is within the base directory
            # os.path.commonpath returns the common path prefix
            try:
                common = os.path.commonpath([absolute_path, real_base_dir])
            except ValueError:
                # Paths are on different drives (Windows)
                return f"Security Error: Cannot access files outside the project directory.\nAllowed directory: {real_base_dir}"

            # If the common path is not the base directory, the file is outside
            if common != real_base_dir:
                logger.warning(f"Security: Blocked access to file outside base directory: {file_path}")
                return (f"Security Error: Cannot access files outside the project directory.\n"
                       f"Requested: {absolute_path}\n"
                       f"Allowed directory: {real_base_dir}\n"
                       f"Tip: Place files in the 'artefacts' folder within the project.")

            logger.info(f"Security: Path validated - {absolute_path}")
            return None  # Valid path

        except Exception as e:
            logger.error(f"Error validating file path: {e}")
            return f"Error validating file path: {str(e)}"

    def _read_file(self, file_path: str, ext: str) -> str:
        """Read file content based on extension."""
        if ext == '.json':
            return self._read_json(file_path)
        elif ext == '.csv':
            return self._read_csv(file_path)
        elif ext == '.pdf':
            return self._read_pdf(file_path)
        else:  # .txt, .md, .log
            return self._read_text(file_path)

    def _read_json(self, file_path: str) -> str:
        """Read and format JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Pretty print JSON
        formatted = json.dumps(data, indent=2)

        # Limit size
        max_chars = 4000
        if len(formatted) > max_chars:
            formatted = formatted[:max_chars] + "\n\n[Content truncated]"

        return f"JSON Content:\n\n{formatted}"

    def _read_csv(self, file_path: str) -> str:
        """Read and format CSV file."""
        rows = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i < 100:  # Limit to first 100 rows
                    rows.append(row)
                else:
                    break

        # Format as text
        content = "CSV Content:\n\n"
        for row in rows:
            content += " | ".join(str(cell) for cell in row) + "\n"

        if len(rows) >= 100:
            content += "\n[Showing first 100 rows]"

        return content

    def _read_text(self, file_path: str) -> str:
        """Read plain text file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Limit size
        max_chars = 4000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[Content truncated]"

        return f"Text Content:\n\n{content}"

    def _read_pdf(self, file_path: str) -> str:
        """Read PDF file."""
        try:
            import PyPDF2

            content = "PDF Content:\n\n"
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)

                # Read first 10 pages or all pages if less than 10
                pages_to_read = min(10, num_pages)
                for i in range(pages_to_read):
                    page = pdf_reader.pages[i]
                    content += f"--- Page {i+1} ---\n"
                    content += page.extract_text()
                    content += "\n\n"

                if num_pages > pages_to_read:
                    content += f"\n[Showing first {pages_to_read} of {num_pages} pages]"

            # Limit total size
            max_chars = 4000
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[Content truncated]"

            return content
        except ImportError:
            return "PDF support requires PyPDF2. Install it with: pip install PyPDF2"
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return f"Error reading PDF: {str(e)}"

    def _summarize_with_lm_studio(self, content: str, file_path: str) -> str:
        """Send content to LM Studio for summarization."""
        try:
            filename = os.path.basename(file_path)
            prompt = f"Please provide a concise summary of the following file ({filename}):\n\n{content}"

            payload = {
                "model": LM_STUDIO_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise, informative summaries of documents and data files."
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
