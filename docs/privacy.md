# Data and privacy

The legally binding text is the page `/datenschutz`. This is the technical view of what goes where.

## What is stored

| Data | Why | How long |
|---|---|---|
| e-mail address | account, sign-in code | until the account is deleted |
| hash of the sign-in code | checking the code | 10 minutes, or until used |
| saved trips, profile, ratings, share links | what the person saves | until they delete it or the account |
| requests per person and day | the daily limit | until the account is deleted |
| active people per day | numbers for the operator | days without a person remain as a count |

"Delete account" removes everything that belongs to the person, at once and for good. Only the
total number of requests per day remains, with no link to a person.

There is one cookie: the signed session (HttpOnly, SameSite=Strict, Secure over HTTPS, 14 days).
No tracking, no ads, no analytics services.

## What goes to other services

| Service | What | When |
|---|---|---|
| OpenRouter, and on to the model provider | the trip wish, profile details, earlier ratings of destinations; no e-mail address | every request. Sent with `data_collection: deny`, so only to providers that do not train on the data |
| Open-Meteo | destination name, coordinates, travel dates | day plans |
| OpenHolidays | country, travel dates | day plans with a start date |
| OpenStreetMap (tiles) | map area, the browser's IP address, origin of the page (no path) | when a map is shown, directly from the browser |
| mail server | e-mail address, code | sign-in |

The shared page sends only the domain as referrer when it loads map tiles
(`Referrer-Policy: strict-origin`), never the path with the token.
