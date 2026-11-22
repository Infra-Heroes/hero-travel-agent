# Architecture

One FastAPI application, one process, one SQLite file. No build step, no queue, no second service.

```
Browser ──► FastAPI (app/main.py)
              ├─ auth.py      one-time codes, signed session cookies
              ├─ agent.py     model calls through OpenRouter, JSON-schema output
              ├─ facts.py     geocoding, measured weather, holidays (before planning)
              ├─ checks.py    feasibility of a plan (after planning)
              ├─ store.py     SQLite: users, trips, limits, profile, ratings, share links
              ├─ mailer.py    SMTP or console
              ├─ report.py    daily numbers report to the operator
              └─ metrics.py   Prometheus
```

## Layout

| Path | Contents |
|---|---|
| `app/` | the application |
| `app/schemas.py` | inputs and outputs; the answer classes are also the JSON schema the model fills |
| `app/texts.py` | the few sentences the server says itself, German and English |
| `app/static/` | landing page, planner, shared-trip page, legal notice, privacy policy |
| `app/static/render.js` | rendering of suggestions and plans, shared by the planner and the shared page |
| `app/static/vendor/` | Leaflet 1.9.4, local so the CSP needs no third-party scripts |
| `tests/` | pytest, without network and without a model |
| `deploy/observability/` | local Prometheus, Grafana and Mailpit to try things out |
| `hero.toml` | deployment description for InfraHeroes |

## A day plan, step by step

1. `POST /api/plan` checks the session and takes one request from the daily limits
   (`store.try_spend`, atomic, so two requests cannot both take the last one).
2. `facts.for_plan` locates the destination (Open-Meteo geocoding; a country after the comma must
   match) and, with a start date, fetches weather and holidays. Answers are cached for a day.
3. `agent.plan_days` sends the wish, the facts and the profile to the model. The answer must match
   the `DayPlan` schema and have exactly the requested number of days, or it is asked once more.
4. `checks.check_plan` drops places far from the destination, estimates travel and writes notes.
5. The page gets a `PlanResult` (plan, facts, routes, checks) and sets everything as text, never
   as HTML.

Without an API key, or with `AGENT_FAKE=1`, `fake_suggestions` and `fake_day_plan` answer with
fixed samples, and nothing is looked up.

## API

All answers are JSON; errors look like `{"detail": "…"}` in the page's language.

| Method and path | Purpose |
|---|---|
| `POST /api/auth/request`, `POST /api/auth/verify`, `POST /api/auth/logout` | ask for a code, sign in, sign out |
| `GET /api/me`, `DELETE /api/me` | account and requests left, delete the account |
| `POST /api/suggest` | three suggestions |
| `POST /api/plan`, `POST /api/plan/refine` | day plan, replan one day |
| `GET/PUT /api/profile` | profile |
| `GET/POST /api/votes` | ratings |
| `GET/POST /api/trips`, `GET/DELETE /api/trips/{id}` | saved trips |
| `GET /api/trips/{id}/calendar.ics` | plan as a calendar file |
| `POST/DELETE /api/trips/{id}/share`, `GET /api/shared/{token}` | create, withdraw, read a share link |
| `GET /healthz` | liveness, also says whether demo mode is on |
| `GET /metrics`, `GET /api/stats`, `POST /api/report/send` | operator only |

## Database

One SQLite file `agent.db` in the data directory. Tables are created on start with
`CREATE TABLE IF NOT EXISTS`; new features add new tables and leave existing ones as they are.

| Table | Contents |
|---|---|
| `users` | e-mail address, created on the first valid code |
| `login_codes` | hash of the code, expiry, failed attempts |
| `trips` | saved suggestions and plans (JSON) |
| `shares` | share token, trip, expiry |
| `profiles` | profile (JSON) |
| `votes` | rating per destination |
| `user_usage`, `usage` | requests per person and day, in total per day |
| `activity` | who was active on which day, for the numbers |
| `meta` | small things such as the day of the last report |

Everything that belongs to a person hangs off `users` by a foreign key and goes when the account is
deleted.
