# Urlaubs-Agent

**A personal trip planner that suggests destinations and plans the days, and books nothing.**

> **This is an example app.** It shows what a small, complete product looks like when it runs
> on [InfraHeroes](https://infra-heroes.de): an AI agent with accounts, limits, a database on a
> volume, a custom domain, metrics and a CI/CD pipeline. Use it as a template for your own app.
> Live at <https://www.urlaubs-planung.org> (German and English).

You say when you want to travel, with whom and how much it may cost. The agent suggests three
destinations that fit and, for the one you pick, plans every day: morning, afternoon, evening,
where to eat, a plan B for rain and a packing list. Weather and holidays come from measured data
instead of guesses, the places are shown on a map, and a simple check warns about days with too
much travel.

## Features

| | |
|---|---|
| **Trip ideas** | three destinations with weather, getting there, accommodation, highlights, a cost estimate and an honest caveat |
| **Day plans** | up to 14 days, each with a map, estimated travel and feasibility notes |
| **Real facts** | measured weather of the same days in the last three years, public and school holidays at the destination |
| **Refine** | replan a single day to a wish, the rest stays |
| **Share** | a read-only link for fellow travellers without an account, with an expiry |
| **Learns** | thumbs up or down per suggestion, and a profile with preferences, things to avoid and accessibility needs |
| **Export** | calendar file (.ics), Google Calendar, PDF |

More in [docs/features.md](docs/features.md).

## Quick start

Without an API key the agent runs in **demo mode** with sample answers: no network, no cost.

```bash
uv venv --python 3.14 && uv pip install -e ".[dev]"
make check    # lint, types, tests with coverage, security checks
make run      # http://localhost:8780, demo mode, sign-in codes in the log
```

For real answers set `OPENROUTER_API_KEY`, see [.env.example](.env.example) and
[docs/configuration.md](docs/configuration.md).

## How it is built

FastAPI and a single page in plain JavaScript, no build step. The model (DeepSeek V4 Flash on
OpenRouter by default) answers in JSON that must match a fixed schema; the page renders data,
never HTML from the model. Accounts are e-mail addresses with a one-time code; everything is
stored in one SQLite file.

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | structure, modules, request flow, API, database |
| [docs/configuration.md](docs/configuration.md) | all environment variables |
| [docs/operations.md](docs/operations.md) | deploying on InfraHeroes, limits, metrics, cost, backup |
| [docs/privacy.md](docs/privacy.md) | what data goes where |
| [CONTRIBUTING.md](CONTRIBUTING.md) | development, tests, rules |
| [SECURITY.md](SECURITY.md) | security model, reporting a vulnerability |

## Limits

- It books nothing and promises no availability. Prices are estimates and say so.
- Place coordinates come from the model. Places far from the destination are dropped; the rest
  are approximate.
- Travel times are straight-line distance times a detour factor, not routing.
- The user interface and the prompts are German first; English is a translation.

## License

[MIT](LICENSE)
