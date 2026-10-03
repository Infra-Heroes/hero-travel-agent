# Urlaubs-Agent

Persönlicher Reiseplaner als eigener Agent pro Person, deployt auf InfraHeroes. **Er bucht nichts**, er schlägt vor und plant.

## Was er kann (MVP)
- **Ideen finden:** Wunsch eingeben (Zeitraum, Nächte, Budget, Reisende, Abreiseort, Vorlieben). Er schlägt 3 Ziele vor, mit Wetter, Anreise, Unterkunftsart, Highlights und einer Kostenschätzung nach Posten
- **Tagesplan:** für ein gewähltes oder bekanntes Ziel bis zu 14 Tage, pro Tag mit Vormittag, Nachmittag, Abend, Essens-Tipp, Schlechtwetter-Alternative und Hinweisen zu Wegen, dazu eine Packliste
- **Meine Reisen:** Vorschläge und Pläne merken (SQLite im eigenen Volume), Plan als Kalenderdatei (`.ics`) exportieren, drucken

Preise sind Schätzungen und als solche gekennzeichnet.

## Technik
- FastAPI, eine einzige Seite (Vanilla JS, ohne Build-Schritt)
- Claude (`claude-opus-5-5`) mit strukturierter Ausgabe (`output_config.format` als JSON-Schema aus den Pydantic-Modellen) und serverseitigem Fallback bei Ablehnung (`fallbacks: "default"`)
- Ohne `ANTHROPIC_API_KEY` (oder mit `AGENT_FAKE=1`) läuft er im **Demo-Modus** mit Beispielantworten, ohne API-Aufrufe
- Ausgaben des Modells werden nur als Text gerendert, nie als HTML

## Lokal
```bash
uv venv --python 3.14 && uv pip install -e ".[dev]"
.venv/bin/pytest -q
DATA_DIR=./data .venv/bin/uvicorn app.main:app --port 8780
```

## Deploy (eine Instanz pro Person)
```bash
heroctl secrets set ANTHROPIC_API_KEY --project urlaubs-agent
heroctl deploy --project urlaubs-agent
```
`hero.toml` setzt `public = false`, der Agent liegt also hinter dem Plattform-Login. Für dauerhaft gespeicherte Reisen braucht `/data` ein Volume.

## Konfiguration
| Variable | Default | Zweck |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | API-Key (Secret). Fehlt er, läuft der Demo-Modus |
| `AGENT_MODEL` | `claude-opus-5-5` | Modell |
| `AGENT_EFFORT` | `medium` | Denkaufwand (`low` bis `max`) |
| `DATA_DIR` | `./data` | Speicherort der gemerkten Reisen |
| `AGENT_FAKE` | – | `1` erzwingt den Demo-Modus |
