# Credential Manager Guide

The agent toolkit includes a secure credential manager that stores API keys and secrets in a `.env` file with natural language support.

## Quick Start

### 1. Create Your .env File

```bash
# Copy the example template
cp .env.example .env

# Edit with your API keys
nano .env  # or use your favorite editor
```

### 2. Add Your API Keys

The `.env` file supports both **standard format** and **natural language format**:

**Standard Format:**
```bash
OPENAI_API_KEY=sk-abc123...
AIRTABLE_TOKEN=pat_xyz789...
```

**Natural Language Format (Recommended):**
```bash
OpenAI API key: sk-abc123...
Airtable personal access token: pat_xyz789...
Discord bot token: MTk4NjIy...
GitHub personal access token: ghp_abc123...
Stripe API key: sk_live_xyz...
```

### 3. Use with Agents

The credential manager automatically provides API keys to agents based on the API you're calling:

```bash
# Example: Calling Airtable API
# Agent automatically finds "Airtable personal access token" from .env
api_call: docs=https://airtable.com/developers/web/api Get records from base appXYZ table tblABC
```

## How It Works

### Fuzzy Matching

The credential manager uses intelligent fuzzy matching to find the right API key:

| You write in .env | Agent searches for | Match? |
|-------------------|-------------------|--------|
| `Airtable personal access token: pat123` | "airtable" | ✅ Yes |
| `Discord bot token: MTk4...` | "discord" | ✅ Yes |
| `Discord bot token: MTk4...` | "discord bot" | ✅ Yes |
| `GitHub API token: ghp_abc` | "github" | ✅ Yes |
| `OPENAI_API_KEY=sk-abc` | "openai" | ✅ Yes |
| `Stripe secret key: sk_live_xyz` | "stripe" | ✅ Yes |

**Matching Strategy:**
1. Exact match (case-insensitive)
2. Partial match (search term in key name)
3. Keyword match (all words appear in key)
4. Reverse partial (key in search term)

### Automatic Platform Detection

When you make an API call, the agent automatically detects the platform from the documentation URL:

| API Documentation URL | Detected Platform | Searches For |
|-----------------------|-------------------|--------------|
| `https://airtable.com/developers/web/api/...` | "airtable" | Airtable credentials |
| `https://discord.com/developers/docs/...` | "discord" | Discord credentials |
| `https://docs.github.com/en/rest/...` | "github" | GitHub credentials |
| `https://stripe.com/docs/api/...` | "stripe" | Stripe credentials |
| `https://platform.openai.com/docs/api-reference/...` | "openai" | OpenAI credentials |

### Priority Order

The agent searches for API keys in this order:

1. **Explicit key in request** - `api_call: ... key:abc123 ...`
2. **Credential manager (.env file)** - Natural language or standard format
3. **System messages** - Keys provided in chat context
4. **Prompt** - Falls back to asking user

## Examples

### Example 1: Airtable API

**.env file:**
```bash
Airtable personal access token: patAbc123XyzDefGhi789
```

**Request:**
```bash
api_call: docs=https://airtable.com/developers/web/api Get records from base appXYZ
```

**Result:** ✅ Agent finds and uses `patAbc123XyzDefGhi789`

---

### Example 2: Discord Bot

**.env file:**
```bash
Discord bot token: MTk4NjIyMDk3MTc1MjAzMzI4.GnBYPQ.abcd1234...
```

**Request:**
```bash
api_call: docs=https://discord.com/developers/docs Send message to channel 123456
```

**Result:** ✅ Agent finds and uses the Discord token

---

### Example 3: Multiple GitHub Tokens

**.env file:**
```bash
GitHub personal access token: ghp_personal_abc123
GitHub work token: ghp_work_xyz789
```

**Request:**
```bash
api_call: docs=https://docs.github.com/en/rest List my repositories
```

**Result:** ✅ Agent finds first matching token (`ghp_personal_abc123`)

**Tip:** Use more specific names for multiple tokens:
```bash
GitHub personal token: ghp_personal_abc123
GitHub work token: ghp_work_xyz789
```

---

### Example 4: Custom API

**.env file:**
```bash
My Custom Service API key: custom_key_abc123
Internal Tool authentication token: internal_xyz789
```

**Request:**
```bash
api_call: docs=https://mycustomservice.com/api/docs Get user data
```

**Result:** ✅ Agent searches for "mycustomservice" and finds matching credential

## Security Features

### 🔒 Automatic Secret Masking

All API keys are automatically masked in logs:

```
✓ Found API key in credential manager for: airtable (pat_...Ghi789)
```

### 🔒 .gitignore Protection

The `.env` file is automatically excluded from git:

```bash
# .gitignore includes
.env
*.env
!.env.example  # Template is safe to commit
```

### 🔒 No Hardcoded Secrets

All secrets live in `.env`, never in code or system prompts.

## Advanced Usage

### Manual Credential Lookup

You can also use the credential manager in your own code:

```python
from credential_manager import get_credential, mask_secret

# Get credential
api_key = get_credential("airtable")
if api_key:
    print(f"Found key: {mask_secret(api_key)}")

# Check if credential exists
if has_credential("stripe"):
    print("Stripe API key is configured")

# List all available credentials (names only)
creds = list_credential_names()
print(f"Available credentials: {creds}")
```

### Reload Credentials

If you modify `.env` while the server is running:

```python
from credential_manager import reload_credentials

# Reload .env file
reload_credentials()
```

## Troubleshooting

### ❌ "No API key found in credential manager"

**Solution:**
1. Check that `.env` file exists in project root
2. Verify the credential name matches the platform
3. Make sure there's no typo in the key name
4. Check the key has a value (not empty or commented out)

**Example Fix:**
```bash
# ❌ Wrong - commented out
# Airtable personal access token: pat123

# ✅ Correct
Airtable personal access token: pat123
```

### ❌ "Credential exists but agent doesn't use it"

**Solution:**
1. Check the API documentation URL is correct
2. Platform detection might not match your credential name
3. Try using a more specific credential name

**Example:**
```bash
# If docs URL is https://api.notion.com/v1/...
# Make sure credential name includes "notion"

Notion API key: secret_abc123  # ✅ Will match
```

### ❌ "API call fails with authentication error"

**Solution:**
1. Verify the API key value is correct
2. Check key hasn't expired
3. Ensure key has required permissions
4. Check if API requires different auth header format

## Best Practices

### ✅ Use Natural Language Names

```bash
# ✅ Good - clear and specific
Airtable personal access token: pat123
Discord production bot token: MTk4...
Stripe live secret key: sk_live_abc

# ❌ Less clear
API_KEY_1: pat123
TOKEN: MTk4...
KEY: sk_live_abc
```

### ✅ Group Related Credentials

```bash
# ============ Airtable ============
Airtable personal access token: pat_personal_123
Airtable work token: pat_work_456

# ============ Discord ============
Discord bot token: MTk4...
Discord webhook URL: https://discord.com/api/webhooks/...
```

### ✅ Add Comments for Context

```bash
# Production Stripe key (live payments)
Stripe API key: sk_live_abc123

# Development Stripe key (testing only)
Stripe test key: sk_test_xyz789
```

### ✅ Never Commit .env

Always use `.env.example` for templates, never commit actual `.env` file:

```bash
# ❌ DON'T DO THIS
git add .env

# ✅ DO THIS
cp .env.example .env
# Edit .env with your keys
# .env is gitignored automatically
```

## Supported Platforms

The credential manager works with any API. Common platforms auto-detected:

- ✅ Airtable
- ✅ Discord
- ✅ GitHub
- ✅ Stripe
- ✅ OpenAI
- ✅ Anthropic
- ✅ Notion
- ✅ Slack
- ✅ Google
- ✅ Twitter/X
- ✅ Any custom API

## Migration from System Messages

**Before (system messages):**
```
System: Airtable base_id: appXYZ, table_id: tblABC, api_key: pat123
User: Get records from Airtable
```

**After (.env file):**
```bash
# .env
Airtable personal access token: pat123
Airtable base id: appXYZ
Airtable table id: tblABC
```

```
User: api_call: docs=https://airtable.com/developers/web/api Get records
```

**Benefits:**
- ✅ Secrets never in chat history
- ✅ Easier to manage and rotate keys
- ✅ Works across all sessions
- ✅ Secure and gitignored

---

**Need help?** Check the `.env.example` file for a complete template with all common API platforms.
