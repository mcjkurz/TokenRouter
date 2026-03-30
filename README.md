# TokenRouter

A lightweight proxy for sharing LLM API access with multiple users. Each user gets their own API token and USD budget, with usage and costs tracked automatically.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp config.example.json config.json  # edit with your settings
```

## Configuration

All configuration is in `config.json`:

```json
{
  "admin_password": "your-secure-password",
  "registration": {
    "enabled": true,
    "access_codes": ["code1", "code2"],
    "allowed_email_domains": ["example.com"],
    "default_budget_usd": 5.00
  },
  "server": {
    "public_api_url": "https://your-domain.com/v1",
    "default_model": "gpt-4o",
    "provider_timeout": 120.0
  },
  "pricing": {
    "default_input_per_million": 1.00,
    "default_output_per_million": 3.00
  },
  "default_provider": "openai",
  "providers": {
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-your-key",
      "input_per_million": 2.50,
      "output_per_million": 10.00,
      "models": {
        "gpt-4o": {},
        "gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60}
      }
    }
  }
}
```

### Pricing

- Each provider has default pricing (`input_per_million`, `output_per_million`)
- Individual models can override with custom pricing
- `{}` means use provider default

## Running

```bash
./start.sh   # start in background
./stop.sh    # stop
```

Or directly: `python run.py`

## Usage

Point any OpenAI-compatible client at the proxy:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TOKEN",
    base_url="https://your-domain.com/v1"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

Check your usage:

```python
import requests
response = requests.get(f"https://your-domain.com/v1/usage/{API_KEY}")
print(response.json())
# {"budget_usd": 5.0, "used_usd": 0.12, "remaining_usd": 4.88, ...}
```

## Admin

- `/admin` — Manage users, budgets, view logs
- `/register` — User self-registration (if enabled)
