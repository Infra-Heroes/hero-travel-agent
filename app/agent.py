"""The travel agent's two jobs: suggest trips for a brief, and plan the days.

Both are single structured calls to a model on OpenRouter (DeepSeek V4 Flash by
default: cheap, long context, JSON-schema output). The model answers in JSON that
matches a schema, so the page gets data it can render rather than prose it has to
parse. Nothing here books, pays or contacts anybody: prices are estimates and say so.

Without an API key (or with AGENT_FAKE=1) a deterministic stand-in answers, so the app
runs locally and in tests without a network or a bill.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from app.schemas import DayPlan, DayPlanRequest, Suggestions, TripBrief

logger = logging.getLogger("travel-agent")

BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("AGENT_MODEL", "deepseek/deepseek-v4-flash")
EFFORT = os.getenv("AGENT_EFFORT", "medium")  # low | medium | high
MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "8000"))
TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))


class AgentError(Exception):
    """Something the person should be told, in their language."""


SYSTEM = """Du bist ein erfahrener, ehrlicher Reiseplaner für Menschen aus Deutschland.
Du buchst nichts und versprichst keine Verfügbarkeit. Preise sind immer realistische
Schätzungen in Euro für die genannte Personenzahl und werden als Schätzung gekennzeichnet.
Berücksichtige Reisezeit, typisches Wetter im Zeitraum, Budget, Mitreisende (z. B. Kinder)
und die Vorlieben. Schreibe kurz, konkret und auf Deutsch. Erfinde keine Öffnungszeiten
oder exakten Preise einzelner Orte; nenne bekannte, real existierende Orte."""


def _schema(model: type) -> dict[str, Any]:
    """A JSON schema the structured-output endpoint accepts: every object
    closed (additionalProperties false) and every field required."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def close(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return close(dict(defs[node["$ref"].split("/")[-1]]))
            out = {k: close(v) for k, v in node.items() if k not in ("title", "default")}
            if out.get("type") == "object":
                out["additionalProperties"] = False
                out["required"] = list(out.get("properties", {}))
            return out
        if isinstance(node, list):
            return [close(v) for v in node]
        return node

    return close(schema)


class TravelAgent:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        on_call: Callable[[float, dict[str, Any]], None] | None = None,
    ) -> None:
        """transport: for tests. on_call(seconds, usage): told after every model call, for
        the metrics. usage is what OpenRouter reported (tokens and cost), possibly empty."""
        self._on_call = on_call
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        # A value that is not an OpenRouter key (a placeholder, a typo) means "no key": the
        # agent then runs in demo mode instead of sending every request to a 401.
        if key and not key.startswith("sk-or-"):
            logger.warning("OPENROUTER_API_KEY does not look like an OpenRouter key: running in demo mode")
            key = ""
        self._key = key
        self.fake = os.getenv("AGENT_FAKE") == "1" or not self._key
        self._client = (
            None
            if self.fake
            else httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=TIMEOUT_SECONDS,
                transport=transport,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "X-Title": "Urlaubs-Agent",
                },
            )
        )

    def _body(self, prompt: str, model_cls: type, extra: str = "") -> dict[str, Any]:
        return {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt + extra},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "result", "strict": True, "schema": _schema(model_cls)},
            },
            # Only providers that really support the schema; others would answer in prose.
            "provider": {"require_parameters": True},
            "reasoning": {"effort": EFFORT, "exclude": True},
            # Ask OpenRouter to report tokens and cost in the answer.
            "usage": {"include": True},
        }

    async def _call(self, body: dict[str, Any]) -> tuple[str, str]:
        assert self._client is not None
        started = time.monotonic()
        try:
            res = await self._client.post("/chat/completions", json=body)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise AgentError("Der Agent ist gerade nicht erreichbar.") from exc
        finally:
            elapsed = time.monotonic() - started
        if res.status_code == 429:
            raise AgentError("Der Agent ist gerade ausgelastet. Bitte gleich nochmal versuchen.")
        if res.status_code >= 400:
            # 401/402 are the operator's problem (key, credit): log it, tell the person little.
            logger.error("OpenRouter answered %s: %s", res.status_code, res.text[:300])
            raise AgentError("Der Agent konnte die Anfrage nicht bearbeiten.")
        try:
            data = res.json()
            if self._on_call is not None:
                self._on_call(elapsed, data.get("usage") or {})
            choice = data["choices"][0]
            return choice["message"].get("content") or "", choice.get("finish_reason") or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.error("Unreadable OpenRouter answer: %s", res.text[:300])
            raise AgentError("Der Agent konnte die Anfrage nicht bearbeiten.") from exc

    async def _ask(self, prompt: str, model_cls: type) -> Any:
        extra = ""
        for attempt in (1, 2):
            text, finish = await self._call(self._body(prompt, model_cls, extra))
            if finish == "length":
                raise AgentError("Der Plan wurde zu lang. Bitte weniger Tage oder weniger Details anfragen.")
            if finish == "content_filter":
                raise AgentError("Zu dieser Anfrage kann der Agent keinen Vorschlag machen.")
            try:
                return model_cls.model_validate(json.loads(text))
            except (ValueError, ValidationError):
                logger.warning("Model answer did not match the schema (attempt %s)", attempt)
                extra = (
                    "\n\nWICHTIG: Antworte ausschließlich mit gültigem JSON, das exakt dem "
                    "vorgegebenen Schema entspricht, ohne Text davor oder danach."
                )
        raise AgentError("Der Agent hat keine brauchbare Antwort geliefert. Bitte nochmal versuchen.")

    async def suggest(self, brief: TripBrief) -> Suggestions:
        if self.fake:
            return fake_suggestions(brief)
        prompt = (
            "Schlage genau 3 unterschiedliche Reiseziele für diesen Wunsch vor. "
            "Für jedes: warum es passt, typisches Wetter im Zeitraum, wie man hinkommt "
            "(mit geschätzter Reisezeit und Kosten), Unterkunftsart, 3-5 Highlights, "
            "eine Kostenschätzung nach Posten und eine ehrliche Einschränkung.\n\n"
            f"Wunsch:\n{brief.as_prompt()}"
        )
        return await self._ask(prompt, Suggestions)

    async def plan_days(self, req: DayPlanRequest) -> DayPlan:
        if self.fake:
            return fake_day_plan(req)
        prompt = (
            f"Erstelle einen Tagesplan für {req.days} Tage in {req.destination}. "
            "Pro Tag: ein Motto, Vormittag, Nachmittag, Abend (jeweils konkrete Orte "
            "oder Aktivitäten mit kurzer Begründung), ein Essens-Tipp, eine Schlechtwetter-"
            "Alternative und ein realistischer Hinweis zu Wegen und Zeiten. Der erste und "
            "letzte Tag berücksichtigen An- und Abreise. Danach eine Packliste passend zu "
            "Ziel, Jahreszeit und Mitreisenden.\n\n"
            f"Angaben:\n{req.as_prompt()}"
        )
        return await self._ask(prompt, DayPlan)


# ── Demo answers ──────────────────────────────────────────────────────────────


def fake_suggestions(brief: TripBrief) -> Suggestions:
    people = brief.adults + brief.children
    base = max(brief.budget_eur, 300)
    picks = [
        (
            "Madeira, Portugal",
            "Flug ab " + brief.origin + ", ca. 4 h",
            0.35,
            "Ferienwohnung mit Meerblick",
            ["Levada-Wanderung 25 Fontes", "Funchal Altstadt & Mercado", "Naturpools Porto Moniz"],
        ),
        (
            "Kreta, Griechenland",
            "Flug ab " + brief.origin + ", ca. 3 h",
            0.30,
            "Familienhotel am Strand",
            ["Elafonisi-Strand", "Altstadt Chania", "Samaria-Schlucht (für Geübte)"],
        ),
        (
            "Gardasee, Italien",
            "Bahn oder Auto, ca. 7-9 h",
            0.15,
            "Agriturismo oder Ferienhaus",
            ["Sirmione", "Monte Baldo Seilbahn", "Radweg Limone"],
        ),
    ]
    out = []
    for name, getting_there, travel_share, stay, highlights in picks:
        travel = round(base * travel_share)
        lodging = round(base * 0.4)
        food = round(base * 0.15)
        extras = max(base - travel - lodging - food, 0)
        out.append(
            {
                "destination": name,
                "why_it_fits": f"Passt zu {', '.join(brief.interests) or 'deinen Wünschen'} und ist für {people} Personen gut machbar.",
                "weather": "Meist mild bis warm, vereinzelt Schauer (typisch für den Zeitraum).",
                "getting_there": getting_there,
                "accommodation": stay,
                "highlights": highlights,
                "cost_estimate": [
                    {"item": "Anreise", "eur": travel},
                    {"item": "Unterkunft", "eur": lodging},
                    {"item": "Essen", "eur": food},
                    {"item": "Ausflüge & Sonstiges", "eur": extras},
                ],
                "total_estimate_eur": travel + lodging + food + extras,
                "caveat": "Demo-Vorschlag ohne echte Preise - mit API-Key plant der Agent wirklich.",
            }
        )
    return Suggestions.model_validate(
        {"summary": "Drei Ideen für deinen Wunsch (Demo-Modus).", "suggestions": out}
    )


def fake_day_plan(req: DayPlanRequest) -> DayPlan:
    start = req.start_date or datetime.now(ZoneInfo("Europe/Berlin")).date()
    days = []
    for i in range(req.days):
        first, last = i == 0, i == req.days - 1
        days.append(
            {
                "day": i + 1,
                "date": (start + timedelta(days=i)).isoformat(),
                "theme": "Ankommen" if first else "Abreise" if last else f"Entdecken in {req.destination}",
                "morning": "Anreise und Check-in" if first else f"Spaziergang durch {req.destination}",
                "afternoon": "Umgebung erkunden" if not last else "Koffer packen, letzter Kaffee",
                "evening": "Abendessen in der Nähe" if not last else "Heimreise",
                "food_tip": "Lokales Restaurant mit regionaler Küche",
                "bad_weather": "Museum oder Café",
                "logistics": "Alles zu Fuß oder mit kurzer Fahrt erreichbar.",
            }
        )
    return DayPlan.model_validate(
        {
            "destination": req.destination,
            "overview": f"{req.days} entspannte Tage in {req.destination} (Demo-Modus).",
            "days": days,
            "packing_list": ["Reisepass/Ausweis", "Ladekabel", "Sonnencreme", "Regenjacke", "Bequeme Schuhe"],
        }
    )
