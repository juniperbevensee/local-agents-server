#!/usr/bin/env python3
"""
API Caller Agent

Intelligently calls APIs by reading their documentation and forming requests based on human language.

Usage:
    api_call: docs=https://api.example.com/docs endpoint=https://api.example.com Get the list of users
    api_call: docs=https://stripe.com/docs/api Create a new customer with email test@example.com
"""

import re
import requests
import json
from bs4 import BeautifulSoup
import logging
from typing import Dict, Any, Optional, Tuple
import sys
import os

# Add parent directory to path to import base_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_agent import BaseAgent
from config import (
    LM_STUDIO_URL,
    LM_STUDIO_MODEL,
    MAX_CONTENT_LENGTH,
    REQUEST_TIMEOUT,
    SUMMARY_MAX_TOKENS,
    SUMMARY_TEMPERATURE
)

logger = logging.getLogger(__name__)


class APICallerAgent(BaseAgent):
    """Agent that calls APIs intelligently using LLM to parse documentation."""

    def get_name(self) -> str:
        return "api_caller"

    def get_description(self) -> str:
        return "Calls APIs by reading documentation and forming requests from natural language"

    def get_trigger_patterns(self) -> list:
        return [
            r'api_call:',
            r'call api',
            r'api request',
            r'docs=https?://',
        ]

    def get_usage_example(self) -> str:
        return "api_call: docs=https://api.example.com/docs endpoint=https://api.example.com Get all users"

    def can_handle(self, message: str) -> bool:
        """Check if message is an API call request."""
        # Check for api_call: prefix
        if 'api_call:' in message.lower():
            return True

        # Check for docs= pattern
        if re.search(r'docs=https?://', message, re.IGNORECASE):
            return True

        return False

    def process(self, message: str, full_context: Dict[str, Any]) -> str:
        """Process API call request with intelligent retry on errors."""
        logger.info(f"API Caller Agent: Processing request")

        # Extract components from message
        docs_url, api_base_url, api_key, request_text = self._extract_request_components(message)

        if not docs_url:
            return (
                "I need the API documentation URL. Format:\n"
                "api_call: docs=https://api.example.com/docs endpoint=https://api.example.com Your request here\n\n"
                "Or:\n"
                "api_call: docs=https://api.example.com/docs Get all users (I'll try to find the API endpoint)"
            )

        if not request_text:
            return "Please specify what you want to do with the API (e.g., 'Get all users', 'Create a new customer')"

        logger.info(f"Docs URL: {docs_url}")
        logger.info(f"API Base URL: {api_base_url or 'Will extract from docs'}")
        logger.info(f"Request: {request_text}")

        # Step 1: Fetch documentation
        logger.info("Step 1: Fetching API documentation...")
        docs_content = self._fetch_documentation(docs_url)
        if docs_content.startswith("Error"):
            return docs_content

        # Step 2: Use LLM to understand the request and form API call (with retry logic)
        max_retries = 2
        api_call_info = None
        result = None
        previous_error = None

        for attempt in range(max_retries):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries - 1}...")

            # Form API call (include previous error if retrying)
            logger.info(f"Step 2.{attempt + 1}: Using LLM to {'parse documentation' if attempt == 0 else 'fix API call based on error'}...")
            api_call_info = self._form_api_call_with_llm(
                docs_content,
                request_text,
                api_base_url,
                api_key=api_key,
                previous_error=previous_error
            )

            if not api_call_info or 'error' in api_call_info:
                return f"Error forming API call: {api_call_info.get('error', 'Unknown error')}"

            # Step 3: Execute the API call
            logger.info(f"Step 3.{attempt + 1}: Executing API call...")
            logger.info(f"  Method: {api_call_info.get('method')}")
            logger.info(f"  URL: {api_call_info.get('url')}")

            result = self._execute_api_call(api_call_info)

            # Check if successful
            if result.get('success'):
                logger.info("✓ API call successful!")
                break
            else:
                # Failed - prepare error info for retry
                logger.warning(f"✗ API call failed with status {result.get('status_code')}")

                # Only retry on client errors (4xx) that might be fixable
                status_code = result.get('status_code', 0)
                if 400 <= status_code < 500 and attempt < max_retries - 1:
                    previous_error = {
                        'status_code': status_code,
                        'error_response': result.get('data'),
                        'attempted_request': {
                            'method': api_call_info.get('method'),
                            'url': api_call_info.get('url'),
                            'headers': api_call_info.get('headers'),
                            'body': api_call_info.get('body'),
                            'params': api_call_info.get('params')
                        }
                    }
                    logger.info("This looks like a parameter error. Will retry with corrected request...")
                else:
                    # Don't retry on server errors (5xx) or if out of retries
                    break

        # Step 4: Format and return response
        return self._format_response(api_call_info, result, retry_count=attempt)

    def _extract_request_components(self, message: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extract docs URL, API base URL, API key, and request text from message.

        Returns:
            (docs_url, api_base_url, api_key, request_text)
        """
        docs_url = None
        api_base_url = None
        api_key = None
        request_text = None

        # Extract docs URL
        docs_match = re.search(r'docs=(https?://[^\s]+)', message, re.IGNORECASE)
        if docs_match:
            docs_url = docs_match.group(1)

        # Extract endpoint/API base URL
        endpoint_match = re.search(r'endpoint=(https?://[^\s]+)', message, re.IGNORECASE)
        if endpoint_match:
            api_base_url = endpoint_match.group(1)

        # Extract API key
        key_match = re.search(r'key:\s*([^\s]+)', message, re.IGNORECASE)
        if key_match:
            api_key = key_match.group(1).strip()
            logger.info(f"API key provided: {api_key[:10]}..." if len(api_key) > 10 else "API key provided")

        # Extract request text (everything after the URLs and key)
        # Remove the api_call: prefix and URL/key parameters
        text = message
        text = re.sub(r'api_call:\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'docs=https?://[^\s]+\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'endpoint=https?://[^\s]+\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'key:\s*[^\s]+\s*', '', text, flags=re.IGNORECASE)

        request_text = text.strip()

        return docs_url, api_base_url, api_key, request_text

    def _fetch_documentation(self, url: str) -> str:
        """
        Fetch and extract text from documentation URL.
        Intelligently follows links to gather complete API documentation.
        Special handling for OpenAPI/Swagger JSON specs.
        """
        from urllib.parse import urljoin, urlparse

        # Check if this is an OpenAPI/Swagger JSON spec
        if url.endswith('.json') or 'openapi.json' in url or 'swagger.json' in url:
            logger.info("Detected OpenAPI JSON spec - will parse as structured API definition")
            spec_result = self._fetch_openapi_spec(url)
            if spec_result:
                return spec_result
            # If it failed, fall through to HTML parsing
            logger.info("Spec URL didn't contain valid JSON, falling back to HTML parsing")

        # Check if this is a Redoc/Swagger UI page - try to extract the spec URL
        if 'redoc' in url.lower() or 'swagger' in url.lower():
            logger.info("Detected API documentation viewer - looking for OpenAPI spec URL")
            spec_url = self._extract_openapi_spec_url(url)
            if spec_url:
                logger.info(f"Found OpenAPI spec URL: {spec_url}")
                spec_result = self._fetch_openapi_spec(spec_url)
                if spec_result:
                    return spec_result
                # If it failed, fall through to HTML parsing
                logger.info("Spec URL didn't contain valid JSON, falling back to HTML parsing")

        # For regular HTML pages, try to find OpenAPI spec links before falling back to HTML parsing
        logger.info("Searching for OpenAPI/Swagger spec links in documentation...")
        spec_url = self._find_openapi_spec_in_page(url)
        if spec_url:
            logger.info(f"Found OpenAPI spec link: {spec_url}")
            logger.info("Using structured API spec instead of HTML parsing for better accuracy")
            spec_result = self._fetch_openapi_spec(spec_url)
            if spec_result:
                return spec_result
            # If it failed, fall through to HTML parsing
            logger.info("Spec URL didn't contain valid JSON, falling back to HTML parsing")

        max_pages = 11  # Initial page + 10 additional pages
        visited_urls = set()
        docs_content = []
        links_to_visit = [url]

        logger.info(f"Starting documentation crawl from: {url}")
        logger.info(f"Will visit up to {max_pages} pages to find complete documentation")

        base_domain = urlparse(url).netloc

        for page_num in range(max_pages):
            if not links_to_visit:
                break

            current_url = links_to_visit.pop(0)

            # Skip if already visited
            if current_url in visited_urls:
                continue

            visited_urls.add(current_url)

            try:
                logger.info(f"Page {page_num + 1}/{max_pages}: Fetching {current_url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(current_url, headers=headers, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract links for potential follow-up (only from first page)
                if page_num == 0:
                    relevant_links = self._extract_relevant_links(soup, current_url, base_domain)
                    links_to_visit.extend(relevant_links[:10])  # Limit to top 10 most relevant
                    if relevant_links:
                        logger.info(f"Found {len(relevant_links)} relevant documentation links to explore")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text
                text = soup.get_text()

                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)

                # Add page marker and content
                page_title = soup.title.string if soup.title else "Documentation Page"
                docs_content.append(f"\n{'='*60}\n")
                docs_content.append(f"Page: {page_title}\n")
                docs_content.append(f"URL: {current_url}\n")
                docs_content.append(f"{'='*60}\n\n")
                docs_content.append(text)

            except Exception as e:
                logger.warning(f"Error fetching {current_url}: {e}")
                continue

        # Combine all documentation
        combined_docs = '\n\n'.join(docs_content)

        # Limit total size
        if len(combined_docs) > MAX_CONTENT_LENGTH * 2:  # Allow 2x for multiple pages
            combined_docs = combined_docs[:MAX_CONTENT_LENGTH * 2] + "\n\n[Documentation truncated - showing first portion]"

        logger.info(f"Successfully fetched {len(visited_urls)} pages, total {len(combined_docs)} characters")
        return combined_docs

    def _extract_relevant_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> list:
        """
        Extract relevant documentation links from a page.
        Prioritizes links that likely contain API information.
        """
        from urllib.parse import urljoin, urlparse

        relevant_keywords = [
            'api', 'endpoint', 'reference', 'auth', 'authentication',
            'request', 'response', 'parameter', 'method', 'rest',
            'guide', 'tutorial', 'example', 'usage', 'getting-started',
            'quickstart', 'integration', 'sdk'
        ]

        links = []
        seen_urls = set()

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)

            # Parse URL
            parsed = urlparse(absolute_url)

            # Only follow links on the same domain
            if parsed.netloc != base_domain:
                continue

            # Skip anchors, downloads, etc
            if parsed.fragment or any(ext in parsed.path.lower() for ext in ['.pdf', '.zip', '.tar', '.gz']):
                continue

            # Remove fragment
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"

            # Skip duplicates
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

            # Check if link text or URL contains relevant keywords
            link_text = a_tag.get_text().lower()
            url_lower = clean_url.lower()

            relevance_score = 0
            for keyword in relevant_keywords:
                if keyword in link_text or keyword in url_lower:
                    relevance_score += 1

            if relevance_score > 0:
                links.append((relevance_score, clean_url))

        # Sort by relevance and return URLs
        links.sort(reverse=True, key=lambda x: x[0])
        return [url for score, url in links]

    def _find_openapi_spec_in_page(self, page_url: str) -> Optional[str]:
        """
        Search for OpenAPI/Swagger spec links in HTML documentation page.
        Looks for common spec file names in links and references.
        """
        try:
            from urllib.parse import urljoin

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(page_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Common OpenAPI spec file patterns
            spec_patterns = [
                'openapi.json',
                'swagger.json',
                'api-docs.json',
                'openapi.yaml',
                'swagger.yaml',
                'api-spec.json',
                'api.json',
            ]

            # Look for links in <a> tags
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].lower()
                for pattern in spec_patterns:
                    if pattern in href:
                        spec_url = a_tag['href']
                        # Make absolute if relative
                        if not spec_url.startswith('http'):
                            spec_url = urljoin(page_url, spec_url)
                        logger.info(f"Found spec link in <a> tag: {spec_url}")
                        return spec_url

            # Look for spec URLs in script tags or inline JavaScript
            for script in soup.find_all('script'):
                if script.string:
                    for pattern in spec_patterns:
                        if pattern in script.string:
                            # Try to extract the URL
                            matches = re.findall(r'["\']([^"\']*' + re.escape(pattern) + r')["\']', script.string)
                            if matches:
                                spec_url = matches[0]
                                if not spec_url.startswith('http'):
                                    spec_url = urljoin(page_url, spec_url)
                                logger.info(f"Found spec URL in script: {spec_url}")
                                return spec_url

            # Look in the page text/content for spec URLs
            page_text = soup.get_text()
            for pattern in spec_patterns:
                # Look for URLs containing the pattern
                url_match = re.search(r'https?://[^\s<>"{}|\\^`\[\]]*' + re.escape(pattern), page_text)
                if url_match:
                    spec_url = url_match.group(0)
                    logger.info(f"Found spec URL in page text: {spec_url}")
                    return spec_url

            # Try common spec URL locations relative to the docs page
            base_url = page_url.split('/docs')[0] if '/docs' in page_url else page_url.rsplit('/', 1)[0]
            common_locations = [
                '/openapi.json',
                '/swagger.json',
                '/api/openapi.json',
                '/api/swagger.json',
                '/docs/openapi.json',
                '/docs/swagger.json',
            ]

            for location in common_locations:
                potential_spec_url = base_url + location
                try:
                    # Quick HEAD request to check if it exists
                    head_response = requests.head(potential_spec_url, headers=headers, timeout=5)
                    if head_response.status_code == 200:
                        logger.info(f"Found spec at common location: {potential_spec_url}")
                        return potential_spec_url
                except:
                    continue

            return None
        except Exception as e:
            logger.warning(f"Error searching for OpenAPI spec: {e}")
            return None

    def _extract_openapi_spec_url(self, page_url: str) -> Optional[str]:
        """
        Extract OpenAPI spec URL from Redoc/Swagger UI pages.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(page_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            content = response.text

            # Look for spec-url or url parameter in Redoc
            import re
            patterns = [
                r'spec-url=["\']([^"\']+)["\']',
                r'url:\s*["\']([^"\']+)["\']',
                r'url=([^&\s]+)',
                r'"specUrl":\s*"([^"]+)"',
            ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    spec_url = match.group(1)
                    # Make absolute if relative
                    if not spec_url.startswith('http'):
                        from urllib.parse import urljoin
                        spec_url = urljoin(page_url, spec_url)
                    return spec_url

            return None
        except Exception as e:
            logger.warning(f"Could not extract spec URL: {e}")
            return None

    def _fetch_openapi_spec(self, spec_url: str) -> str:
        """
        Fetch and parse OpenAPI JSON spec into readable documentation.
        Extracts endpoints, parameters, schemas, enums, etc.
        """
        try:
            logger.info(f"Fetching OpenAPI spec from: {spec_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(spec_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            spec = response.json()

            # Format the spec into readable documentation
            docs = []
            docs.append("="*60)
            docs.append("API SPECIFICATION (OpenAPI/Swagger)")
            docs.append("="*60)
            docs.append("")

            # API Info
            if 'info' in spec:
                info = spec['info']
                docs.append(f"API: {info.get('title', 'Unknown')}")
                docs.append(f"Version: {info.get('version', 'Unknown')}")
                if 'description' in info:
                    docs.append(f"Description: {info['description']}")
                docs.append("")

            # Servers/Base URLs
            if 'servers' in spec:
                docs.append("Base URLs:")
                for server in spec['servers']:
                    docs.append(f"  - {server.get('url')}")
                docs.append("")

            # Security/Authentication
            if 'securitySchemes' in spec.get('components', {}):
                docs.append("Authentication:")
                for name, scheme in spec['components']['securitySchemes'].items():
                    docs.append(f"  - {name}: {scheme.get('type')} ({scheme.get('scheme', 'N/A')})")
                docs.append("")

            # Endpoints/Paths
            if 'paths' in spec:
                docs.append("ENDPOINTS:")
                docs.append("="*60)
                for path, methods in spec['paths'].items():
                    for method, details in methods.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                            docs.append(f"\n{method.upper()} {path}")
                            if 'summary' in details:
                                docs.append(f"  Summary: {details['summary']}")
                            if 'description' in details:
                                docs.append(f"  Description: {details['description']}")

                            # Parameters
                            if 'parameters' in details:
                                docs.append("  Parameters:")
                                for param in details['parameters']:
                                    param_name = param.get('name')
                                    param_in = param.get('in')
                                    required = param.get('required', False)
                                    param_type = param.get('schema', {}).get('type', 'unknown')

                                    # Extract enum values if present
                                    enum_values = param.get('schema', {}).get('enum', [])
                                    enum_str = f" (valid values: {', '.join(map(str, enum_values))})" if enum_values else ""

                                    req_str = "[REQUIRED]" if required else "[optional]"
                                    docs.append(f"    - {param_name} ({param_in}) {req_str}: {param_type}{enum_str}")

                                    if 'description' in param:
                                        docs.append(f"      Description: {param['description']}")

                            # Request body
                            if 'requestBody' in details:
                                docs.append("  Request Body:")
                                req_body = details['requestBody']
                                if 'content' in req_body:
                                    for content_type, content_spec in req_body['content'].items():
                                        docs.append(f"    Content-Type: {content_type}")
                                        if 'schema' in content_spec:
                                            docs.append(f"    Schema: {json.dumps(content_spec['schema'], indent=6)}")

                            # Responses
                            if 'responses' in details:
                                docs.append("  Responses:")
                                for code, response in details['responses'].items():
                                    docs.append(f"    {code}: {response.get('description', 'No description')}")

            # Schemas/Models
            if 'schemas' in spec.get('components', {}):
                docs.append("\n" + "="*60)
                docs.append("DATA MODELS:")
                docs.append("="*60)
                for schema_name, schema_def in list(spec['components']['schemas'].items())[:10]:  # Limit to first 10
                    docs.append(f"\n{schema_name}:")
                    if 'properties' in schema_def:
                        docs.append("  Properties:")
                        for prop_name, prop_def in schema_def['properties'].items():
                            prop_type = prop_def.get('type', 'unknown')
                            enum_values = prop_def.get('enum', [])
                            enum_str = f" (valid values: {', '.join(map(str, enum_values))})" if enum_values else ""
                            docs.append(f"    - {prop_name}: {prop_type}{enum_str}")

            combined_docs = '\n'.join(docs)
            logger.info(f"Successfully parsed OpenAPI spec: {len(combined_docs)} characters")
            return combined_docs

        except json.JSONDecodeError as e:
            logger.warning(f"URL did not contain valid JSON spec: {e}")
            # Return None to signal that this wasn't a valid spec (will fall back to HTML parsing)
            return None
        except Exception as e:
            logger.warning(f"Could not fetch OpenAPI spec: {e}")
            # Return None to signal that spec fetch failed (will fall back to HTML parsing)
            return None

    def _form_api_call_with_llm(
        self,
        docs_content: str,
        request_text: str,
        api_base_url: Optional[str],
        api_key: Optional[str] = None,
        previous_error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to parse documentation and form an API call.
        If previous_error is provided, the LLM will attempt to fix the request.
        If api_key is provided, adds it to the Authorization header.

        Returns dict with: method, url, headers, body, params
        """
        try:
            # Build error context if this is a retry
            error_context = ""
            if previous_error:
                error_context = f"""
PREVIOUS ATTEMPT FAILED:
The previous API call failed with the following error:

Status Code: {previous_error['status_code']}

Error Response:
{json.dumps(previous_error['error_response'], indent=2)}

Failed Request:
Method: {previous_error['attempted_request']['method']}
URL: {previous_error['attempted_request']['url']}
Headers: {json.dumps(previous_error['attempted_request']['headers'], indent=2)}
Body: {json.dumps(previous_error['attempted_request']['body'], indent=2) if previous_error['attempted_request']['body'] else 'None'}
Params: {json.dumps(previous_error['attempted_request']['params'], indent=2) if previous_error['attempted_request']['params'] else 'None'}

Please analyze the error and fix the API call. Pay special attention to:
- Required vs optional parameters
- Correct parameter names (check the documentation carefully)
- Proper data types for each parameter
- Required headers

"""

            # Build a detailed prompt for the LLM
            prompt = f"""You are an API expert. Based on the API documentation below, I need you to form a valid API request.

API Documentation:
{docs_content}

{'Base API URL: ' + api_base_url if api_base_url else 'Please extract the base API URL from the documentation.'}

User Request: {request_text}

{error_context}

Please analyze the documentation and provide ONLY a JSON response (no other text) with the following structure:
{{
    "method": "GET/POST/PUT/DELETE/PATCH",
    "url": "complete URL for the API call",
    "headers": {{"Header-Name": "value"}},
    "body": {{"key": "value"}} or null,
    "params": {{"param": "value"}} or null,
    "explanation": "brief explanation of what this API call does"
}}

Important:
- Provide the complete, absolute URL
- Include all required headers (like Content-Type, Authorization if needed)
- If authentication is required, note it in headers with a placeholder like "YOUR_API_KEY"
- Return ONLY valid JSON, no markdown formatting or code blocks
- READ THE DOCUMENTATION CAREFULLY to get parameter names exactly right
"""

            payload = {
                "model": LM_STUDIO_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an API expert that reads documentation and forms valid API requests. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower temperature for more precise API call formation
                "max_tokens": 1000
            }

            logger.info("Calling LLM to form API request...")
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            llm_response = result['choices'][0]['message']['content']

            logger.info(f"LLM Response: {llm_response[:200]}...")

            # Try to parse JSON from the response
            # Sometimes LLM wraps JSON in markdown code blocks, so clean that up
            llm_response = llm_response.strip()

            # Remove markdown code block markers if present
            if llm_response.startswith('```'):
                # Remove ```json or ``` at start
                llm_response = re.sub(r'^```(?:json)?\s*', '', llm_response)
                # Remove ``` at end
                llm_response = re.sub(r'\s*```$', '', llm_response)
                llm_response = llm_response.strip()

            # Parse JSON
            api_call_info = json.loads(llm_response)

            # Add API key to headers if provided
            if api_key:
                if 'headers' not in api_call_info:
                    api_call_info['headers'] = {}

                # Add API key to Authorization header
                # Support common auth header formats
                if 'Authorization' not in api_call_info['headers']:
                    # Check if docs mention Bearer token
                    if 'bearer' in docs_content.lower():
                        api_call_info['headers']['Authorization'] = f'Bearer {api_key}'
                    # Check if docs mention API key header
                    elif 'x-api-key' in docs_content.lower():
                        api_call_info['headers']['X-API-Key'] = api_key
                    elif 'apikey' in docs_content.lower():
                        api_call_info['headers']['ApiKey'] = api_key
                    else:
                        # Default to ApiKey header
                        api_call_info['headers']['ApiKey'] = api_key

                    logger.info(f"Added API key to headers")

            logger.info("Successfully formed API call:")
            logger.info(f"  Method: {api_call_info.get('method')}")
            logger.info(f"  URL: {api_call_info.get('url')}")

            return api_call_info

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM Response was: {llm_response}")
            return {"error": f"LLM did not return valid JSON. Response: {llm_response[:200]}"}
        except Exception as e:
            logger.error(f"Error forming API call with LLM: {e}")
            return {"error": str(e)}

    def _execute_api_call(self, api_call_info: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the API call based on the formed request."""
        try:
            method = api_call_info.get('method', 'GET').upper()
            url = api_call_info.get('url')
            headers = api_call_info.get('headers', {})
            body = api_call_info.get('body')
            params = api_call_info.get('params')

            # Build the complete URL with query parameters for logging and display
            from urllib.parse import urlencode
            full_url = url
            if params:
                param_string = urlencode(params)
                full_url = f"{url}?{param_string}"

            logger.info(f"Executing {method} {full_url}")

            # Make the API call
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                params=params if params else None,
                timeout=REQUEST_TIMEOUT
            )

            # Try to parse response as JSON, otherwise return text
            try:
                response_data = response.json()
            except:
                response_data = response.text

            return {
                "status_code": response.status_code,
                "success": response.ok,
                "data": response_data,
                "headers": dict(response.headers),
                "full_url": full_url  # Include the complete URL with params
            }

        except Exception as e:
            logger.error(f"Error executing API call: {e}")
            return {
                "status_code": 0,
                "success": False,
                "error": str(e)
            }

    def _format_response(self, api_call_info: Dict[str, Any], result: Dict[str, Any], retry_count: int = 0) -> str:
        """Format the API response for the user."""
        response = "API Call Result\n" + "="*60 + "\n\n"

        # Show retry info if retried
        if retry_count > 0:
            if result.get('success'):
                response += f"✓ **Success after {retry_count} {'retry' if retry_count == 1 else 'retries'}!**\n"
                response += f"The LLM analyzed the error and corrected the API call.\n\n"
            else:
                response += f"⚠️ Failed after {retry_count} {'retry' if retry_count == 1 else 'retries'}.\n\n"

        # Show what was called
        response += f"**Request Made:**\n"
        response += f"  Method: {api_call_info.get('method')}\n"

        # Show the full URL with query parameters if available
        full_url = result.get('full_url', api_call_info.get('url'))
        response += f"  URL: {full_url}\n"

        if api_call_info.get('explanation'):
            response += f"  Purpose: {api_call_info.get('explanation')}\n"

        response += "\n"

        # Show result
        if result.get('success'):
            response += f"**Status:** ✓ Success ({result.get('status_code')})\n\n"
            response += f"**Response:**\n"

            # Pretty print the data
            data = result.get('data')
            if isinstance(data, (dict, list)):
                response += "```json\n"
                response += json.dumps(data, indent=2)
                response += "\n```\n"
            else:
                response += str(data)[:1000]  # Limit text responses
                if len(str(data)) > 1000:
                    response += "\n\n[Response truncated]"

        else:
            response += f"**Status:** ✗ Failed ({result.get('status_code', 'N/A')})\n\n"
            response += f"**Error:**\n{result.get('error', 'Unknown error')}\n"

            if result.get('data'):
                response += f"\n**Response:**\n{json.dumps(result.get('data'), indent=2)[:500]}\n"

        # Add helpful notes
        response += "\n" + "="*60 + "\n"

        # Check for auth placeholders
        if api_call_info.get('headers', {}).get('Authorization') == 'YOUR_API_KEY':
            response += "\n⚠️  Note: This API requires authentication. The placeholder 'YOUR_API_KEY' was used.\n"

        return response
