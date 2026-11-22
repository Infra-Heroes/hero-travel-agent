"""Does the day plan hold up? Checked by the server, not by the model.

- Places whose coordinates lie far from the destination are dropped from the map:
  the model guessed them wrong, and a pin in the sea helps nobody.
- Per day the way between the stops, in the order of the day, is estimated as the
  crow flies with a detour factor: short legs on foot, longer ones by car or bus.
  A day with more travel than its pace allows gets a warning.
- A place that is well known to be closed on the day's weekday gets a warning.

These are estimates without a routing service; they say so in the text.
"""

from __future__ import annotations

import math
from datetime import date
from itertools import pairwise

from app.schemas import Check, DayPlan, DayRoute, Facts, PlanResult

MAX_KM_FROM_CENTRE = 150.0
DETOUR = 1.3
WALK_KMH, WALK_UP_TO_KM = 4.5, 2.0
RIDE_KMH, RIDE_OVERHEAD_MIN = 35.0, 10
# Minutes of getting around per day that each pace still calls a day out, not a transfer.
PACE_MINUTES = {"entspannt": 75, "ausgewogen": 120, "aktiv": 180}
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WEEKDAY_NAMES = {
    "de": ["montags", "dienstags", "mittwochs", "donnerstags", "freitags", "samstags", "sonntags"],
    "en": [
        "on Mondays",
        "on Tuesdays",
        "on Wednesdays",
        "on Thursdays",
        "on Fridays",
        "on Saturdays",
        "on Sundays",
    ],
}


def km_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def leg_minutes(km: float) -> int:
    km *= DETOUR
    if km <= WALK_UP_TO_KM:
        return round(km / WALK_KMH * 60)
    return round(km / RIDE_KMH * 60) + RIDE_OVERHEAD_MIN


def _text(lang: str, de: str, en: str) -> str:
    return en if lang == "en" else de


def check_plan(plan: DayPlan, facts: Facts | None, pace: str = "ausgewogen", lang: str = "de") -> PlanResult:
    result = PlanResult.model_validate({**plan.model_dump(), "facts": facts.model_dump() if facts else None})
    budget = PACE_MINUTES.get(pace, PACE_MINUTES["ausgewogen"])
    checks: list[Check] = []
    routes: list[DayRoute] = []
    for day in result.days:
        if facts and facts.lat is not None and facts.lon is not None:
            day.places = [
                p
                for p in day.places
                if -90 <= p.lat <= 90
                and -180 <= p.lon <= 180
                and km_between(facts.lat, facts.lon, p.lat, p.lon) <= MAX_KM_FROM_CENTRE
            ]
        order = {"morning": 0, "afternoon": 1, "evening": 2}
        stops = sorted(day.places, key=lambda p: order[p.slot])
        km = 0.0
        minutes = 0
        for a, b in pairwise(stops):
            leg = km_between(a.lat, a.lon, b.lat, b.lon)
            km += leg
            minutes += leg_minutes(leg)
            if leg * DETOUR > 60:
                checks.append(
                    Check(
                        day=day.day,
                        level="warn",
                        text=_text(
                            lang,
                            f"Von {a.name} nach {b.name} sind es rund {leg * DETOUR:.0f} km.",
                            f"From {a.name} to {b.name} it is about {leg * DETOUR:.0f} km.",
                        ),
                    )
                )
        if len(stops) > 1:
            routes.append(DayRoute(day=day.day, km=round(km * DETOUR, 1), minutes=minutes))
        first_or_last = day.day in (1, len(result.days))
        if minutes > budget and not first_or_last:
            checks.append(
                Check(
                    day=day.day,
                    level="warn",
                    text=_text(
                        lang,
                        f"Viel unterwegs: geschätzt {minutes} Minuten Wege, für das Tempo „{pace}“ zu viel.",
                        f"A lot of travel: about {minutes} minutes on the way, much for this pace.",
                    ),
                )
            )
        try:
            weekday = date.fromisoformat(day.date).weekday()
        except ValueError:
            continue
        for p in day.places:
            if WEEKDAYS[weekday] in p.closed_on:
                checks.append(
                    Check(
                        day=day.day,
                        level="warn",
                        text=_text(
                            lang,
                            f"{p.name} ist {WEEKDAY_NAMES['de'][weekday]} meist geschlossen.",
                            f"{p.name} is usually closed {WEEKDAY_NAMES['en'][weekday]}.",
                        ),
                    )
                )
        if facts:
            for h in facts.holidays:
                if h.kind == "public" and h.start <= day.date <= h.end:
                    checks.append(
                        Check(
                            day=day.day,
                            level="info",
                            text=_text(
                                lang,
                                f"Feiertag ({h.name}): Geschäfte und manche Museen haben zu.",
                                f"Public holiday ({h.name}): shops and some museums are closed.",
                            ),
                        )
                    )
    result.routes = routes
    result.checks = checks
    return result
