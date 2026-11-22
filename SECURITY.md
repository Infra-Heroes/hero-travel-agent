# Sicherheit

## Eine Lücke melden

Bitte nicht als öffentliches Issue, sondern per Mail an **info@infra-heroes.de** mit dem Betreff
„Security Urlaubs-Agent“. Wir melden uns so schnell wie möglich.

## Wie der Agent geschützt ist

### Anmeldung

- Konten sind E-Mail-Adressen, angemeldet wird mit einem sechsstelligen Code, ohne Passwort.
- Ein Code gilt 10 Minuten, einmal und für höchstens 5 Versuche. Gespeichert wird nur ein
  HMAC-SHA256 des Codes mit dem Serverschlüssel.
- „Code senden“ antwortet für bekannte und unbekannte Adressen gleich; man kann nicht erfragen,
  wer ein Konto hat.
- Begrenzt sind: Codes anfordern (3 pro Adresse und 10 pro Client in 10 Minuten, 200 pro Stunde
  insgesamt) und Codes probieren (20 pro Client in 10 Minuten).
- Die Sitzung ist ein signiertes Cookie: HttpOnly, SameSite=Strict, über HTTPS Secure, 14 Tage.
- `ALLOWED_EMAILS` und `ALLOWED_EMAIL_DOMAINS` schränken ein, wer sich anmelden darf.

### Daten

- Jede gespeicherte Reise, jedes Profil, jede Bewertung gehört genau einer Person; alle Abfragen
  filtern nach ihr.
- Freigabe-Links sind zufällige Token (144 Bit), laufen ab, lassen sich zurückziehen und zeigen
  nichts über die Person. Die Seite schickt nur die Domain als Referrer mit und wird nicht
  indexiert.
- Gespeicherte Pläne werden gegen das Schema geprüft, bevor sie in die Datenbank gehen.

### Seite

- Content-Security-Policy: Skripte, Stile und Verbindungen nur vom eigenen Host, Bilder zusätzlich
  von `tile.openstreetmap.org`; keine Inline-Skripte, kein Einbetten in fremde Seiten.
- Alles, was aus einer Modellantwort stammt, wird als Text gesetzt, nie als HTML.
- Dazu `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`,
  `Cross-Origin-Opener-Policy` und über HTTPS `Strict-Transport-Security`.
- Anfragen über 256 KB werden abgewiesen, bevor sie gelesen werden.

### Kosten

Tageslimits pro Person und insgesamt begrenzen, was ein Konto oder ein Angriff an Modellkosten
verursachen kann.

### Betrieb

- Der Server läuft im Container als Benutzer ohne Rechte.
- Secrets kommen aus der Plattform, nie aus dem Repository.
- Die CI prüft jeden Pull Request mit `bandit` (Codemuster) und `pip-audit` (bekannte Lücken in
  Abhängigkeiten); Renovate hält die Abhängigkeiten aktuell.
