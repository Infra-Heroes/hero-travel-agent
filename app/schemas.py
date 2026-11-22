"""What goes in and what comes back."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

LANGUAGE_NOTE = {
    "de": "",
    "en": "\nAntwortsprache: Englisch. Schreibe alle Texte auf Englisch (Orte behalten ihren üblichen Namen).",
}

# ── Requests ──────────────────────────────────────────────────────────────────


class TripBrief(BaseModel):
    """The wish, as somebody would say it to a travel agent."""

    when: str = Field(min_length=2, max_length=80, description="z. B. 'Herbstferien 2026' oder 'Mai'")
    nights: int = Field(ge=1, le=30)
    budget_eur: int = Field(ge=100, le=50000, description="Gesamtbudget für alle Reisenden")
    adults: int = Field(ge=1, le=10)
    children: int = Field(default=0, ge=0, le=10)
    origin: str = Field(min_length=2, max_length=60, description="Abreiseort")
    interests: list[str] = Field(default_factory=list, max_length=12)
    notes: str = Field(default="", max_length=1000)
    lang: str = Field(default="de", pattern="^(de|en)$")

    def as_prompt(self) -> str:
        return (
            f"Zeitraum: {self.when}\nDauer: {self.nights} Nächte\n"
            f"Budget gesamt: {self.budget_eur} EUR\n"
            f"Reisende: {self.adults} Erwachsene, {self.children} Kinder\n"
            f"Abreise ab: {self.origin}\n"
            f"Vorlieben: {', '.join(self.interests) or 'keine Angabe'}\n"
            f"Sonstiges: {self.notes or '-'}"
            f"{LANGUAGE_NOTE[self.lang]}"
        )


class DayPlanRequest(BaseModel):
    """A day plan for a place that is already decided."""

    destination: str = Field(min_length=2, max_length=100)
    days: int = Field(ge=1, le=14)
    start_date: date | None = None
    adults: int = Field(default=2, ge=1, le=10)
    children: int = Field(default=0, ge=0, le=10)
    pace: str = Field(default="entspannt", pattern="^(entspannt|ausgewogen|aktiv)$")
    interests: list[str] = Field(default_factory=list, max_length=12)
    notes: str = Field(default="", max_length=1000)
    lang: str = Field(default="de", pattern="^(de|en)$")

    def as_prompt(self) -> str:
        return (
            f"Ziel: {self.destination}\nTage: {self.days}\n"
            f"Start: {self.start_date.isoformat() if self.start_date else 'offen'}\n"
            f"Reisende: {self.adults} Erwachsene, {self.children} Kinder\n"
            f"Tempo: {self.pace}\n"
            f"Vorlieben: {', '.join(self.interests) or 'keine Angabe'}\n"
            f"Sonstiges: {self.notes or '-'}"
            f"{LANGUAGE_NOTE[self.lang]}"
        )


# ── Answers (also the JSON schema Claude fills) ───────────────────────────────


class CostItem(BaseModel):
    item: str
    eur: int


class Suggestion(BaseModel):
    destination: str
    why_it_fits: str
    weather: str
    getting_there: str
    accommodation: str
    highlights: list[str]
    cost_estimate: list[CostItem]
    total_estimate_eur: int
    caveat: str


class Suggestions(BaseModel):
    summary: str
    suggestions: list[Suggestion]


Weekday = Literal["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class Place(BaseModel):
    """A stop of the day, for the map and the plausibility check. The coordinates
    come from the model and are checked against the destination (app/checks.py)."""

    name: str
    slot: Literal["morning", "afternoon", "evening"]
    lat: float
    lon: float
    # Only weekdays on which the place is well known to be closed, else empty.
    closed_on: list[Weekday] = Field(default_factory=list)


class Day(BaseModel):
    day: int
    date: str
    theme: str
    morning: str
    afternoon: str
    evening: str
    food_tip: str
    bad_weather: str
    logistics: str
    # Plans saved before the map have no places.
    places: list[Place] = Field(default_factory=list)


class DayPlan(BaseModel):
    """What the model fills. The server adds facts and checks (PlanResult)."""

    destination: str
    overview: str
    days: list[Day]
    packing_list: list[str]


# ── Added by the server, not by the model ──────────────────────────────────────


class Weather(BaseModel):
    """Measured weather of the same days in past years (Open-Meteo archive)."""

    years: int
    temp_max_c: float
    temp_min_c: float
    rainy_days_share: float  # 0..1, days with at least 1 mm


class Holiday(BaseModel):
    name: str
    start: str
    end: str
    kind: Literal["public", "school"]
    regional: bool = False


class Facts(BaseModel):
    lat: float | None = None
    lon: float | None = None
    country: str = ""
    weather: Weather | None = None
    holidays: list[Holiday] = Field(default_factory=list)


class Check(BaseModel):
    day: int
    level: Literal["info", "warn"]
    text: str


class DayRoute(BaseModel):
    day: int
    km: float
    minutes: int


class PlanResult(DayPlan):
    facts: Facts | None = None
    routes: list[DayRoute] = Field(default_factory=list)
    checks: list[Check] = Field(default_factory=list)


class RefineRequest(BaseModel):
    """Change one day of a plan, keep the others."""

    plan: PlanResult
    day: int = Field(ge=1, le=14)
    wish: str = Field(min_length=3, max_length=300)
    pace: str = Field(default="ausgewogen", pattern="^(entspannt|ausgewogen|aktiv)$")
    lang: str = Field(default="de", pattern="^(de|en)$")
    # A saved plan is updated in place.
    trip_id: str | None = Field(default=None, max_length=32)


class Profile(BaseModel):
    """What a person would otherwise type in every time."""

    origin: str = Field(default="", max_length=60)
    adults: int = Field(default=2, ge=1, le=10)
    children: int = Field(default=0, ge=0, le=10)
    budget_eur: int | None = Field(default=None, ge=100, le=50000)
    interests: list[str] = Field(default_factory=list, max_length=12)
    avoid: str = Field(default="", max_length=300)
    accessibility: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=500)

    def as_prompt(self) -> str:
        parts = []
        if self.avoid:
            parts.append(f"Bitte vermeiden: {self.avoid}")
        if self.accessibility:
            parts.append(f"Barrierefreiheit: {self.accessibility}")
        if self.notes:
            parts.append(f"Allgemein: {self.notes}")
        return ("\nAus dem Profil:\n" + "\n".join(parts)) if parts else ""


class Vote(BaseModel):
    destination: str = Field(min_length=2, max_length=100)
    vote: int = Field(ge=-1, le=1)
