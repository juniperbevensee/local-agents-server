# Local Agents Server

A Python Flask agent that integrates with LM Studio to fetch URLs and generate summaries.

## Features

- Receives requests via Flask server in OpenAI-compatible format
- Extracts URLs from conversation messages
- Fetches website content and cleans HTML
- Summarizes content using local LLM via LM Studio
- Returns summaries in OpenAI-compatible response format

## Prerequisites

- Python 3.8 or higher
- LM Studio installed and running locally
- A model loaded in LM Studio

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd local-agents-server
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to adjust settings, or set environment variables:

- `LM_STUDIO_HOST`: LM Studio host (default: localhost)
- `LM_STUDIO_PORT`: LM Studio port (default: 1234)
- `LM_STUDIO_MODEL`: Model name (default: local-model)
- `FLASK_PORT`: Flask server port (default: 5000)

## Usage

### 1. Start LM Studio

1. Open LM Studio
2. Load your preferred model
3. Start the local server (usually on port 1234)
4. Ensure the API is accessible at `http://localhost:1234`

### 2. Start the Flask Agent

```bash
python agent.py
```

The server will start on `http://localhost:5000`

### 3. Send Requests

Send POST requests to `http://localhost:5000/v1/chat/completions` with the following format:

```json
{
  "model": "openai/gpt-oss-20b",
  "messages": [
    {
      "role": "user",
      "content": "Please summarize this article: https://example.com/article"
    }
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 4096
  }
}
```

The agent will:
1. Extract the URL from the last message
2. Fetch the website content
3. Send it to LM Studio for summarization
4. Return the summary in OpenAI-compatible format

### Example with cURL

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [
      {
        "role": "user",
        "content": "Summarize https://example.com/article"
      }
    ]
  }'
```

## How It Works

1. **Request Reception**: Flask server receives POST request at `/v1/chat/completions`
2. **URL Extraction**: Regex extracts URL from the last message content
3. **Content Fetching**:
   - HTTP request to the URL
   - HTML parsing with BeautifulSoup
   - Text extraction and cleaning
4. **Summarization**:
   - Content sent to LM Studio's local API
   - LLM generates summary
5. **Response**: Summary returned in OpenAI-compatible format

## API Endpoints

### POST `/v1/chat/completions`
Main endpoint for URL summarization requests.

**Request Body:**
- `messages`: Array of message objects
- `model`: Model identifier (optional)
- `stream`: Boolean for streaming (default: false)

**Response:**
OpenAI-compatible chat completion response with summary

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "url-fetch-summarize-agent"
}
```

## Integrating with LM Studio

### Option 1: Use as Custom Agent

In your LM Studio workflow, configure this server as a custom agent endpoint:
- Agent URL: `http://localhost:5000/v1/chat/completions`
- The agent will intercept URL requests and provide summaries

### Option 2: Direct API Calls

Make direct API calls from your application to this server instead of LM Studio for URL summarization tasks.

## Troubleshooting

**LM Studio Connection Failed:**
- Ensure LM Studio is running
- Check that the local server is started in LM Studio
- Verify the port (default: 1234) in `config.py`

**URL Fetching Failed:**
- Some websites block automated requests
- Check your internet connection
- Try with different URLs

**Summarization Quality:**
- Adjust temperature in `config.py`
- Try different models in LM Studio
- Modify the prompt in `agent.py` for better results

## Development

To modify the agent:

1. Edit `agent.py` for core logic
2. Update `config.py` for configuration options
3. Add new dependencies to `requirements.txt`

## License

See LICENSE file for details.
