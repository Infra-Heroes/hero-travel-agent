"""Real data for a day plan instead of the model's guesses.

- where: Open-Meteo geocoding (no key), the destination's centre and country
- weather: the same days in the last three years, as measured (Open-Meteo archive)
- holidays: public and school holidays at the destination (OpenHolidays API)

Every source is optional: a timeout, an unknown place or a country without data
leaves that part out, and the plan is made as before. Answers are cached in memory,
so the same destination is not looked up again for every request.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.schemas import Facts, Holiday, Weather

logger = logging.getLogger("travel-agent")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOLIDAYS_URL = "https://openholidaysapi.org"
TIMEOUT = float(os.getenv("FACTS_TIMEOUT_SECONDS", "6"))
YEARS = 3
CACHE_SECONDS = 24 * 3600


class FactFinder:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self._client = httpx.AsyncClient(timeout=TIMEOUT, transport=transport)
        self._cache: dict[tuple[Any, ...], tuple[float, Any]] = {}

    async def _get(self, url: str, params: dict[str, Any]) -> Any:
        key = (url, tuple(sorted(params.items())))
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        res = await self._client.get(url, params=params, headers={"Accept": "application/json"})
        res.raise_for_status()
        data = res.json()
        if len(self._cache) > 500:
            self._cache.clear()
        self._cache[key] = (time.monotonic(), data)
        return data

    async def locate(self, destination: str, lang: str = "de") -> dict[str, Any] | None:
        """Centre and country of a destination. "Lissabon, Portugal": the part before the
        comma is looked up, the part after it picks among places of the same name."""
        if not self.enabled:
            return None
        name, _, hint = destination.partition(",")
        hint = hint.strip().lower()
        # Destinations are typed in German or English: "Lissabon" exists only in German.
        # Without a country hint the largest place wins; with one, only a place in that
        # country counts (a Lissabon in Finland is no answer for "Lissabon, Portugal").
        best = None
        for language in dict.fromkeys((lang, "de", "en")):
            try:
                data = await self._get(
                    GEOCODE_URL, {"name": name.strip(), "count": 10, "language": language, "format": "json"}
                )
            except (httpx.HTTPError, ValueError) as exc:
                logger.info("geocoding %r failed: %s", destination, exc)
                return None
            results = data.get("results") or []
            if hint:
                for r in results:
                    if hint in str(r.get("country", "")).lower() or hint in str(r.get("admin1", "")).lower():
                        return r
                continue
            for r in results:
                if best is None or (r.get("population") or 0) > (best.get("population") or 0):
                    best = r
        return best

    async def weather(self, lat: float, lon: float, start: date, days: int) -> Weather | None:
        """The same calendar days in the last YEARS years, as measured."""
        maxes: list[float] = []
        mins: list[float] = []
        rain: list[float] = []
        for back in range(1, YEARS + 1):
            try:
                first = start.replace(year=start.year - back)
            except ValueError:  # 29 February
                first = (start - timedelta(days=1)).replace(year=start.year - back)
            last = first + timedelta(days=max(days, 1) - 1)
            if last >= datetime.now(UTC).date():
                continue
            try:
                data = await self._get(
                    ARCHIVE_URL,
                    {
                        "latitude": round(lat, 3),
                        "longitude": round(lon, 3),
                        "start_date": first.isoformat(),
                        "end_date": last.isoformat(),
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                        "timezone": "auto",
                    },
                )
            except (httpx.HTTPError, ValueError) as exc:
                logger.info("weather lookup failed: %s", exc)
                continue
            daily = data.get("daily") or {}
            maxes += [v for v in daily.get("temperature_2m_max") or [] if v is not None]
            mins += [v for v in daily.get("temperature_2m_min") or [] if v is not None]
            rain += [v for v in daily.get("precipitation_sum") or [] if v is not None]
        if not maxes or not mins:
            return None
        return Weather(
            years=YEARS,
            temp_max_c=round(sum(maxes) / len(maxes), 1),
            temp_min_c=round(sum(mins) / len(mins), 1),
            rainy_days_share=round(sum(1 for r in rain if r >= 1.0) / len(rain), 2) if rain else 0.0,
        )

    async def holidays(self, country: str, start: date, days: int, lang: str = "de") -> list[Holiday]:
        end = start + timedelta(days=max(days, 1) - 1)
        out: list[Holiday] = []
        for kind, path in (("public", "PublicHolidays"), ("school", "SchoolHolidays")):
            try:
                data = await self._get(
                    f"{HOLIDAYS_URL}/{path}",
                    {
                        "countryIsoCode": country.upper(),
                        "languageIsoCode": lang.upper(),
                        "validFrom": start.isoformat(),
                        "validTo": end.isoformat(),
                    },
                )
            except (httpx.HTTPError, ValueError) as exc:
                logger.info("holiday lookup %s %s failed: %s", country, kind, exc)
                continue
            seen = set()
            for h in data if isinstance(data, list) else []:
                names = h.get("name") or []
                name = next((n.get("text") for n in names if n.get("language") == lang.upper()), None)
                name = name or (names[0].get("text") if names else "")
                key = (name, h.get("startDate"), h.get("endDate"))
                if not name or key in seen:
                    continue
                seen.add(key)
                out.append(
                    Holiday(
                        name=name,
                        start=str(h.get("startDate", ""))[:10],
                        end=str(h.get("endDate", ""))[:10],
                        kind=kind,  # type: ignore[arg-type]
                        regional=not h.get("nationwide", True),
                    )
                )
        return out[:20]

    async def for_plan(self, destination: str, start: date | None, days: int, lang: str) -> Facts | None:
        place = await self.locate(destination, lang)
        if place is None:
            return None
        lat, lon = float(place["latitude"]), float(place["longitude"])
        facts = Facts(lat=lat, lon=lon, country=str(place.get("country_code", "")))
        if start is not None:
            weather, holidays = await asyncio.gather(
                self.weather(lat, lon, start, days),
                self.holidays(facts.country, start, days, lang) if facts.country else _none(),
            )
            facts.weather = weather
            facts.holidays = holidays or []
        return facts


async def _none() -> list[Holiday]:
    return []


def facts_prompt(facts: Facts | None) -> str:
    """The facts as the model gets them, so the plan builds on them."""
    if facts is None:
        return ""
    lines = []
    if facts.weather:
        w = facts.weather
        lines.append(
            f"Gemessenes Wetter dieser Tage in den letzten {w.years} Jahren: "
            f"{w.temp_min_c:.0f} bis {w.temp_max_c:.0f} °C, an {round(w.rainy_days_share * 100)} % "
            "der Tage Regen. Plane danach (z. B. Badetage, Regenalternativen)."
        )
    for h in facts.holidays:
        what = "Feiertag" if h.kind == "public" else "Schulferien"
        where = " (regional)" if h.regional else ""
        lines.append(f"{what}{where} am Ziel: {h.name}, {h.start} bis {h.end}")
    if any(h.kind == "public" for h in facts.holidays):
        lines.append("An Feiertagen sind Geschäfte und manche Museen zu; Ausflugsziele sind voller.")
    return ("\n\nFakten (verlässlich, nicht erfunden):\n" + "\n".join(lines)) if lines else ""
