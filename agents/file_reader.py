#!/usr/bin/env python3
"""
File Agent

Reads and writes local files (JSON, CSV, TXT, MD, LOG) with security restrictions.
Can only access files within the project directory (artefacts folder recommended).
"""

import re
import requests
import json
import csv
import os
import logging
from typing import Dict, Any, Optional
import sys

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from config import LM_STUDIO_URL, LM_STUDIO_MODEL, SUMMARY_MAX_TOKENS, SUMMARY_TEMPERATURE

logger = logging.getLogger(__name__)


class FileReaderAgent(BaseAgent):
    """Agent that reads and writes local files."""

    SUPPORTED_EXTENSIONS = {'.json', '.csv', '.txt', '.pdf', '.md', '.log'}
    WRITABLE_EXTENSIONS = {'.json', '.csv', '.txt', '.md', '.log'}  # PDF excluded from writing

    def __init__(self):
        """Initialize with the base directory for security."""
        # Get the base directory (where the Flask app is running)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.artefacts_dir = os.path.join(self.base_dir, 'artefacts')
        logger.info(f"File Agent: Base directory set to {self.base_dir}")
        logger.info(f"File Agent: Artefacts directory at {self.artefacts_dir}")

    def get_name(self) -> str:
        return "file_agent"

    def get_description(self) -> str:
        return "Reads and writes local files (JSON, CSV, TXT, MD, LOG) within the project directory"

    def get_trigger_patterns(self) -> list:
        return [
            r'file:',
            r'read file',
            r'write file',
            r'save to',
            r'save as',
            r'write to',
            r'summarize file',
            r'analyze file',
            r'\.(json|csv|txt|pdf|md|log)\b',
        ]

    def get_usage_example(self) -> str:
        return "file:artefacts/data.json or save to artefacts/results.json or write to artefacts/output.txt"

    def can_handle(self, message: str) -> bool:
        """Check if message contains a file operation."""
        message_lower = message.lower()

        # Check for file operations
        if any(trigger in message_lower for trigger in ['file:', 'read file', 'write file', 'save to', 'save as', 'write to']):
            return True

        # Check for file extensions
        for ext in self.SUPPORTED_EXTENSIONS:
            if ext in message_lower:
                return True

        return False

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """Process file read or write operation."""
        message_lower = message.lower()

        # Determine if this is a write or read operation using regex patterns
        # Check for write patterns: "save ... to", "write ... to", "save as", etc.
        write_patterns = [
            r'\bsave\s+.*\s+to\b',           # "save X to" or "save that result to"
            r'\bwrite\s+.*\s+to\b',          # "write X to" or "write that to"
            r'\bsave\s+as\b',                 # "save as"
            r'\bwrite\s+as\b',                # "write as"
            r'\bsave\s+to\b',                 # "save to"
            r'\bwrite\s+to\b',                # "write to"
            r'\bwrite\s+file\b',              # "write file"
        ]

        is_write = any(re.search(pattern, message_lower) for pattern in write_patterns)

        if is_write:
            return self._handle_write(message, full_context)
        else:
            return self._handle_read(message, full_context)

    def _handle_read(self, message: str, full_context: Dict[str, Any]) -> str:
        """Handle file read operation."""
        # Extract file path
        file_path = self._extract_file_path(message)
        if not file_path:
            return f"I couldn't find a valid file path. Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}\nExample: file:artefacts/data.json"

        logger.info(f"File Agent: Reading file: {file_path}")

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

        # Store the raw content in context for potential chaining
        if '_file_content' not in full_context:
            full_context['_file_content'] = {}
        full_context['_file_content']['last_read'] = content
        full_context['_file_content']['last_read_path'] = file_path

        return f"Summary of {os.path.basename(file_path)}:\n\n{summary}"

    def _handle_write(self, message: str, full_context: Dict[str, Any]) -> str:
        """Handle file write operation."""
        # Get content to write first (needed for auto-filename generation)
        content = self._extract_write_content(message, full_context)
        if content is None:
            return "Error: Could not determine what content to write. Please provide content or reference previous results."

        # Extract file path and content
        file_path = self._extract_write_path(message)

        # If no file path specified, generate one based on content type
        if not file_path:
            file_path = self._generate_filename(content, message)
            logger.info(f"Auto-generated filename: {file_path}")

        # Make path relative to artefacts if not already absolute
        if not os.path.isabs(file_path) and not file_path.startswith('artefacts'):
            file_path = os.path.join('artefacts', file_path)

        # Convert to absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)

        logger.info(f"File Agent: Writing to file: {file_path}")

        # Security check: Validate path is within allowed directory
        security_error = self._validate_file_path(file_path)
        if security_error:
            return security_error

        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in self.WRITABLE_EXTENSIONS:
            return f"Error: Cannot write file type '{ext}'. Writable types: {', '.join(self.WRITABLE_EXTENSIONS)}"

        # Check if file exists and handle naming conflicts
        # Only overwrite if explicitly requested
        if os.path.exists(file_path) and not self._should_overwrite(message):
            file_path = self._get_unique_filename(file_path)
            logger.info(f"File exists, renamed to: {file_path}")

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write file
        try:
            self._write_file(file_path, ext, content)
            logger.info(f"Successfully wrote to {file_path}")
            return f"✓ Successfully wrote to {os.path.relpath(file_path, self.base_dir)}\n\nPath: {file_path}"
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return f"Error writing file: {str(e)}"

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

    def _extract_write_path(self, text: str) -> Optional[str]:
        """Extract destination file path from write operation."""
        # Patterns: "save to X", "write to X", "save as X", "save that result to X"
        patterns = [
            # With quotes: "save to 'file.json'"
            r'(?:save|write)\s+.*?(?:to|as)\s+["\']([^"\']+\.(?:json|csv|txt|md|log))["\']',
            # Natural language: "save [anything] to X" or "write [anything] to X"
            # This handles: "save this message to", "save message to", "save that result to", etc.
            r'(?:save|write)\s+.*?(?:to|as)\s+([^\s:]+\.(?:json|csv|txt|md|log))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                path = match.group(1).strip('"\'')
                # Remove trailing punctuation like colons
                path = path.rstrip(':,;')
                return path

        return None

    def _extract_write_content(self, message: str, full_context: Dict[str, Any]) -> Optional[Any]:
        """
        Extract content to write from message or context.
        Checks for: explicit content in message, previous API results, previous file reads.
        """
        # Check if there's previous API call result in context
        if '_last_api_result' in full_context:
            logger.info("Using previous API result as content to write")
            return full_context['_last_api_result']

        # Try to extract content from the message itself
        # Look for content after the filename - "save this message to file.txt\n\nCONTENT"
        # or "save to file.json: {content}"
        # Extract everything after the file path
        file_path_match = re.search(r'(?:save|write)\s+.*?(?:to|as)\s+([^\s:]+\.(?:json|csv|txt|md|log))\s*:?\s*(.+)',
                                     message, re.DOTALL | re.IGNORECASE)
        if file_path_match and file_path_match.group(2):
            content_str = file_path_match.group(2).strip()
            if content_str:
                logger.info("Found content after filename")
                # Try to parse as JSON if it looks like JSON
                if content_str.startswith('{') or content_str.startswith('['):
                    try:
                        return json.loads(content_str)
                    except:
                        return content_str
                return content_str

        # No content found
        return None

    def _write_file(self, file_path: str, ext: str, content: Any) -> None:
        """Write content to file based on extension."""
        if ext == '.json':
            with open(file_path, 'w', encoding='utf-8') as f:
                if isinstance(content, str):
                    # Try to parse string as JSON first
                    try:
                        content = json.loads(content)
                    except:
                        pass
                json.dump(content, f, indent=2, ensure_ascii=False)
                logger.info(f"Wrote JSON to {file_path}")

        elif ext == '.csv':
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                    # List of dicts - write as CSV
                    writer = csv.DictWriter(f, fieldnames=content[0].keys())
                    writer.writeheader()
                    writer.writerows(content)
                else:
                    # Just write as text
                    f.write(str(content))
                logger.info(f"Wrote CSV to {file_path}")

        else:  # .txt, .md, .log
            with open(file_path, 'w', encoding='utf-8') as f:
                if isinstance(content, (dict, list)):
                    f.write(json.dumps(content, indent=2))
                else:
                    f.write(str(content))
                logger.info(f"Wrote text to {file_path}")

    def _generate_filename(self, content: Any, message: str) -> str:
        """
        Generate a filename based on content type and message context.
        Returns a filename with appropriate extension.
        """
        from datetime import datetime

        # Determine file extension based on content type
        if isinstance(content, dict) or isinstance(content, list):
            ext = '.json'
        elif 'csv' in message.lower():
            ext = '.csv'
        elif 'markdown' in message.lower() or 'md' in message.lower():
            ext = '.md'
        elif 'log' in message.lower():
            ext = '.log'
        else:
            ext = '.txt'

        # Generate timestamp-based filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"output_{timestamp}{ext}"

        logger.info(f"Generated filename: {filename}")
        return filename

    def _should_overwrite(self, message: str) -> bool:
        """Check if message explicitly requests to overwrite existing file."""
        message_lower = message.lower()
        overwrite_keywords = [
            'overwrite',
            'replace',
            'write over',
            'rewrite',
            'update the file',
            'update file'
        ]
        return any(keyword in message_lower for keyword in overwrite_keywords)

    def _get_unique_filename(self, file_path: str) -> str:
        """
        Generate a unique filename by adding _1, _2, etc. if file exists.
        Example: file.txt -> file_1.txt -> file_2.txt
        """
        if not os.path.exists(file_path):
            return file_path

        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)

        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_path = os.path.join(directory, new_filename)
            if not os.path.exists(new_path):
                return new_path
            counter += 1

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
