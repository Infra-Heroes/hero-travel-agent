# Configuration

Everything is set by environment variables. A template to copy is [`.env.example`](../.env.example).
Secrets (marked) never belong in a file in the repository; in a deployment they come from the
project's secrets (`secret:NAME` in `hero.toml`).

## Model

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | – | **Secret.** Missing or not starting with `sk-or-`: demo mode |
| `AGENT_MODEL` | `deepseek/deepseek-v4-flash` | model on OpenRouter; it must support JSON-schema output |
| `AGENT_EFFORT` | `medium` | reasoning effort for day plans: `off`, `low`, `medium`, `high` |
| `AGENT_EFFORT_SUGGEST` | `off` | reasoning effort for suggestions |
| `AGENT_MAX_TOKENS` | `8000` | upper bound of the answer length |
| `AGENT_TIMEOUT_SECONDS` | `120` | how long to wait for the model |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | another compatible endpoint |
| `AGENT_FAKE` | – | `1` forces demo mode |

## Facts

| Variable | Default | Purpose |
|---|---|---|
| `FACTS` | `1`, `0` in demo mode | look up weather, holidays and places |
| `FACTS_TIMEOUT_SECONDS` | `6` | timeout per lookup |

## Accounts and mail

| Variable | Default | Purpose |
|---|---|---|
| `SMTP_HOST`, `SMTP_PORT` | –, `587` | mail server for the codes; port 465 means TLS, otherwise STARTTLS |
| `SMTP_USER`, `SMTP_PASSWORD` | – | **Secrets.** Mail server login |
| `MAIL_FROM` | `Urlaubs-Agent <noreply@localhost>` | sender |
| `MAIL_BACKEND` | – | `console`: mails go to the log instead of a server (development only) |
| `ALLOWED_EMAILS`, `ALLOWED_EMAIL_DOMAINS` | empty | who may sign in, comma separated; empty means everybody |
| `SESSION_SECRET` | generated | **Secret**, 16+ characters. If unset, a random key is kept in the data directory |

Without `SMTP_HOST` and without `MAIL_BACKEND=console` nobody can sign in.

## Limits

| Variable | Default | Purpose |
|---|---|---|
| `USER_DAILY_QUERIES` | `10` | requests per person and day (suggestion, plan and refining a day count one each) |
| `AGENT_DAILY_CALLS` | `200` | requests per day in total |

## Operations

| Variable | Default | Purpose |
|---|---|---|
| `DATA_DIR` | `./data` | database and generated session key |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warning`, `error` |
| `METRICS_TOKEN` | – | **Secret.** Bearer token for `/metrics` and `/api/stats`; without it only from the machine itself |
| `REPORT_TO` | – | **Secret.** Recipient of the daily numbers report; empty means no report |
| `REPORT_HOUR_UTC` | `6` | hour the report is sent |
