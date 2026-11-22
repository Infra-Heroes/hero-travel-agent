# Features

## Trip ideas

Input: time of travel, nights, budget for everyone, travellers, place of departure, interests and
free text. The agent suggests exactly three different destinations, each with:

- why it fits, typical weather, getting there with time and cost, kind of accommodation
- three to five highlights
- a cost estimate by item and a total
- an honest caveat

Each suggestion has 👍 and 👎. Liked destinations are favoured in later suggestions, disliked ones
are not suggested again.

## Day plan

For a chosen or known destination, 1 to 14 days, at a relaxed, balanced or active pace. Each day
has a theme, morning, afternoon, evening, a food tip, a rainy-day alternative and a note on getting
around. The first and last day allow for arrival and departure. A packing list comes with it.

### Facts instead of guesses

With a start date the server looks up, before planning:

- **Weather:** highs, lows and the share of rainy days on the same calendar days in the last three
  years, as measured ([Open-Meteo archive](https://open-meteo.com/en/docs/historical-weather-api)).
- **Public and school holidays** at the destination ([OpenHolidays](https://www.openholidaysapi.org)),
  for the roughly 35 countries it covers.

Both go into the plan (beach days, rainy-day options, crowded sights) and are shown above it. If a
source is down, the plan is made without it.

### Map

The model names the places of each day with coordinates. The server drops places more than 150 km
from the destination; the rest appear on an OpenStreetMap map that can be filtered by day.

### Feasibility

`app/checks.py` checks every day without an external service:

- travel between the places in the order of the day: straight line times 1.3, on foot up to
  2 km, beyond that by car or bus with 10 minutes added
- a warning when a day has more travel than its pace allows (75, 120 or 180 minutes)
- a warning for a single leg over 60 km
- a warning when a place is known to be closed on that weekday
- a note on public holidays

### Refine a day

"Adjust this day" replans a single day to a wish such as "more relaxed" or "more for kids". The
other days stay; a saved plan is updated. It costs one request, like a new plan.

## My trips

Save suggestions and plans (up to 100), print them or save as PDF, export a calendar file (whole
days or with times) or add single days to Google Calendar.

### Sharing

A saved plan can get a link `/s/<token>`, valid for 7, 30 or 90 days. Anyone with it sees the trip
without an account but cannot change it. Sharing again makes a new link; "Withdraw link" ends it at
once. The page is not indexed and shows nothing about the person who shared it.

## Profile

Place of departure, travellers, budget, interests, things to avoid, accessibility needs and other
notes. The profile prefills the forms and goes with every request to the model.

## Accounts and limits

Sign in with an e-mail address and a six-digit code, no password. Every person has a daily number of
requests and the agent as a whole has one too, because every request costs money. The account can
be deleted with all its data at any time. See [privacy.md](privacy.md) and
[../SECURITY.md](../SECURITY.md).

## Languages

German and English. The page follows the browser's language and can be switched; the model answers
in the chosen language.
