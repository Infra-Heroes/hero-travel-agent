# Daten und Datenschutz

Die rechtlich verbindliche Fassung steht auf der Seite `/datenschutz`. Hier steht technisch, was
wohin geht.

## Was gespeichert wird

| Daten | Wozu | Wie lange |
|---|---|---|
| E-Mail-Adresse | Konto, Anmeldecode | bis zum Löschen des Kontos |
| Hash des Anmeldecodes | Prüfen des Codes | 10 Minuten, oder bis er benutzt ist |
| gemerkte Reisen, Profil, Bewertungen, Freigaben | was die Person selbst speichert | bis sie es löscht oder das Konto löscht |
| Anfragen pro Person und Tag | Tageslimit | bis zum Löschen des Kontos |
| aktive Personen pro Tag | Zahlen für den Betreiber | Tage ohne Person bleiben als Zählung |

„Konto löschen“ entfernt alles, was zu der Person gehört, sofort und endgültig. Übrig bleibt nur
die Zahl der Anfragen pro Tag insgesamt, ohne Bezug zu einer Person.

Es gibt ein einziges Cookie: die signierte Sitzung (HttpOnly, SameSite=Strict, über HTTPS Secure,
14 Tage). Kein Tracking, keine Werbung, keine Analyse-Dienste.

## Was an andere Dienste geht

| Dienst | Was | Wann |
|---|---|---|
| OpenRouter, weiter an den Anbieter des Modells | der Reisewunsch, Profilangaben, frühere Bewertungen von Zielen; keine E-Mail-Adresse | bei jeder Anfrage. Gesendet wird mit `data_collection: deny`, also nur an Anbieter, die nicht mit den Daten trainieren |
| Open-Meteo | Name des Ziels, Koordinaten, Reisedaten | beim Tagesplan |
| OpenHolidays | Land, Reisedaten | beim Tagesplan mit Startdatum |
| OpenStreetMap (Kacheln) | Kartenausschnitt, IP-Adresse des Browsers, Herkunft der Seite (ohne Pfad) | beim Anzeigen der Karte, direkt aus dem Browser |
| Mailserver | E-Mail-Adresse, Code | beim Anmelden |

Die Freigabe-Seite schickt beim Laden der Kartenkacheln nur die Domain als Herkunft mit
(`Referrer-Policy: strict-origin`), nie den Pfad mit dem Token.
