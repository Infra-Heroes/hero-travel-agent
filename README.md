# Urlaubs-Agent

**Ein persönlicher Reiseplaner, der Vorschläge macht und die Tage plant, aber nichts bucht.**

Du sagst, wann du verreisen willst, mit wem und wie viel es kosten darf. Der Agent schlägt
drei passende Ziele vor und plant für das Ziel deiner Wahl jeden Tag: Vormittag, Nachmittag,
Abend, Essen, Plan B bei Regen, dazu eine Packliste. Wetter und Feiertage stammen aus echten
Daten statt aus Schätzungen, die Orte stehen auf einer Karte, und ein einfacher Prüfschritt
warnt vor Tagen mit zu viel Fahrerei.

Live: <https://www.urlaubs-planung.org> · Läuft auf [InfraHeroes](https://infra-heroes.de)

## Was er kann

| | |
|---|---|
| **Ideen finden** | drei Ziele mit Wetter, Anreise, Unterkunft, Highlights, Kostenschätzung und einer ehrlichen Einschränkung |
| **Tagesplan** | bis zu 14 Tage, jeder Tag mit Karte, geschätzten Wegen und Hinweisen zur Machbarkeit |
| **Echte Fakten** | gemessenes Wetter derselben Tage der letzten drei Jahre, Feiertage und Schulferien am Ziel |
| **Nachbessern** | einen einzelnen Tag nach Wunsch neu planen, der Rest bleibt |
| **Teilen** | Link nur zum Lesen für Mitreisende ohne Konto, mit Ablaufdatum |
| **Lernt dazu** | Daumen hoch oder runter pro Vorschlag, dazu ein Profil mit Vorlieben, Dingen, die man meiden will, und Barrierefreiheit |
| **Mitnehmen** | Kalenderdatei (.ics), Google-Kalender, PDF |

Mehr dazu: [docs/features.md](docs/features.md).

## Schnellstart

Ohne API-Key läuft der Agent im **Demo-Modus** mit Beispielantworten, ohne Netz und ohne Kosten.

```bash
uv venv --python 3.14 && uv pip install -e ".[dev]"
make test          # Lint, Typen, Tests mit Abdeckung
make run           # http://localhost:8780, Demo-Modus, Codes im Log
```

Mit einem echten Modell: `OPENROUTER_API_KEY` setzen, siehe [.env.example](.env.example) und
[docs/configuration.md](docs/configuration.md).

## Wie er gebaut ist

FastAPI mit einer Seite in Vanilla-JavaScript, ohne Build-Schritt. Das Modell (standardmäßig
DeepSeek V4 Flash über OpenRouter) antwortet in JSON nach einem festen Schema, die Seite rendert
nur Daten, nie HTML vom Modell. Konten sind E-Mail-Adressen mit Einmalcode, gespeichert wird in
einer SQLite-Datei.

| Dokument | Inhalt |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Aufbau, Module, Datenfluss, Datenbank |
| [docs/configuration.md](docs/configuration.md) | alle Umgebungsvariablen |
| [docs/operations.md](docs/operations.md) | Deploy, Limits, Metriken, Kosten |
| [docs/privacy.md](docs/privacy.md) | welche Daten wohin gehen |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Entwickeln, Testen, Beiträge |
| [SECURITY.md](SECURITY.md) | Sicherheitsmodell, Lücken melden |

## Grenzen

- Er bucht nichts und verspricht keine Verfügbarkeit. Preise sind Schätzungen und so gekennzeichnet.
- Die Koordinaten der Orte gibt das Modell an. Orte weit weg vom Ziel werden verworfen, der Rest
  ist eine ungefähre Lage.
- Die Wege sind Luftlinie mal Umwegfaktor, kein Routing.
