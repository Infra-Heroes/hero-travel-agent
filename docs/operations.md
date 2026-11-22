# Betrieb

## Deploy

Der Agent läuft auf [InfraHeroes](https://infra-heroes.de) als MicroVM. `hero.toml` beschreibt alles,
was der Deploy braucht: Größe, Port, Health-Check, das Volume, die Umgebung und welche Werte aus
den Secrets des Projekts kommen.

| Schritt | Wo |
|---|---|
| Pull Request prüfen (Lint, Typen, Tests, bandit, pip-audit) | Woodpecker, `.woodpecker/pipeline.yml` |
| Deploy bei jedem Push auf `main` | GitHub Actions, `.github/workflows/deploy.yml`, mit [infra-heroes/deploy-action](https://github.com/Infra-Heroes/deploy-action) |

Der Workflow braucht ein Secret `HERO_TOKEN`: ein Deploy-Token, das nur dieses Projekt erreicht.

```bash
heroctl tokens create --name github-actions --scope deploy --project urlaubs-agent
```

### Einmalig im Projekt anlegen

```bash
heroctl volumes create urlaubs-data --size 1 --project urlaubs-agent
heroctl secrets set OPENROUTER_API_KEY --project urlaubs-agent
# ebenso SMTP_HOST, SMTP_USER, SMTP_PASSWORD, METRICS_TOKEN, SESSION_SECRET, REPORT_TO
```

`SESSION_SECRET` bei einem Umzug unbedingt übernehmen, sonst sind alle abgemeldet.

### Volume und Rechte

Das Volume gehört beim Start root. `docker-entrypoint.sh` übergibt `/data` an den Benutzer `agent`
und startet den Server ohne Rechte. Mit einem Volume gibt es genau ein Replikat und kein
Scale-to-Zero.

### Eigene Domain

`custom_domains` in `hero.toml`, mit `verify_domains = true`. DNS: ein CNAME der Subdomain auf
`ingress.infra-heroes.de.` und der TXT-Eintrag, den `heroctl domains challenge` zeigt.

## Limits

Jede Person hat `USER_DAILY_QUERIES` Anfragen am Tag, der Agent insgesamt `AGENT_DAILY_CALLS`.
Die Seite zeigt, wie viele noch übrig sind. Ist das Gesamtlimit erreicht, sagt der Agent das,
statt Kosten zu erzeugen.

## Zahlen und Überwachung

- `GET /healthz`: Lebenszeichen für den Health-Check.
- `GET /metrics` (Bearer `METRICS_TOKEN`): Nutzer, aktive und neue Nutzer heute, Anfragen nach
  Art und Ergebnis, Bewertungen, Codes und Anmeldungen, Antwortzeit des Modells, Token und die von
  OpenRouter gemeldeten Kosten. Adressen und Codes kommen in keiner Metrik vor.
- `GET /api/stats` (ebenso geschützt): Zahlen pro Tag.
- Täglicher Bericht an `REPORT_TO`, nur Zahlen.
- Grafana-Dashboard: `deploy/observability/grafana/dashboards/travel-agent.json`.

Lokal alles zusammen:

```bash
docker compose -f deploy/observability/docker-compose.yml up -d
# Mailpit http://localhost:8025, Prometheus http://localhost:9091, Grafana http://localhost:3001
```

## Kosten

DeepSeek V4 Flash kostet bei OpenRouter etwa 0,09 $ pro Million Eingabe- und 0,18 $ pro Million
Ausgabetoken. Ein Vorschlag kostete beim Ausprobieren rund 0,0006 $ und dauerte 15 bis 18
Sekunden; Tagespläne sind länger. Die Wetter-, Feiertags- und Kartendienste kosten nichts.

## Sicherung

Alles Wichtige liegt in `agent.db` auf dem Volume. Eine Kopie im laufenden Betrieb:

```bash
sqlite3 /data/agent.db ".backup '/data/agent-$(date +%F).db'"
```
