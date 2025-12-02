# TokenRouter

TokenRouter is a lightweight, educational proxy service that lets you share one LLM API account with multiple teams or users. Each team gets their own API token and quota, and all usage is tracked automatically. It is useful in classroom settings, when you teach students how to work with LLMs and structured outputs via Python API access, without requiring them to have their own subscriptions.

## Getting Started

Install the dependencies:

```bash
pip install -r requirements.txt
```

Set required environment variables and start the server:

```bash
export PROVIDER_API_KEY='your-api-key-here'
export PROVIDER_BASE_URL='https://api.poe.com/v1'
export ADMIN_PASSWORD='your-secure-password'
./start_foreground.sh
```

**Helper Scripts:**
- `./check_status.sh` - Check if server is running and responding
- `./kill_ports.sh` - Kill any process using port 8000
- `./start_foreground.sh` - Start server in foreground
- `./start_background.sh` - Start server in background (logs to `logs/tokenrouter_YYYYMMDD_HHMMSS.log`)

**Configuration:**

Set environment variables to configure TokenRouter:

```bash
# Required variables (app will not start without these)
export PROVIDER_API_KEY='your-provider-api-key'
export PROVIDER_BASE_URL='https://api.poe.com/v1'
export ADMIN_PASSWORD='your-secure-password'

# Optional variables
export ALLOWED_MODELS='GPT-5-nano,GPT-5-mini,...'       # Models available from your provider
export DATABASE_URL='sqlite:///./data/tokenrouter.db'   # Database location
export HOST='0.0.0.0'                                    # Server host
export PORT='8000'                                       # Server port

# Registration (optional - for self-service user registration)
export REGISTRATION_ENABLED='true'                      # Enable user registration
export REGISTRATION_ACCESS_CODES='code1,code2,code3'  # Comma-separated list of valid registration codes
export ALLOWED_EMAIL_DOMAINS='stanford.edu,gmail.com'        # Allowed email domains
export DEFAULT_REGISTRATION_QUOTA='500000'             # Default quota for new users
export PUBLIC_API_URL='https://api.yourdomain.com/v1'     # Public API URL shown to users
```

TokenRouter is designed to be accessed remotely via a domain name (e.g., `api.yourdomain.com`) using Cloudflare Tunnel or a reverse proxy.

## User Registration

TokenRouter supports self-service user registration. Users can create their own accounts at `/register` if they have:
- An email from an allowed domain (e.g., ln.hk, ln.edu.hk)
- A valid registration access code (one of the codes configured in REGISTRATION_ACCESS_CODES)

## Admin Panel

Access the admin panel at `https://api.yourdomain.com/admin` to:
- Create teams and assign tokens
- Set and manage quotas
- Monitor usage and view request logs
- Reset usage counters

Admin password must be set via `ADMIN_PASSWORD` environment variable.

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

**Check Available Models:**
```bash
curl https://api.yourdomain.com/v1/models
```

**Check Your Quota:**
```bash
curl https://api.yourdomain.com/v1/usage/YOUR_TEAM_NAME
```

## Cloudflare Setup

If using Cloudflare Tunnel, configure a firewall rule to allow API traffic:

1. Cloudflare Dashboard → **Security** → **Firewall Rules**
2. Create rule:
   - **Field**: Hostname equals `api.yourdomain.com`
   - **Action**: Allow or Skip

## API Documentation

Interactive API docs available at `https://api.yourdomain.com/docs` when the service is running.

---

Built with FastAPI and SQLAlchemy.
