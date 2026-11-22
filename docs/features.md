# Funktionen

## Ideen finden

Eingabe: Zeitraum, Nächte, Budget für alle zusammen, Reisende, Abreiseort, Vorlieben und freier
Text. Der Agent schlägt genau drei unterschiedliche Ziele vor. Für jedes:

- warum es passt, typisches Wetter, Anreise mit Zeit und Kosten, Unterkunftsart
- drei bis fünf Highlights
- eine Kostenschätzung nach Posten und ein Gesamtbetrag
- eine ehrliche Einschränkung

Unter jedem Vorschlag stehen 👍 und 👎. Gemochtes wird bei den nächsten Vorschlägen bevorzugt,
Abgelehntes nicht noch einmal vorgeschlagen.

## Tagesplan

Für ein gewähltes oder bekanntes Ziel, 1 bis 14 Tage, im Tempo entspannt, ausgewogen oder aktiv.
Jeder Tag hat ein Motto, Vormittag, Nachmittag, Abend, einen Essens-Tipp, eine Alternative bei
Regen und einen Hinweis zu Wegen. Der erste und der letzte Tag berücksichtigen An- und Abreise.
Dazu kommt eine Packliste.

### Fakten statt Schätzung

Mit Startdatum holt der Server vor dem Planen:

- **Wetter:** Höchst- und Tiefstwerte und den Anteil der Regentage derselben Kalendertage in den
  letzten drei Jahren, gemessen ([Open-Meteo Archiv](https://open-meteo.com/en/docs/historical-weather-api)).
- **Feiertage und Schulferien** am Ziel ([OpenHolidays](https://www.openholidaysapi.org)), für die
  rund 35 Länder, die die Quelle kennt.

Beides fließt in den Plan ein (Badetage, Regenalternativen, volle Ausflugsziele) und steht über dem
Plan. Fällt eine Quelle aus, wird ohne sie geplant.

### Karte

Das Modell nennt pro Tag die besuchten Orte mit Koordinaten. Orte mehr als 150 km vom Ziel weg
verwirft der Server, der Rest erscheint auf einer OpenStreetMap-Karte, filterbar nach Tag.

### Machbarkeit

`app/checks.py` prüft jeden Tag ohne externen Dienst:

- Wege zwischen den Orten in der Reihenfolge des Tages: Luftlinie mal 1,3, bis 2 km zu Fuß,
  darüber mit Auto oder Bus samt 10 Minuten Aufschlag
- Warnung, wenn ein Tag mehr Wege hat, als das Tempo verträgt (75, 120 oder 180 Minuten)
- Warnung bei einem einzelnen Weg über 60 km
- Warnung, wenn ein Ort an diesem Wochentag bekanntermaßen geschlossen ist
- Hinweis an Feiertagen

### Einen Tag anpassen

„Diesen Tag anpassen“ plant einen einzelnen Tag nach einem Wunsch neu, zum Beispiel
„entspannter“ oder „mehr für Kinder“. Die anderen Tage bleiben, ein gespeicherter Plan wird
aktualisiert. Das kostet eine Anfrage, wie ein neuer Plan.

## Meine Reisen

Vorschläge und Pläne merken (bis zu 100), drucken oder als PDF speichern, als Kalenderdatei
exportieren (ganze Tage oder mit Uhrzeiten) oder pro Tag in den Google-Kalender übernehmen.

### Teilen

Ein gespeicherter Plan bekommt auf Wunsch einen Link `/s/<token>`, der 7, 30 oder 90 Tage gilt.
Wer ihn hat, sieht die Reise ohne Konto, kann aber nichts ändern. Neu teilen macht einen neuen
Link, „Link zurückziehen“ macht ihn sofort ungültig. Die Seite wird nicht indexiert und zeigt
nichts über die Person, die geteilt hat.

## Profil

Abreiseort, Reisende, Budget, Vorlieben, was man meiden will, Barrierefreiheit und sonstige
Hinweise. Das Profil füllt die Formulare vor und geht mit jeder Anfrage an das Modell.

## Konto und Limits

Anmelden mit E-Mail-Adresse und sechsstelligem Code, ohne Passwort. Jede Person hat ein
Tageslimit an Anfragen, der Agent insgesamt auch, weil jede Anfrage Geld kostet. Das Konto lässt
sich jederzeit samt aller Daten löschen. Details in [privacy.md](privacy.md) und
[../SECURITY.md](../SECURITY.md).

## Sprachen

Deutsch und Englisch. Die Seite folgt der Browsersprache und lässt sich umschalten; das Modell
antwortet in der gewählten Sprache.
