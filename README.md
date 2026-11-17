# Urlaubs-Agent

Persönlicher Reiseplaner als eigener Agent pro Person, deployt auf InfraHeroes. **Er bucht nichts**, er schlägt vor und plant.

## Was er kann (MVP)
- **Ideen finden:** Wunsch eingeben (Zeitraum, Nächte, Budget, Reisende, Abreiseort, Vorlieben). Er schlägt 3 Ziele vor, mit Wetter, Anreise, Unterkunftsart, Highlights und einer Kostenschätzung nach Posten
- **Tagesplan:** für ein gewähltes oder bekanntes Ziel bis zu 14 Tage, pro Tag mit Vormittag, Nachmittag, Abend, Essens-Tipp, Schlechtwetter-Alternative und Hinweisen zu Wegen, dazu eine Packliste
- **Meine Reisen:** Vorschläge und Pläne merken (SQLite im eigenen Volume), Plan als Kalenderdatei (`.ics`) exportieren, drucken

Preise sind Schätzungen und als solche gekennzeichnet.

## Technik
- FastAPI, eine einzige Seite (Vanilla JS, ohne Build-Schritt)
- Modell über **OpenRouter**, standardmäßig `deepseek/deepseek-v4-flash` (günstig, langer Kontext, JSON-Schema-Ausgabe). Die Antwort wird gegen das Schema geprüft, bei einer unbrauchbaren Antwort einmal neu angefragt
- Ohne `OPENROUTER_API_KEY` (oder mit `AGENT_FAKE=1`) läuft er im **Demo-Modus** mit Beispielantworten, ohne API-Aufrufe
- Ausgaben des Modells werden nur als Text gerendert, nie als HTML

## Zugang
Eine App auf InfraHeroes hat keinen Login davor, der Agent bringt deshalb sein eigenes Passwort mit (`app/auth.py`):
- `AGENT_PASSWORD` (Secret, mindestens 8 Zeichen) ist das Passwort. **Fehlt es, liefert der Agent nichts außer `/healthz` aus.**
- Das richtige Passwort setzt ein signiertes Cookie (HttpOnly, SameSite=Strict, unter https Secure, 14 Tage). Ein neues Passwort meldet alle ab.
- Falsche Passwörter werden begrenzt: 5 pro Adresse und 20 insgesamt in 10 Minuten.

## Kosten
Jede Modellanfrage zählt gegen `AGENT_DAILY_CALLS` (Standard 30 pro Tag, gespeichert im Volume). Ist das Limit erreicht, fragt der Agent das Modell nicht mehr. Der Preis von V4 Flash liegt bei etwa 0,09 $ pro Million Eingabe- und 0,18 $ pro Million Ausgabetoken.

## Lokal
```bash
uv venv --python 3.14 && uv pip install -e ".[dev]"
.venv/bin/pytest -q
AGENT_PASSWORD=***REMOVED*** DATA_DIR=./data .venv/bin/uvicorn app.main:app --port 8780
```

## Deploy (eine Instanz pro Person)
Einmalig pro Instanz:
```bash
heroctl projects create urlaubs-agent
heroctl volumes create urlaubs-data --size 1 --project urlaubs-agent
heroctl secrets set OPENROUTER_API_KEY --project urlaubs-agent
heroctl secrets set AGENT_PASSWORD --project urlaubs-agent
```
Danach deployt jeder Push auf `main` über die Woodpecker-Pipeline (`.woodpecker/pipeline.yml`: Lint, Test, bandit/pip-audit, dann `heroctl deploy`). Von Hand: `heroctl deploy --project urlaubs-agent`.

Das Volume gehört beim Start root. Das Entrypoint-Skript übergibt `/data` an den Benutzer `agent` und startet den Server ohne Rechte. Mit einem Volume gibt es genau ein Replikat und kein Scale-to-Zero, ein Redeploy dauert kurz.

## Konfiguration
| Variable | Default | Zweck |
|---|---|---|
| `OPENROUTER_API_KEY` | – | API-Key (Secret). Fehlt er, läuft der Demo-Modus |
| `AGENT_PASSWORD` | – | Passwort (Secret). Fehlt es, wird nichts ausgeliefert |
| `AGENT_MODEL` | `deepseek/deepseek-v4-flash` | Modell auf OpenRouter |
| `AGENT_EFFORT` | `medium` | Denkaufwand (`low`, `medium`, `high`) |
| `AGENT_DAILY_CALLS` | `30` | Modellanfragen pro Tag |
| `AGENT_MAX_TOKENS` | `8000` | Obergrenze der Antwortlänge |
| `AGENT_TIMEOUT_SECONDS` | `120` | Wartezeit auf das Modell |
| `DATA_DIR` | `./data` | Speicherort der gemerkten Reisen |
| `AGENT_FAKE` | – | `1` erzwingt den Demo-Modus |
