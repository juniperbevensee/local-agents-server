# LM Studio Agent Toolkit

A modular Python Flask server that provides specialized agents for various tasks, all powered by your local LLM via LM Studio.

## Features

- **Modular Agent System**: Easily add new agents with a simple template
- **URL Fetcher Agent**: Fetches and summarizes web content
- **File Reader Agent**: Reads and summarizes local files (JSON, CSV, PDF, TXT, MD, LOG)
- **API Caller Agent**: Intelligently calls APIs by reading documentation and forming requests from natural language
- **HELP Endpoint**: Discover all available tools
- **OpenAI-Compatible API**: Works with any OpenAI-compatible client
- **Detailed Logging**: See exactly what's happening with each request

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- LM Studio installed and running locally
- A model loaded in LM Studio

### 2. Installation

```bash
# Clone and navigate to the repository
git clone <repository-url>
cd local-agents-server

# Starter script
./start.sh

OR

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start LM Studio

1. Open LM Studio
2. Load your preferred model
3. Start the local server (usually on port 1234)
4. Verify the API is accessible at `http://localhost:1234`

### 4. Start the Agent Server

you can mostly just run the './start.sh but otherwise

```
python agent.py
```

Server starts on `http://localhost:5000'

## Env Set-up

### 1. Create your .env file
```cp .env.example .env```

### 2. Add your keys with natural language
```
cat >> .env << EOF
Airtable personal access token: pat_yourtoken
Discord bot token: MTk4yourtoken
EOF
```

### 3. Use with agents - keys are found automatically!

`

## Available Agents

### 1. URL Fetcher Agent

Fetches content from URLs and provides summaries.

**Usage:**
```
Please summarize https://example.com/article
```

**Triggers:** Any message containing a URL

---

### 2. File Reader Agent

Reads and summarizes local files (JSON, CSV, PDF, TXT, MD, LOG).

**Usage:**
```
file:/path/to/document.pdf
Please summarize file:/Users/me/data.json
Analyze ~/Documents/report.csv
```

**Supported formats:** JSON, CSV, PDF, TXT, MD, LOG

---

### 3. API Caller Agent

Intelligently calls APIs by reading their documentation and forming requests based on natural language. The LLM reads the API docs, understands your request, forms the API call, and executes it!

**Usage:**
```
api_call: docs=https://api.github.com/docs endpoint=https://api.github.com Get my repositories
api_call: docs=https://jsonplaceholder.typicode.com/guide endpoint=https://jsonplaceholder.typicode.com Get all posts
api_call: docs=https://api.stripe.com/docs Create a customer with email test@example.com
api_call: docs=https://aleph.occrp.org/api/openapi.json key:YOUR_API_KEY_HERE Find entities related to "Trump Organization"
```

**Optional Parameters:**
- `docs=<url>` - **Required**: URL to API documentation
- `endpoint=<url>` - Optional: API base URL (auto-detected from docs if omitted)
- `key:<api_key>` - Optional: API key for authentication (automatically added to appropriate header)

**How it works:**
1. **Intelligent Documentation Crawling**: Fetches the initial docs page and automatically follows up to 10 relevant links (API reference, authentication, endpoints, examples, etc.)
2. **Context Accumulation**: Gathers information from multiple pages to build complete understanding (headers, auth methods, parameters)
3. **LLM Analysis**: Sends all documentation to LLM which understands your natural language request
4. **API Call Formation**: LLM forms the appropriate API call (method, URL, headers, body, params)
5. **Execution & Retry**: Executes the call; if it fails with a 4xx error, automatically retries with corrected parameters
6. **Formatted Results**: Returns clear, formatted response with success/failure status

**Advanced Features:**
- **OpenAPI/Swagger parsing**: Auto-detects and parses OpenAPI specs to get exact parameter names, enums, and schemas
- **Multi-page crawling**: Automatically explores documentation to find endpoints, auth methods, and examples
- **Intelligent retries**: If the first attempt fails, analyzes the error and corrects the request automatically
- **API key support**: Provide your API key via `key:` parameter - automatically added to correct auth header
- **Context-aware**: Remembers authentication requirements and headers from across multiple doc pages
- **Automatic endpoint discovery**: Can find API base URL from documentation
- Works with REST APIs that have web-based documentation pages

---

## API Endpoints

### POST `/v1/chat/completions`

Main endpoint for agent requests (OpenAI-compatible).

**Example:**
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Summarize https://news.ycombinator.com"}
    ]
  }'
```

### GET `/help`

Returns list of all available agents and how to use them.

**Example:**
```bash
curl http://localhost:5000/help
```

### GET `/health`

Health check endpoint.

### GET `/`

Root endpoint showing service info and available agents.

## Usage Examples

### Example 1: Summarize a URL

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Please summarize https://example.com/article"
    }
  ]
}
```

### Example 2: Analyze a JSON File

```json
{
  "messages": [
    {
      "role": "user",
      "content": "file:/Users/me/data/analytics.json"
    }
  ]
}
```

### Example 3: Read a PDF

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Analyze file:~/Documents/report.pdf"
    }
  ]
}
```

### Example 4: Call an API

```json
{
  "messages": [
    {
      "role": "user",
      "content": "api_call: docs=https://jsonplaceholder.typicode.com endpoint=https://jsonplaceholder.typicode.com Get all posts"
    }
  ]
}
```

## Configuration

Edit `config.py` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LM_STUDIO_HOST` | localhost | LM Studio host |
| `LM_STUDIO_PORT` | 1234 | LM Studio port |
| `LM_STUDIO_MODEL` | local-model | Model identifier |
| `FLASK_HOST` | 0.0.0.0 | Flask server host |
| `FLASK_PORT` | 5000 | Flask server port |
| `MAX_CONTENT_LENGTH` | 4000 | Max content chars to process |
| `SUMMARY_TEMPERATURE` | 0.7 | LLM temperature for summaries |
| `SUMMARY_MAX_TOKENS` | 500 | Max tokens for summaries |

## Creating Custom Agents

Want to add a new agent? It's easy!

1. **Read the template guide:** See `AGENT_TEMPLATE.md`
2. **Create your agent:** Copy the template to `agents/your_agent.py`
3. **Implement the methods:** Fill in the required methods
4. **Register it:** Add to `AGENTS` list in `agent.py`

### Quick Example

```python
from base_agent import BaseAgent

class WeatherAgent(BaseAgent):
    def get_name(self):
        return "weather"

    def get_description(self):
        return "Gets weather information"

    def get_trigger_patterns(self):
        return [r'weather', r'forecast']

    def get_usage_example(self):
        return "What's the weather in London?"

    def can_handle(self, message):
        return 'weather' in message.lower()

    def process(self, message, context):
        # Your logic here
        return "Weather data..."
```

See `AGENT_TEMPLATE.md` for complete documentation.

## Project Structure

```
local-agents-server/
├── agent.py                 # Main Flask server with routing
├── base_agent.py           # Base agent class/pattern
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── AGENT_TEMPLATE.md       # Guide for creating new agents
├── agents/
│   ├── __init__.py
│   ├── url_fetcher.py      # URL fetching agent
│   └── file_reader.py      # File reading agent
├── start.sh                # Quick start script
├── test_request.py         # Test client
└── example_request.json    # Example request
```

## How It Works

1. **Request Reception**: Flask server receives POST at `/v1/chat/completions`
2. **Agent Routing**: Router checks each agent's `can_handle()` method
3. **Agent Processing**: Matched agent's `process()` method runs
4. **LM Studio Integration**: Content sent to LM Studio for summarization
5. **Response**: Summary returned in OpenAI-compatible format

## Logging

The server provides detailed logging:

```
2025-12-05 12:20:06 - __main__ - INFO - ================================================================================
2025-12-05 12:20:06 - __main__ - INFO - Incoming Request: POST /v1/chat/completions
2025-12-05 12:20:06 - __main__ - INFO - Headers: {'Content-Type': 'application/json', ...}
2025-12-05 12:20:06 - __main__ - INFO - Body: {"messages": [...]}
2025-12-05 12:20:06 - __main__ - INFO - Routing to agent: url_fetcher
2025-12-05 12:20:06 - __main__ - INFO - URL Fetcher Agent: Processing URL: https://...
```

## Troubleshooting

**LM Studio Connection Failed:**
- Ensure LM Studio is running
- Check the local server is started in LM Studio
- Verify port (default: 1234) in `config.py`
- Test with: `curl http://localhost:1234/v1/models`

**Agent Not Triggering:**
- Check trigger patterns in agent's `get_trigger_patterns()`
- View logs to see which agent (if any) matched
- Visit `/help` to see all agents and their triggers

**File Not Found:**
- Use absolute paths: `file:/Users/me/file.txt`
- Or use `~/` for home directory: `file:~/Documents/file.txt`
- Check file permissions

**PDF Reading Failed:**
- Ensure PyPDF2 is installed: `pip install PyPDF2`
- Some PDFs may be image-based and not extractable

## Testing

```bash
# Test URL agent
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Summarize https://example.com"}]}'

# Test file agent
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "file:/path/to/file.json"}]}'

# Get help
curl http://localhost:5000/help

# Health check
curl http://localhost:5000/health
```

Or use the test script:
```bash
python test_request.py https://example.com
```

## Contributing

1. Create a new agent following `AGENT_TEMPLATE.md`
2. Test thoroughly
3. Add documentation
4. Submit a PR!

## License

See LICENSE file for details.
