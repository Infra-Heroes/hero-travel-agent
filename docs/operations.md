# Operations

## Deploying

The agent runs on [InfraHeroes](https://infra-heroes.de) as a MicroVM. `hero.toml` describes all
the deployment needs: size, port, health check, the volume, the environment and which values come
from the project's secrets.

| Step | Where |
|---|---|
| Check pull requests (lint, types, tests, bandit, pip-audit) | Woodpecker, `.woodpecker/pipeline.yml` |
| Deploy on every push to `main` | GitHub Actions, `.github/workflows/deploy.yml`, with [infra-heroes/deploy-action](https://github.com/Infra-Heroes/deploy-action) |

The workflow needs a secret `HERO_TOKEN`: a deploy token that reaches only this project.

```bash
heroctl tokens create --name github-actions --scope deploy --project urlaubs-agent
```

### Once per project

```bash
heroctl volumes create urlaubs-data --size 1 --project urlaubs-agent
heroctl secrets set OPENROUTER_API_KEY --project urlaubs-agent
# likewise SMTP_HOST, SMTP_USER, SMTP_PASSWORD, METRICS_TOKEN, SESSION_SECRET, REPORT_TO
```

Keep `SESSION_SECRET` when moving the app, or everybody is signed out.

### Volume and permissions

The volume belongs to root at start. `docker-entrypoint.sh` hands `/data` to the user `agent` and
starts the server without privileges. With a volume there is exactly one replica and no
scale-to-zero.

### Custom domain

`custom_domains` in `hero.toml`, with `verify_domains = true`. DNS: a CNAME of the subdomain to
`ingress.infra-heroes.de.` and the TXT record `heroctl domains challenge` shows.

## Limits

Every person has `USER_DAILY_QUERIES` requests a day, the agent `AGENT_DAILY_CALLS` in total. The
page shows how many are left. When the total is used up, the agent says so instead of running up
costs.

## Numbers and monitoring

- `GET /healthz`: liveness for the health check.
- `GET /metrics` (bearer `METRICS_TOKEN`): users, active and new users today, requests by kind and
  result, ratings, codes and sign-ins, model response time, tokens and the cost OpenRouter reports.
  No address and no code appears in any metric.
- `GET /api/stats` (protected the same way): numbers per day.
- A daily report to `REPORT_TO`, numbers only.
- Grafana dashboard: `deploy/observability/grafana/dashboards/travel-agent.json`.

All of it locally:

```bash
docker compose -f deploy/observability/docker-compose.yml up -d
# Mailpit http://localhost:8025, Prometheus http://localhost:9091, Grafana http://localhost:3001
```

## Cost

DeepSeek V4 Flash costs about $0.09 per million input and $0.18 per million output tokens on
OpenRouter. A suggestion cost about $0.0006 when tried and took 15 to 18 seconds; day plans are
longer. The weather, holiday and map services are free.

## Backup

Everything that matters is in `agent.db` on the volume. A copy while running:

```bash
sqlite3 /data/agent.db ".backup '/data/agent-$(date +%F).db'"
```
