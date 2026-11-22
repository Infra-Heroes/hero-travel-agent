# Konfiguration

Alles über Umgebungsvariablen. Eine Vorlage zum Kopieren liegt in [`.env.example`](../.env.example).
Secrets (gekennzeichnet) gehören nie in eine Datei im Repository; im Deploy kommen sie aus den
Secrets des Projekts (`secret:NAME` in `hero.toml`).

## Modell

| Variable | Standard | Zweck |
|---|---|---|
| `OPENROUTER_API_KEY` | – | **Secret.** Fehlt er oder beginnt er nicht mit `sk-or-`, läuft der Demo-Modus |
| `AGENT_MODEL` | `deepseek/deepseek-v4-flash` | Modell auf OpenRouter; es muss JSON-Schema-Ausgabe können |
| `AGENT_EFFORT` | `medium` | Denkaufwand für Tagespläne: `off`, `low`, `medium`, `high` |
| `AGENT_EFFORT_SUGGEST` | `off` | Denkaufwand für Vorschläge |
| `AGENT_MAX_TOKENS` | `8000` | Obergrenze der Antwortlänge |
| `AGENT_TIMEOUT_SECONDS` | `120` | Wartezeit auf das Modell |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | anderer, kompatibler Endpunkt |
| `AGENT_FAKE` | – | `1` erzwingt den Demo-Modus |

## Fakten

| Variable | Standard | Zweck |
|---|---|---|
| `FACTS` | `1`, im Demo-Modus `0` | Wetter, Feiertage und Geocoding nachschlagen |
| `FACTS_TIMEOUT_SECONDS` | `6` | Wartezeit pro Abfrage |

## Konten und Mail

| Variable | Standard | Zweck |
|---|---|---|
| `SMTP_HOST`, `SMTP_PORT` | –, `587` | Mailserver für die Codes; Port 465 heißt TLS, sonst STARTTLS |
| `SMTP_USER`, `SMTP_PASSWORD` | – | **Secrets.** Anmeldung am Mailserver |
| `MAIL_FROM` | `Urlaubs-Agent <noreply@localhost>` | Absender |
| `MAIL_BACKEND` | – | `console`: Mails gehen ins Log statt an einen Server (nur zum Entwickeln) |
| `ALLOWED_EMAILS`, `ALLOWED_EMAIL_DOMAINS` | leer | wer sich anmelden darf, kommagetrennt; leer heißt jede Adresse |
| `SESSION_SECRET` | wird erzeugt | **Secret**, 16+ Zeichen. Ohne Angabe liegt ein zufälliger Schlüssel im Datenverzeichnis |

Ohne `SMTP_HOST` und ohne `MAIL_BACKEND=console` kann sich niemand anmelden.

## Limits

| Variable | Standard | Zweck |
|---|---|---|
| `USER_DAILY_QUERIES` | `10` | Anfragen pro Person und Tag (Vorschlag, Plan, Tag anpassen zählen je eine) |
| `AGENT_DAILY_CALLS` | `200` | Anfragen pro Tag insgesamt |

## Betrieb

| Variable | Standard | Zweck |
|---|---|---|
| `DATA_DIR` | `./data` | Datenbank und erzeugter Sitzungsschlüssel |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warning`, `error` |
| `METRICS_TOKEN` | – | **Secret.** Bearer-Token für `/metrics` und `/api/stats`; ohne nur vom eigenen Rechner |
| `REPORT_TO` | – | **Secret.** Empfänger des täglichen Zahlenberichts; leer heißt kein Bericht |
| `REPORT_HOUR_UTC` | `6` | Stunde des Berichts |
