# TokenRouter

A lightweight proxy for sharing LLM API access with multiple users. Each user gets their own API token and quota, with all usage tracked automatically. Built for classroom settings where students need Python API access to LLMs without their own subscriptions.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # edit with your settings
cp providers.example.json providers.json  # edit with your providers
```

## Configuration

### `.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_PASSWORD` | Yes | — | Password for the admin panel |
| `DEFAULT_MODEL` | No | `gpt-5.4` | Default model when none specified |
| `PROVIDER_TIMEOUT` | No | `120.0` | Upstream request timeout (seconds) |
| `LOG_PAYLOAD_MAX_BYTES` | No | `8192` | Integer max bytes stored per request/response payload (set `0` to disable payload logging) |
| `DATABASE_URL` | No | `sqlite:///./data/tokenrouter.db` | Database location |
| `PUBLIC_API_URL` | No | — | Public URL shown to users |
| `ENABLE_API_DOCS` | No | `false` | Enable Swagger docs at `/docs` |
| `REGISTRATION_ENABLED` | No | `true` | Allow user self-registration |
| `REGISTRATION_ACCESS_CODES` | No | — | Comma-separated access codes |
| `ALLOWED_EMAIL_DOMAINS` | No | `ln.hk,ln.edu.hk` | Allowed email domains |
| `DEFAULT_REGISTRATION_QUOTA` | No | `500000` | Default token quota for new users |

### `providers.json`

```json
{
  "default_provider": "openai",
  "default_model": "gpt-5",
  "providers": {
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-your-key",
      "models": ["gpt-5*", "o3-*", "o4-*"]
    }
  }
}
```

- `default_model` — When a request uses model name `"default"` or `"default-model"`, it is replaced with this value before routing. This is useful for IDE tool use (e.g., Cursor) where the IDE may modify the request schema based on recognized model names; using `"default-model"` prevents this.

## Running

```bash
./start.sh          # start in background
./stop.sh           # stop the server
```

Or run directly:

```bash
python run.py
```

## Usage

Users point any OpenAI-compatible client at the proxy:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TOKEN",
    base_url="https://your-domain.com/v1"
)

response = client.chat.completions.create(
    model="claude-opus-4.5",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Admin

Access the admin panel at `/admin` to manage users, tokens, quotas, and monitor usage.

Users can self-register at `/register` (if enabled).
