# Urlaubs-Agent

Persönlicher Reiseplaner als eigener Agent pro Person, deployt auf InfraHeroes. **Er bucht nichts**, er schlägt vor und plant.

## Was er kann (MVP)
- **Ideen finden:** Wunsch eingeben (Zeitraum, Nächte, Budget, Reisende, Abreiseort, Vorlieben). Er schlägt 3 Ziele vor, mit Wetter, Anreise, Unterkunftsart, Highlights und einer Kostenschätzung nach Posten
- **Tagesplan:** für ein gewähltes oder bekanntes Ziel bis zu 14 Tage, pro Tag mit Vormittag, Nachmittag, Abend, Essens-Tipp, Schlechtwetter-Alternative und Hinweisen zu Wegen, dazu eine Packliste
- **Meine Reisen:** Vorschläge und Pläne merken (SQLite im eigenen Volume), Plan als Kalenderdatei (`.ics`) exportieren, drucken

Preise sind Schätzungen und als solche gekennzeichnet.
- **Tag anpassen:** einen einzelnen Tag nach einem Wunsch neu planen („entspannter“, „mehr für Kinder“), die anderen Tage bleiben
- **Teilen:** ein Link nur zum Lesen (`/s/<token>`) für Mitreisende ohne Konto, 7, 30 oder 90 Tage gültig, jederzeit zurückziehbar
- **Fakten statt Schätzung:** mit Startdatum das gemessene Wetter derselben Tage der letzten drei Jahre (Open-Meteo) sowie Feiertage und Schulferien am Ziel (OpenHolidays). Beides fließt in den Plan ein; fehlt eine Quelle, geht es ohne
- **Karte:** die Orte jedes Tages auf OpenStreetMap (Leaflet liegt unter `static/vendor`), Orte weit weg vom Ziel werden verworfen
- **Machbarkeit:** geschätzte Wege pro Tag, Warnung bei zu viel Fahrerei für das Tempo, bei bekannten Ruhetagen und an Feiertagen (`app/checks.py`, ohne Routing-Dienst)
- **Daumen hoch/runter:** pro Vorschlag; Gemochtes und Abgelehntes fließt in die nächsten Vorschläge ein
- **Profil:** Abreiseort, Reisende, Budget, Vorlieben, Meiden und Barrierefreiheit einmal angeben; füllt die Formulare vor und geht mit jeder Anfrage mit

## Technik
- FastAPI, eine einzige Seite (Vanilla JS, ohne Build-Schritt)
- Modell über **OpenRouter**, standardmäßig `deepseek/deepseek-v4-flash` (günstig, langer Kontext, JSON-Schema-Ausgabe). Die Antwort wird gegen das Schema geprüft, bei einer unbrauchbaren Antwort einmal neu angefragt
- Ohne `OPENROUTER_API_KEY` (oder mit `AGENT_FAKE=1`) läuft er im **Demo-Modus** mit Beispielantworten, ohne API-Aufrufe
- Ausgaben des Modells werden nur als Text gerendert, nie als HTML

## Zugang
Die Startseite ist öffentlich. Der Planer ist nur mit Konto erreichbar, und das Konto ist eine E-Mail-Adresse:
- Adresse eingeben, einen sechsstelligen Code per Mail bekommen, Code eingeben. Ein Passwort gibt es nicht.
- Der Code gilt 10 Minuten, nur einmal und nur für 5 Versuche. Gespeichert wird nur ein Hash.
- Die Antwort auf „Code senden“ ist für bekannte und unbekannte Adressen gleich, man kann also nicht erfragen, wer ein Konto hat.
- Codes anfordern (3 pro Adresse und 10 pro Client in 10 Minuten, 200 pro Stunde insgesamt) und Codes probieren (20 pro Client in 10 Minuten) sind begrenzt.
- Mit `ALLOWED_EMAILS` oder `ALLOWED_EMAIL_DOMAINS` lässt sich einschränken, wer sich anmelden darf. Leer heißt: jede Adresse.
- Die Sitzung ist ein signiertes Cookie (HttpOnly, SameSite=Strict, unter https Secure, 14 Tage). Gemerkte Reisen gehören ihrer Person.
- Ohne Mailserver (`SMTP_HOST`) kann sich niemand anmelden.

## Limits und Zahlen
- Jede Person hat `USER_DAILY_QUERIES` Anfragen pro Tag (Standard 10), und der Agent insgesamt `AGENT_DAILY_CALLS` (Standard 200), weil jede Anfrage Geld kostet. Die Seite zeigt, wie viele noch übrig sind.
- Gespeichert werden pro Tag: aktive Nutzer, neue Nutzer und Modellanfragen (`GET /api/stats`, nur für den Betreiber).
- `GET /metrics` liefert Prometheus-Metriken (Bearer-Token `METRICS_TOKEN`, ohne Token nur vom eigenen Rechner): Nutzer, aktive und neue Nutzer heute, Anfragen nach Ergebnis, Codes und Anmeldungen, Antwortzeit des Modells, Token und die von OpenRouter gemeldeten Kosten. Adressen und Codes kommen in keiner Metrik vor.
- Das Grafana-Dashboard liegt in `deploy/observability/grafana/dashboards/travel-agent.json`.

## Lokal ausprobieren
```bash
uv venv --python 3.14 && uv pip install -e ".[dev]"
.venv/bin/pytest -q

# Mailserver zum Abfangen der Codes (http://localhost:8025), Prometheus (9091) und Grafana (3001)
docker compose -f deploy/observability/docker-compose.yml up -d

OPENROUTER_API_KEY=sk-or-... METRICS_TOKEN=local-metrics-token SMTP_HOST=localhost SMTP_PORT=1025 \
  DATA_DIR=./data .venv/bin/uvicorn app.main:app --port 8780
```
Ohne `OPENROUTER_API_KEY` antwortet der Agent mit Beispielen. Statt eines Mailservers geht auch `MAIL_BACKEND=console`: Die Codes stehen dann im Log.

## Kosten
V4 Flash kostet bei OpenRouter etwa 0,09 $ pro Million Eingabe- und 0,18 $ pro Million Ausgabetoken. Beim Ausprobieren kostete eine Anfrage rund 0,0006 $ und dauerte 15 bis 18 Sekunden.

## Deploy
`hero.toml` und `.woodpecker/pipeline.yml` beschreiben den Deploy auf InfraHeroes (Projekt, Volume und die Secrets stehen in `hero.toml`). Jeder Push auf `main` läuft durch Lint, Test, bandit und pip-audit und deployt dann.

Das Volume gehört beim Start root. Das Entrypoint-Skript übergibt `/data` an den Benutzer `agent` und startet den Server ohne Rechte. Mit einem Volume gibt es genau ein Replikat und kein Scale-to-Zero.

## Konfiguration
| Variable | Default | Zweck |
|---|---|---|
| `OPENROUTER_API_KEY` | – | API-Key (Secret). Fehlt er oder ist er kein `sk-or-…`-Key, läuft der Demo-Modus |
| `AGENT_MODEL` | `deepseek/deepseek-v4-flash` | Modell auf OpenRouter |
| `AGENT_EFFORT` | `medium` | Denkaufwand (`low`, `medium`, `high`) |
| `USER_DAILY_QUERIES` | `10` | Anfragen pro Person und Tag |
| `AGENT_DAILY_CALLS` | `200` | Anfragen pro Tag insgesamt |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` | – / `587` | Mailserver für die Codes (Port 465 = TLS, sonst STARTTLS). `MAIL_BACKEND=console` schreibt die Codes ins Log |
| `ALLOWED_EMAILS`, `ALLOWED_EMAIL_DOMAINS` | leer | Wer sich anmelden darf, kommagetrennt. Leer = jede Adresse |
| `SESSION_SECRET` | wird erzeugt | Schlüssel für die Sitzungen (16+ Zeichen). Ohne Angabe liegt ein zufälliger Schlüssel im Datenverzeichnis |
| `METRICS_TOKEN` | – | Bearer-Token für `/metrics` und `/api/stats`. Ohne Token nur vom eigenen Rechner |
| `AGENT_MAX_TOKENS` | `8000` | Obergrenze der Antwortlänge |
| `AGENT_TIMEOUT_SECONDS` | `120` | Wartezeit auf das Modell |
| `DATA_DIR` | `./data` | Datenbank (Nutzer, Reisen, Zähler) |
| `AGENT_FAKE` | – | `1` erzwingt den Demo-Modus |
