# Aufbau

Eine FastAPI-Anwendung, ein Prozess, eine SQLite-Datei. Kein Build-Schritt, keine Warteschlange,
kein zweiter Dienst.

```
Browser ──► FastAPI (app/main.py)
              ├─ auth.py      Einmalcodes, signierte Sitzungscookies
              ├─ agent.py     Modellaufrufe über OpenRouter, JSON-Schema-Ausgabe
              ├─ facts.py     Geocoding, gemessenes Wetter, Feiertage (vor dem Planen)
              ├─ checks.py    Machbarkeit eines Plans (nach dem Planen)
              ├─ store.py     SQLite: Nutzer, Reisen, Limits, Profil, Bewertungen, Freigaben
              ├─ mailer.py    SMTP oder Konsole
              ├─ report.py    täglicher Zahlenbericht an den Betreiber
              └─ metrics.py   Prometheus
```

## Verzeichnisse

| Pfad | Inhalt |
|---|---|
| `app/` | die Anwendung |
| `app/schemas.py` | Ein- und Ausgaben; die Antwortklassen sind zugleich das JSON-Schema für das Modell |
| `app/texts.py` | die wenigen Sätze, die der Server selbst sagt, deutsch und englisch |
| `app/static/` | Startseite, Planer, Freigabe-Seite, Impressum, Datenschutz |
| `app/static/render.js` | Darstellung von Vorschlägen und Plänen, gemeinsam für Planer und Freigabe |
| `app/static/vendor/` | Leaflet 1.9.4, lokal, damit die CSP keine fremden Skripte erlauben muss |
| `tests/` | pytest, ohne Netz und ohne Modell |
| `deploy/observability/` | lokales Prometheus, Grafana und Mailpit zum Ausprobieren |
| `hero.toml` | Deploy-Beschreibung für InfraHeroes |

## Eine Planung, Schritt für Schritt

1. `POST /api/plan` prüft die Sitzung und zieht eine Anfrage vom Tageslimit ab (`store.try_spend`,
   atomar, damit zwei Anfragen nicht beide die letzte nehmen).
2. `facts.for_plan` sucht das Ziel (Open-Meteo Geocoding, mit Ländervorgabe nach dem Komma) und
   holt mit Startdatum Wetter und Feiertage. Ergebnisse bleiben einen Tag im Speicher.
3. `agent.plan_days` schickt Wunsch, Fakten und Profil an das Modell. Die Antwort muss dem Schema
   `DayPlan` genügen und genau so viele Tage haben wie gewünscht, sonst wird einmal neu gefragt.
4. `checks.check_plan` verwirft Orte weit weg vom Ziel, schätzt die Wege und schreibt Hinweise.
5. Die Seite bekommt `PlanResult` (Plan, Fakten, Wege, Hinweise) und setzt alles als Text, nie als
   HTML.

Ohne API-Key oder mit `AGENT_FAKE=1` antworten `fake_suggestions` und `fake_day_plan` mit festen
Beispielen. Dann wird auch nichts nachgeschlagen.

## Schnittstelle

Alle Antworten sind JSON; Fehler haben die Form `{"detail": "…"}` in der Sprache der Seite.

| Methode und Pfad | Zweck |
|---|---|
| `POST /api/auth/request`, `POST /api/auth/verify`, `POST /api/auth/logout` | Code anfordern, anmelden, abmelden |
| `GET /api/me`, `DELETE /api/me` | Konto und verbleibende Anfragen, Konto löschen |
| `POST /api/suggest` | drei Vorschläge |
| `POST /api/plan`, `POST /api/plan/refine` | Tagesplan, einen Tag neu planen |
| `GET/PUT /api/profile` | Profil |
| `GET/POST /api/votes` | Bewertungen |
| `GET/POST /api/trips`, `GET/DELETE /api/trips/{id}` | gemerkte Reisen |
| `GET /api/trips/{id}/calendar.ics` | Plan als Kalenderdatei |
| `POST/DELETE /api/trips/{id}/share`, `GET /api/shared/{token}` | Freigabe-Link anlegen, zurückziehen, lesen |
| `GET /healthz` | Lebenszeichen, sagt auch, ob der Demo-Modus läuft |
| `GET /metrics`, `GET /api/stats`, `POST /api/report/send` | nur für den Betreiber |

## Datenbank

Eine SQLite-Datei `agent.db` im Datenverzeichnis. Tabellen werden beim Start mit
`CREATE TABLE IF NOT EXISTS` angelegt; neue Funktionen bringen neue Tabellen mit, bestehende
werden nicht verändert.

| Tabelle | Inhalt |
|---|---|
| `users` | E-Mail-Adresse, angelegt beim ersten gültigen Code |
| `login_codes` | Hash des Codes, Ablauf, Fehlversuche |
| `trips` | gemerkte Vorschläge und Pläne (JSON) |
| `shares` | Freigabe-Token, Reise, Ablauf |
| `profiles` | Profil (JSON) |
| `votes` | Bewertung pro Ziel |
| `user_usage`, `usage` | Anfragen pro Person und Tag, insgesamt pro Tag |
| `activity` | wer an welchem Tag aktiv war, für die Zahlen |
| `meta` | Kleinigkeiten wie der Tag des letzten Berichts |

Alles, was zu einer Person gehört, hängt per Fremdschlüssel an `users` und verschwindet beim
Löschen des Kontos.
