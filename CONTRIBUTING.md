# Contributing

## Setup

Python 3.12 or newer (CI uses 3.14) and [uv](https://docs.astral.sh/uv/).

```bash
uv venv --python 3.14
uv pip install -e ".[dev]"
make run      # demo mode on http://localhost:8780, sign-in codes in the log
```

Without `OPENROUTER_API_KEY` the agent answers with fixed samples. For real answers copy
`.env.example` to `.env`, fill it in and run `make run` again.

## Checks

```bash
make check    # everything CI checks
```

| Command | Checks |
|---|---|
| `make lint` | `ruff check` and `ruff format --check` (rules in `pyproject.toml`) |
| `make types` | `mypy` |
| `make test` | `pytest` with coverage; below 95 % it fails |
| `make security` | `bandit` and `pip-audit` |

The tests need neither network nor model: the agent runs in demo mode, external services are
simulated with `httpx.MockTransport`, and every test gets its own database (`tests/conftest.py`).

## Rules

- **Nothing from the model as HTML.** Everything that comes from a model answer is set with
  `textContent`; `app/static/render.js` is the place for it.
- **No third-party scripts.** The Content Security Policy allows scripts from the own host only;
  libraries go to `app/static/vendor/` (version in the file header).
- **Only extend the database.** New features get new tables with `CREATE TABLE IF NOT EXISTS`;
  existing columns are not changed, because the database lives on in production. What belongs to a
  person hangs off `users` with `ON DELETE CASCADE`.
- **External services may fail.** A missing answer means: carry on without it, not an error.
- **Two languages.** Page texts are written in German; the English translation is in
  `app/static/i18n.js`, the server's sentences are in `app/texts.py`. Code, comments, commits and
  docs are in English.
- **New data flows** go into [docs/privacy.md](docs/privacy.md) and the `/datenschutz` page.

## Pull requests

One topic per pull request, with tests. The title says what changes for users or operations; it
ends up in the [CHANGELOG](CHANGELOG.md). Checks must be green before merging.
