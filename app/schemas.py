"""What goes in and what comes back."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

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

    def as_prompt(self) -> str:
        return (
            f"Zeitraum: {self.when}\nDauer: {self.nights} Nächte\n"
            f"Budget gesamt: {self.budget_eur} EUR\n"
            f"Reisende: {self.adults} Erwachsene, {self.children} Kinder\n"
            f"Abreise ab: {self.origin}\n"
            f"Vorlieben: {', '.join(self.interests) or 'keine Angabe'}\n"
            f"Sonstiges: {self.notes or '-'}"
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

    def as_prompt(self) -> str:
        return (
            f"Ziel: {self.destination}\nTage: {self.days}\n"
            f"Start: {self.start_date.isoformat() if self.start_date else 'offen'}\n"
            f"Reisende: {self.adults} Erwachsene, {self.children} Kinder\n"
            f"Tempo: {self.pace}\n"
            f"Vorlieben: {', '.join(self.interests) or 'keine Angabe'}\n"
            f"Sonstiges: {self.notes or '-'}"
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


class DayPlan(BaseModel):
    destination: str
    overview: str
    days: list[Day]
    packing_list: list[str]
