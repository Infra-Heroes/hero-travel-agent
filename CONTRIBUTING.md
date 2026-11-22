# Mitmachen

## Einrichten

Python 3.12 oder neuer (die CI nutzt 3.14), dazu [uv](https://docs.astral.sh/uv/).

```bash
uv venv --python 3.14
uv pip install -e ".[dev]"
make run      # Demo-Modus auf http://localhost:8780, Anmeldecodes stehen im Log
```

Ohne `OPENROUTER_API_KEY` antwortet der Agent mit festen Beispielen. Für echte Antworten
`.env.example` nach `.env` kopieren, ausfüllen und `make run` neu starten.

## Prüfen

```bash
make check    # alles, was die CI auch prüft
```

| Befehl | Prüft |
|---|---|
| `make lint` | `ruff check` und `ruff format --check` (Regeln in `pyproject.toml`) |
| `make types` | `mypy` |
| `make test` | `pytest` mit Abdeckung, unter 90 % schlägt es fehl |
| `make security` | `bandit` und `pip-audit` |

Die Tests brauchen weder Netz noch Modell: Der Agent läuft im Demo-Modus, externe Dienste werden
mit `httpx.MockTransport` nachgebildet, jede Testfunktion bekommt eine eigene Datenbank
(`tests/conftest.py`).

## Regeln

- **Nichts vom Modell als HTML.** Alles, was aus einer Modellantwort stammt, wird mit
  `textContent` gesetzt. `app/static/render.js` ist die Stelle dafür.
- **Keine fremden Skripte.** Die Content-Security-Policy erlaubt nur Skripte vom eigenen Host;
  Bibliotheken kommen nach `app/static/vendor/` (Version im Dateikopf).
- **Datenbank nur erweitern.** Neue Funktionen bekommen neue Tabellen mit
  `CREATE TABLE IF NOT EXISTS`; bestehende Spalten werden nicht geändert, weil die Datenbank im
  Betrieb weiterlebt. Was einer Person gehört, hängt per `ON DELETE CASCADE` an `users`.
- **Externe Dienste dürfen ausfallen.** Eine fehlende Antwort heißt: ohne diese Angabe weiter,
  nicht Fehler.
- **Texte zweisprachig.** Sätze der Seite sind deutsch; die englische Übersetzung steht in
  `app/static/i18n.js`, Sätze des Servers in `app/texts.py`.
- **Neue Datenflüsse** in [docs/privacy.md](docs/privacy.md) und auf der Seite `/datenschutz`
  nachtragen.

## Pull Requests

Ein Thema pro Pull Request, mit Tests. Der Titel sagt, was sich für Nutzer oder Betrieb ändert;
er landet so im [CHANGELOG](CHANGELOG.md). Die Prüfungen müssen grün sein, bevor gemergt wird.
