# TokenRouter

TokenRouter is a lightweight proxy service that lets you share one paid LLM account with multiple teams or users. Each team gets their own API token and quota, and all usage is tracked automatically.

## Getting Started

First, install the dependencies:

```bash
pip install -r requirements.txt
```

Then start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On first run, you'll be prompted for your LLM provider's API key. The service will save it to a `.env` file for future use.

**Important:** TokenRouter is designed to be accessed remotely by multiple users. You'll typically want to deploy it on a server and make it available through a domain name (e.g., `api.qhchina.org`) using a reverse proxy or tunnel service. This allows your teams to access the service from anywhere.

As the admin, you need to specify which models your provider supports in the `.env` file. For example, the default configuration includes:

```bash
ALLOWED_MODELS=GPT-5-nano,GPT-5-mini,Gemini-2.5-flash,Gemini-2.5-pro
```

Update this list to match the models available from your LLM provider.

## Admin Panel

Open your browser to `https://api.qhchina.org/admin` (or your configured domain) to access the admin panel. You'll be prompted for the admin password (default is `admin123`, but you should change it via the `ADMIN_PASSWORD` environment variable).

From the admin panel you can create teams, set quotas, monitor usage, view request logs, and reset usage counters. Only admins can edit or delete teams - users just use their assigned tokens.

## For Users

Users interact with TokenRouter exactly like the regular OpenAI API. Just provide them with their team token and they can use this code:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TEAM_TOKEN",
    base_url="https://api.qhchina.org/v1"
)

response = client.chat.completions.create(
    model="GPT-5-nano",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

That's it! The service automatically tracks their usage and enforces their quota. When they run out of tokens, requests will be rejected until you increase their quota or reset their usage counter.

## Database

TokenRouter uses SQLite to store teams and request logs. The database is created automatically when you first start the service. You can view or edit it using tools like [DB Browser for SQLite](https://sqlitebrowser.org/) if you need to make manual changes.

## Troubleshooting

If you get a "port already in use" error, run the service on a different port: `uvicorn app.main:app --port 8001`

If users get "quota exceeded" errors, check the admin panel to see their usage and increase their quota or reset their counter.

If requests aren't working, check that your provider API key is valid and that the model names match what your provider supports.

## API Documentation

For developers who want to integrate with TokenRouter programmatically, interactive API documentation is available at `https://api.qhchina.org/docs` (or your configured domain) when the service is running.

---

Built with FastAPI and SQLAlchemy.
