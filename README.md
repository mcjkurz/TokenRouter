# TokenRouter

TokenRouter is a lightweight proxy service that lets you share one paid LLM account with multiple teams or users. Each team gets their own API token and quota, and all usage is tracked automatically. It's useful in classroom settings, teaching students how to work with LLMs and structured outputs via Python API access, without requiring them to purchase their own separate accounts.

## Getting Started

Install the dependencies:

```bash
pip install -r requirements.txt
```

Set your LLM provider's API key, configure admin password, and start the server:

```bash
export PROVIDER_API_KEY='your-api-key-here'
export ADMIN_PASSWORD='your-secure-password'
./start_foreground.sh
```

**Helper Scripts:**
- `./kill_ports.sh` - Kill any process using port 8000
- `./start_foreground.sh` - Start server in foreground
- `./start_background.sh` - Start server in background (logs to `tokenrouter.log`)

**Configuration:**

Set environment variables to customize TokenRouter:

```bash
export PROVIDER_API_KEY='your-provider-api-key'         # Required
export PROVIDER_BASE_URL='https://api.poe.com/v1'       # Your LLM provider endpoint
export ALLOWED_MODELS='GPT-5-nano,GPT-5-mini,...'       # Models available from your provider
export ADMIN_PASSWORD='your-secure-password'            # Default: admin123
```

TokenRouter is designed to be accessed remotely via a domain name (e.g., `api.yourdomain.com`) using Cloudflare Tunnel or a reverse proxy.

## Admin Panel

Access the admin panel at `https://api.yourdomain.com/admin` to:
- Create teams and assign tokens
- Set and manage quotas
- Monitor usage and view request logs
- Reset usage counters

Default admin password is `admin123` (change via `ADMIN_PASSWORD` environment variable).

## For Users

Users interact with TokenRouter using the standard OpenAI API:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TEAM_TOKEN",
    base_url="https://api.yourdomain.com/v1"
)

response = client.chat.completions.create(
    model="GPT-5-nano",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

The service automatically tracks usage and enforces quotas.

## Cloudflare Setup

If using Cloudflare Tunnel, configure a firewall rule to allow API traffic:

1. Cloudflare Dashboard → **Security** → **Firewall Rules**
2. Create rule:
   - **Field**: Hostname equals `api.yourdomain.com`
   - **Action**: Allow or Skip

## Troubleshooting

- **Port already in use**: Run `./kill_ports.sh` or use a different port
- **Quota exceeded**: Check usage in admin panel and increase quota or reset counter
- **Invalid API key**: Verify `PROVIDER_API_KEY` is set correctly

## API Documentation

Interactive API docs available at `https://api.yourdomain.com/docs` when the service is running.

---

Built with FastAPI and SQLAlchemy.
