# LiteLLM Integration Guide

This toolkit now supports **LiteLLM**, allowing you to use any LLM provider (OpenAI, Anthropic, Azure, Cohere, etc.) in addition to the default LM Studio local inference.

## What is LiteLLM?

[LiteLLM](https://docs.litellm.ai/docs/) is a unified interface for 100+ LLM providers. It allows you to switch between providers by simply changing environment variables, without modifying code.

## Quick Start

### 1. Install LiteLLM (Optional)

```bash
# Uncomment the litellm line in requirements.txt, then:
pip install litellm
```

### 2. Set Environment Variables

**For LM Studio (Default - No Setup Required):**
```bash
# Already configured to use localhost:1234 by default
export LLM_PROVIDER="lm_studio"  # This is the default
```

**For OpenAI:**
```bash
export LLM_PROVIDER="litellm"
export LITELLM_MODEL="gpt-4"
export OPENAI_API_KEY="sk-..."
```

**For Anthropic Claude:**
```bash
export LLM_PROVIDER="litellm"
export LITELLM_MODEL="claude-3-opus-20240229"
export ANTHROPIC_API_KEY="sk-ant-..."
```

**For Azure OpenAI:**
```bash
export LLM_PROVIDER="litellm"
export LITELLM_MODEL="azure/gpt-4"
export AZURE_API_KEY="..."
export AZURE_API_BASE="https://your-resource.openai.azure.com"
export AZURE_API_VERSION="2023-05-15"
```

### 3. Start the Server

```bash
python agent.py
```

The toolkit will automatically use your configured LLM provider!

## Supported Providers

LiteLLM supports 100+ providers. Here are some popular ones:

| Provider | Model Example | Required Env Vars |
|----------|--------------|-------------------|
| **OpenAI** | `gpt-4`, `gpt-3.5-turbo` | `OPENAI_API_KEY` |
| **Anthropic** | `claude-3-opus-20240229`, `claude-3-sonnet-20240229` | `ANTHROPIC_API_KEY` |
| **Azure OpenAI** | `azure/gpt-4` | `AZURE_API_KEY`, `AZURE_API_BASE` |
| **Google VertexAI** | `vertex_ai/gemini-pro` | `VERTEXAI_PROJECT`, `VERTEXAI_LOCATION` |
| **Cohere** | `command-nightly` | `COHERE_API_KEY` |
| **Replicate** | `replicate/llama-2-70b-chat` | `REPLICATE_API_KEY` |
| **Hugging Face** | `huggingface/...` | `HUGGINGFACE_API_KEY` |
| **LM Studio** | `local-model` | None (default) |

See the full list: https://docs.litellm.ai/docs/providers

## Configuration Options

All configuration is in `config.py` or via environment variables:

```bash
# Choose provider
export LLM_PROVIDER="litellm"  # or "lm_studio" (default)

# LiteLLM-specific
export LITELLM_MODEL="gpt-4"               # Model name/identifier
export LITELLM_API_BASE="https://..."     # Optional: custom API base URL

# LM Studio-specific (default provider)
export LM_STUDIO_HOST="localhost"         # Default: localhost
export LM_STUDIO_PORT="1234"              # Default: 1234
export LM_STUDIO_MODEL="local-model"      # Default: local-model
```

## How It Works

The toolkit uses a unified `llm_client.py` module that abstracts LLM calls:

```python
from llm_client import chat_completion

# This works with any provider!
response = chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=500
)
```

The `llm_client` automatically routes to the configured provider (LM Studio or LiteLLM).

## Fallback Behavior

- If `LLM_PROVIDER=litellm` but LiteLLM is not installed, the system automatically falls back to LM Studio
- If LiteLLM is configured but API calls fail, you'll get clear error messages

## Examples

### Example 1: Using OpenAI GPT-4

```bash
# Set environment
export LLM_PROVIDER="litellm"
export LITELLM_MODEL="gpt-4"
export OPENAI_API_KEY="sk-..."

# Start server
python agent.py

# Make a request (in another terminal)
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "https://github.com/anthropics Summarize this page"}
    ]
  }'
```

### Example 2: Using Anthropic Claude

```bash
# Set environment
export LLM_PROVIDER="litellm"
export LITELLM_MODEL="claude-3-sonnet-20240229"
export ANTHROPIC_API_KEY="sk-ant-..."

# Start server
python agent.py
```

### Example 3: Switching Back to LM Studio

```bash
# Just unset or change the provider
export LLM_PROVIDER="lm_studio"

# Or remove the env var entirely
unset LLM_PROVIDER

# Start server
python agent.py
```

## Cost Considerations

When using cloud providers through LiteLLM:

- **OpenAI GPT-4**: ~$0.03-0.06 per 1K tokens
- **Anthropic Claude 3 Opus**: ~$0.015-0.075 per 1K tokens
- **Azure OpenAI**: Varies by region and agreement
- **LM Studio**: Free (local inference)

Monitor your API usage through your provider's dashboard!

## Troubleshooting

**LiteLLM not found:**
```bash
# Install it
pip install litellm
```

**API key errors:**
```bash
# Make sure the correct env var is set for your provider
echo $OPENAI_API_KEY  # For OpenAI
echo $ANTHROPIC_API_KEY  # For Anthropic
```

**Model not found:**
```bash
# Check the exact model name for your provider
# See: https://docs.litellm.ai/docs/providers
```

**Falls back to LM Studio unexpectedly:**
- Check that `LLM_PROVIDER="litellm"` is set
- Verify LiteLLM is installed: `pip list | grep litellm`

## Advanced: Custom LLM Client

You can create custom LLM client instances:

```python
from llm_client import LLMClient

# Force LiteLLM for this specific call
client = LLMClient(provider='litellm')
response = client.chat_completion(messages=[...])

# Force LM Studio
client = LLMClient(provider='lm_studio')
response = client.chat_completion(messages=[...])
```

## Resources

- **LiteLLM Documentation**: https://docs.litellm.ai/docs/
- **Supported Providers**: https://docs.litellm.ai/docs/providers
- **LiteLLM GitHub**: https://github.com/BerriAI/litellm

---

**Questions?** Open an issue or check the LiteLLM documentation.
