# TokenRouter

TokenRouter is a lightweight, educational proxy service that lets you share one LLM API account with multiple teams or users. Each team gets their own API token and quota, and all usage is tracked automatically. It is useful in classroom settings, when you teach students how to work with LLMs and structured outputs via Python API access, without requiring them to have their own subscriptions.

## Getting Started

1. **Create and activate a virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env` with your configuration. Required settings:

```
PROVIDER_API_KEY=your-api-key-here
PROVIDER_BASE_URL=https://api.poe.com/v1
ADMIN_PASSWORD=your-secure-password
```

3. **Start the server:**

```bash
./start.sh
```

## Scripts

| Script | Description |
|--------|-------------|
| `./start.sh` | Start server in background (logs to `logs/tokenrouter_YYYYMMDD_HHMMSS.log`) |
| `./stop.sh` | Stop the running server |
| `./check_status.sh` | Check if server is running and responding |

## Configuration

All configuration is done through the `.env` file. See `.env.example` for all available options.

**Required Settings:**

| Variable | Description |
|----------|-------------|
| `PROVIDER_API_KEY` | API key for your upstream LLM provider |
| `PROVIDER_BASE_URL` | Base URL for the provider API (e.g., `https://api.poe.com/v1`) |
| `ADMIN_PASSWORD` | Password for admin panel authentication |

**Optional Settings:**

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Server bind address (use `0.0.0.0` for external access) |
| `PORT` | `8000` | Server port |
| `PUBLIC_API_URL` | `http://localhost:8000` | Public URL shown to users |
| `DEFAULT_MODEL` | `GPT-5-nano` | Default model when none specified |
| `ALLOWED_MODELS` | (see .env.example) | Comma-separated list of allowed models |
| `PROVIDER_TIMEOUT` | `120.0` | Timeout for provider requests (seconds) |
| `DATABASE_URL` | `sqlite:///./data/tokenrouter.db` | Database location |
| `ENABLE_API_DOCS` | `false` | Enable Swagger docs at `/docs` |

**Registration Settings:**

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRATION_ENABLED` | `true` | Enable user self-registration |
| `REGISTRATION_ACCESS_CODES` | (empty) | Comma-separated access codes for registration |
| `ALLOWED_EMAIL_DOMAINS` | `ln.hk,ln.edu.hk` | Allowed email domains |
| `DEFAULT_REGISTRATION_QUOTA` | `500000` | Default token quota for new users |

## User Registration

TokenRouter supports self-service user registration. Users can create their own accounts at `/register` if they have:
- An email from an allowed domain (configured in `ALLOWED_EMAIL_DOMAINS`)
- A valid registration access code (if `REGISTRATION_ACCESS_CODES` is configured)

## Admin Panel

Access the admin panel at `https://yourdomain.com/admin` to:
- Create teams and assign tokens
- Set and manage quotas
- Monitor usage and view request logs
- Reset usage counters

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

**Check Available Models:**
```bash
curl https://api.yourdomain.com/v1/models
```

**Check Your Quota:**
```bash
curl https://api.yourdomain.com/v1/usage/YOUR_TEAM_NAME
```

## Deployment

TokenRouter is designed to be accessed remotely via a domain name (e.g., `api.yourdomain.com`) using Cloudflare Tunnel or a reverse proxy.

**Cloudflare Setup:**

If using Cloudflare Tunnel with Bot Protection enabled, you may need to configure a firewall rule to allow API traffic:

1. Cloudflare Dashboard → **Security** → **WAF**
2. Create a rule to skip or allow requests to your API hostname
3. Consider disabling "Browser Integrity Check" for `/v1/*` paths to allow programmatic API clients

---

Built with FastAPI and SQLAlchemy.
