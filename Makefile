# Development shortcuts. The CI runs the same commands (see .woodpecker/pipeline.yml).
PY := .venv/bin

.PHONY: install run lint format types test security check

install:
	uv pip install -e ".[dev]"

# Demo mode unless .env sets OPENROUTER_API_KEY; sign-in codes appear in the log.
run:
	set -a; if [ -f .env ]; then . ./.env; fi; set +a; \
	MAIL_BACKEND=$${MAIL_BACKEND:-console} DATA_DIR=$${DATA_DIR:-./data} \
	$(PY)/uvicorn app.main:app --reload --port 8780

lint:
	$(PY)/ruff check .
	$(PY)/ruff format --check .

format:
	$(PY)/ruff check --fix .
	$(PY)/ruff format .

types:
	$(PY)/mypy

test:
	$(PY)/pytest -q

security:
	$(PY)/bandit -q -r app -ll
	$(PY)/pip-audit --progress-spinner off

check: lint types test security
