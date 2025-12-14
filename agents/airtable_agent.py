#!/usr/bin/env python3
"""
Airtable Agent

Specialized agent for interacting with Airtable using the pyairtable library.
Supports common operations: list records, create, update, delete, search.

Usage:
    airtable: List all records from base appXYZ table tblABC
    airtable: Create record in Projects with Name="New Project" and Status="Active"
    airtable: Update record recXYZ in Tasks set Status="Done"
    airtable: Delete record recXYZ from Archive
    airtable: Search for records where Status="Active" in Projects
"""

import re
import logging
from typing import Dict, Any, Optional, List
import sys
import os
import json

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from credential_manager import get_credential, mask_secret

logger = logging.getLogger(__name__)

# Try to import pyairtable
try:
    from pyairtable import Api, Table
    PYAIRTABLE_AVAILABLE = True
except ImportError:
    PYAIRTABLE_AVAILABLE = False
    logger.warning("pyairtable not installed. Install with: pip install pyairtable")


class AirtableAgent(BaseAgent):
    """Agent for Airtable operations using pyairtable library."""

    def get_name(self) -> str:
        return "airtable"

    def get_description(self) -> str:
        return "Interacts with Airtable databases using the pyairtable library for CRUD operations"

    def get_trigger_patterns(self) -> list:
        return [
            r'airtable:',
            r'\bairtable\b.*\b(list|get|create|update|delete|search|find)\b',
            r'\b(base|table)\s+(app[a-zA-Z0-9]+|tbl[a-zA-Z0-9]+)\b',
        ]

    def get_usage_example(self) -> str:
        return "airtable: List all records from Projects table"

    def can_handle(self, message: str) -> bool:
        """Check if this is an Airtable request."""
        message_lower = message.lower()

        # Check for explicit trigger
        if 'airtable:' in message_lower:
            return True

        # Check for Airtable IDs (app... or tbl...)
        if re.search(r'\b(app|tbl)[a-zA-Z0-9]+\b', message):
            return True

        # Check for Airtable operations with Airtable keyword
        if 'airtable' in message_lower:
            operations = ['list', 'get', 'create', 'update', 'delete', 'search', 'find', 'records']
            if any(op in message_lower for op in operations):
                return True

        return False

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """Process Airtable request."""
        if not PYAIRTABLE_AVAILABLE:
            return (
                "❌ pyairtable library not installed.\n\n"
                "Install it with: pip install pyairtable\n\n"
                "See: https://pyairtable.readthedocs.io/"
            )

        logger.info("Airtable Agent: Processing request")

        # Get API token from credential manager
        api_token = get_credential("airtable")
        if not api_token:
            return (
                "❌ No Airtable API token found.\n\n"
                "Add to your .env file:\n"
                "Airtable personal access token: pat_your_token_here\n\n"
                "Get your token from: https://airtable.com/create/tokens"
            )

        logger.info(f"Using Airtable API token: {mask_secret(api_token)}")

        # Extract operation details
        operation = self._detect_operation(message)
        base_id = self._extract_base_id(message)
        table_id = self._extract_table_id(message)

        # Try to get base_id and table_id from .env if not in message
        if not base_id:
            base_id = get_credential("airtable base id") or get_credential("airtable base")
            if base_id:
                logger.info(f"Using base_id from .env: {base_id}")

        if not table_id:
            table_id = get_credential("airtable table id") or get_credential("airtable table")
            if table_id:
                logger.info(f"Using table_id from .env: {table_id}")

        # Validate we have required IDs
        if not base_id:
            return (
                "❌ No Airtable base ID found.\n\n"
                "Either:\n"
                "1. Include in message: 'base appXYZ123'\n"
                "2. Add to .env: Airtable base id: appXYZ123\n\n"
                "Find your base ID in the Airtable API docs for your base."
            )

        if not table_id:
            return (
                "❌ No Airtable table ID found.\n\n"
                "Either:\n"
                "1. Include in message: 'table tblXYZ123' or 'Projects table'\n"
                "2. Add to .env: Airtable table id: tblXYZ123\n\n"
                "Find your table ID in the Airtable API docs for your base."
            )

        try:
            # Initialize Airtable API
            api = Api(api_token)
            table = api.table(base_id, table_id)

            # Execute operation
            if operation == 'list' or operation == 'get':
                return self._list_records(table, message)
            elif operation == 'create':
                return self._create_record(table, message)
            elif operation == 'update':
                return self._update_record(table, message)
            elif operation == 'delete':
                return self._delete_record(table, message)
            elif operation == 'search' or operation == 'find':
                return self._search_records(table, message)
            else:
                return f"❌ Unknown operation: {operation}. Supported: list, create, update, delete, search"

        except Exception as e:
            logger.error(f"Airtable API error: {e}", exc_info=True)
            return f"❌ Airtable API Error: {str(e)}\n\nCheck your base ID, table ID, and API token permissions."

    def _detect_operation(self, message: str) -> str:
        """Detect the operation type from the message."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['list', 'get all', 'show', 'fetch all']):
            return 'list'
        elif 'create' in message_lower or 'add' in message_lower or 'insert' in message_lower:
            return 'create'
        elif 'update' in message_lower or 'modify' in message_lower or 'edit' in message_lower:
            return 'update'
        elif 'delete' in message_lower or 'remove' in message_lower:
            return 'delete'
        elif 'search' in message_lower or 'find' in message_lower or 'where' in message_lower:
            return 'search'
        else:
            return 'list'  # Default to list

    def _extract_base_id(self, message: str) -> Optional[str]:
        """Extract Airtable base ID from message."""
        # Look for app... pattern
        match = re.search(r'\b(app[a-zA-Z0-9]{14,})\b', message)
        if match:
            return match.group(1)

        # Look for "base appXYZ" or "base: appXYZ"
        match = re.search(r'base[:\s]+([a-zA-Z0-9]+)', message, re.IGNORECASE)
        if match and match.group(1).startswith('app'):
            return match.group(1)

        return None

    def _extract_table_id(self, message: str) -> Optional[str]:
        """Extract Airtable table ID or name from message."""
        # Look for tbl... pattern
        match = re.search(r'\b(tbl[a-zA-Z0-9]{14,})\b', message)
        if match:
            return match.group(1)

        # Look for "table tblXYZ" or "table: tblXYZ"
        match = re.search(r'table[:\s]+([a-zA-Z0-9]+)', message, re.IGNORECASE)
        if match:
            return match.group(1)

        # Look for table name in quotes or capitalized
        match = re.search(r'(?:from|in|table)\s+["\']?([A-Z][a-zA-Z\s]+)["\']?(?:\s|$)', message)
        if match:
            return match.group(1).strip()

        return None

    def _list_records(self, table: Any, message: str) -> str:
        """List all records from table."""
        try:
            # Extract limit if specified
            limit_match = re.search(r'(?:first|limit|max)\s+(\d+)', message, re.IGNORECASE)
            max_records = int(limit_match.group(1)) if limit_match else 100

            logger.info(f"Listing records (max: {max_records})...")
            records = table.all(max_records=max_records)

            if not records:
                return "✓ No records found in this table."

            # Format response
            response = f"✓ Found {len(records)} record(s):\n\n"

            for i, record in enumerate(records, 1):
                response += f"**Record {i}** (ID: {record['id']})\n"
                for field_name, field_value in record['fields'].items():
                    # Format value
                    if isinstance(field_value, list):
                        field_value = ', '.join(str(v) for v in field_value)
                    response += f"  • {field_name}: {field_value}\n"
                response += "\n"

            return response.strip()

        except Exception as e:
            logger.error(f"Error listing records: {e}")
            return f"❌ Error listing records: {str(e)}"

    def _create_record(self, table: Any, message: str) -> str:
        """Create a new record in table."""
        try:
            # Extract fields from message
            fields = self._parse_fields(message)

            if not fields:
                return (
                    "❌ No fields found to create.\n\n"
                    "Format: airtable: Create record with Name=\"Project X\" and Status=\"Active\""
                )

            logger.info(f"Creating record with fields: {fields}")
            record = table.create(fields)

            response = f"✓ Record created successfully!\n\n"
            response += f"**Record ID:** {record['id']}\n"
            response += f"**Fields:**\n"
            for field_name, field_value in record['fields'].items():
                response += f"  • {field_name}: {field_value}\n"

            return response.strip()

        except Exception as e:
            logger.error(f"Error creating record: {e}")
            return f"❌ Error creating record: {str(e)}"

    def _update_record(self, table: Any, message: str) -> str:
        """Update an existing record."""
        try:
            # Extract record ID
            record_id = self._extract_record_id(message)
            if not record_id:
                return "❌ No record ID found. Format: 'update record recXYZ123 set Name=\"New Name\"'"

            # Extract fields to update
            fields = self._parse_fields(message)
            if not fields:
                return "❌ No fields found to update. Format: 'set Name=\"Value\" and Status=\"Active\"'"

            logger.info(f"Updating record {record_id} with fields: {fields}")
            record = table.update(record_id, fields)

            response = f"✓ Record updated successfully!\n\n"
            response += f"**Record ID:** {record['id']}\n"
            response += f"**Updated Fields:**\n"
            for field_name, field_value in record['fields'].items():
                response += f"  • {field_name}: {field_value}\n"

            return response.strip()

        except Exception as e:
            logger.error(f"Error updating record: {e}")
            return f"❌ Error updating record: {str(e)}"

    def _delete_record(self, table: Any, message: str) -> str:
        """Delete a record from table."""
        try:
            # Extract record ID
            record_id = self._extract_record_id(message)
            if not record_id:
                return "❌ No record ID found. Format: 'delete record recXYZ123'"

            logger.info(f"Deleting record {record_id}...")
            deleted = table.delete(record_id)

            return f"✓ Record deleted successfully!\n\n**Deleted Record ID:** {deleted['id']}"

        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            return f"❌ Error deleting record: {str(e)}"

    def _search_records(self, table: Any, message: str) -> str:
        """Search for records matching criteria."""
        try:
            # Parse search formula from message
            formula = self._parse_search_formula(message)

            if not formula:
                # If no formula, just list all
                return self._list_records(table, message)

            logger.info(f"Searching with formula: {formula}")
            records = table.all(formula=formula)

            if not records:
                return f"✓ No records found matching criteria: {formula}"

            # Format response (similar to list)
            response = f"✓ Found {len(records)} matching record(s):\n\n"

            for i, record in enumerate(records, 1):
                response += f"**Record {i}** (ID: {record['id']})\n"
                for field_name, field_value in record['fields'].items():
                    if isinstance(field_value, list):
                        field_value = ', '.join(str(v) for v in field_value)
                    response += f"  • {field_name}: {field_value}\n"
                response += "\n"

            return response.strip()

        except Exception as e:
            logger.error(f"Error searching records: {e}")
            return f"❌ Error searching records: {str(e)}"

    def _extract_record_id(self, message: str) -> Optional[str]:
        """Extract record ID from message."""
        # Look for rec... pattern
        match = re.search(r'\b(rec[a-zA-Z0-9]{14,})\b', message)
        if match:
            return match.group(1)

        # Look for "record recXYZ" or "record: recXYZ" or "id: recXYZ"
        match = re.search(r'(?:record|id)[:\s]+([a-zA-Z0-9]+)', message, re.IGNORECASE)
        if match and match.group(1).startswith('rec'):
            return match.group(1)

        return None

    def _parse_fields(self, message: str) -> Dict[str, Any]:
        """
        Parse field assignments from message.

        Supports formats:
        - Name="Value" and Status="Active"
        - with Name="Value", Status="Active"
        - set Name="Value" and Status="Active"
        """
        fields = {}

        # Pattern: FieldName="Value" or FieldName='Value' or FieldName=Value
        pattern = r'([A-Za-z_][A-Za-z0-9_\s]*?)\s*=\s*["\']([^"\']+)["\']'
        matches = re.findall(pattern, message)

        for field_name, field_value in matches:
            field_name = field_name.strip()
            field_value = field_value.strip()

            # Try to parse as JSON for arrays/objects
            if field_value.startswith('[') or field_value.startswith('{'):
                try:
                    field_value = json.loads(field_value)
                except:
                    pass  # Keep as string

            # Try to parse as number
            elif field_value.isdigit():
                field_value = int(field_value)
            elif field_value.replace('.', '', 1).isdigit():
                field_value = float(field_value)

            fields[field_name] = field_value

        return fields

    def _parse_search_formula(self, message: str) -> Optional[str]:
        """
        Parse search criteria into Airtable formula.

        Supports simple patterns like:
        - where Status="Active"
        - find Name="Project X"
        """
        # Look for "where field=value" pattern
        where_match = re.search(r'where\s+([A-Za-z_][A-Za-z0-9_\s]*?)\s*=\s*["\']([^"\']+)["\']', message, re.IGNORECASE)
        if where_match:
            field_name = where_match.group(1).strip()
            field_value = where_match.group(2).strip()
            return f"{{{field_name}}}='{field_value}'"

        # Look for "find field=value" pattern
        find_match = re.search(r'find\s+([A-Za-z_][A-Za-z0-9_\s]*?)\s*=\s*["\']([^"\']+)["\']', message, re.IGNORECASE)
        if find_match:
            field_name = find_match.group(1).strip()
            field_value = find_match.group(2).strip()
            return f"{{{field_name}}}='{field_value}'"

        return None
