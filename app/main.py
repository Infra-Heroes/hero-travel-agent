"""Urlaubs-Agent: a personal travel planner that suggests and plans, never books.

One instance per person, deployed on InfraHeroes. The agent has its own password
gate (app/auth.py): a customer app has no login in front of it. Saved trips live on
the instance's own volume.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from app.agent import AgentError, TravelAgent
from app.auth import COOKIE, SESSION_SECONDS, Gate, client_address, gate_middleware, is_https, login_page
from app.schemas import DayPlan, DayPlanRequest, Suggestions, TripBrief
from app.store import TripStore

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
STATIC = Path(__file__).parent / "static"

DAILY_CALLS = int(os.getenv("AGENT_DAILY_CALLS", "30"))

app = FastAPI(title="Urlaubs-Agent", docs_url=None, redoc_url=None)
store = TripStore(DATA_DIR / "trips.db")
agent = TravelAgent(spend=lambda: store.try_spend(DAILY_CALLS))
gate = Gate()


@app.middleware("http")
async def password_gate(request: Request, call_next):  # type: ignore[no-untyped-def]
    return await gate_middleware(request, call_next, gate)


@app.middleware("http")
async def security_headers(request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )
    return response


@app.exception_handler(AgentError)
async def agent_error(_, exc: AgentError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=503)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    # "auth" false means AGENT_PASSWORD is missing or too short: the agent serves nothing.
    return {"status": "ok", "demo": agent.fake, "auth": gate.configured}


@app.get("/login", include_in_schema=False)
async def login_form(request: Request) -> Response:
    if gate.valid_session(request.cookies.get(COOKIE)):
        return RedirectResponse("/", status_code=303)
    if not gate.configured:
        return login_page("Der Agent ist nicht eingerichtet (AGENT_PASSWORD fehlt).", 503)
    return login_page()


@app.post("/login", include_in_schema=False)
async def login(request: Request) -> Response:
    if not gate.configured:
        return login_page("Der Agent ist nicht eingerichtet (AGENT_PASSWORD fehlt).", 503)
    address = client_address(request)
    if gate.locked(address):
        return login_page("Zu viele Versuche. Bitte in einigen Minuten nochmal.", 429)
    body = (await request.body())[:4096].decode("utf-8", errors="replace")
    password = parse_qs(body).get("password", [""])[0]
    if not gate.check_password(password):
        gate.record_failure(address)
        return login_page("Das Passwort stimmt nicht.", 401)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE,
        gate.new_session(),
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=is_https(request),
    )
    return response


@app.post("/logout", include_in_schema=False)
async def logout() -> Response:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE)
    return response


@app.post("/api/suggest", response_model=Suggestions)
async def suggest(brief: TripBrief) -> Suggestions:
    return await agent.suggest(brief)


@app.post("/api/plan", response_model=DayPlan)
async def plan(req: DayPlanRequest) -> DayPlan:
    return await agent.plan_days(req)


class SaveTrip(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    kind: str = Field(pattern="^(suggestions|plan)$")
    payload: dict[str, Any]


@app.get("/api/trips")
async def list_trips() -> dict[str, Any]:
    return {"trips": store.list()}


@app.post("/api/trips", status_code=201)
async def save_trip(body: SaveTrip) -> dict[str, Any]:
    # Validate what is stored against the shape the page will render.
    try:
        (Suggestions if body.kind == "suggestions" else DayPlan).model_validate(body.payload)
    except ValidationError as exc:
        raise HTTPException(422, "Ungültiger Reiseplan") from exc
    return store.save(body.title, body.kind, body.payload)


@app.get("/api/trips/{trip_id}")
async def get_trip(trip_id: str) -> dict[str, Any]:
    trip = store.get(trip_id)
    if trip is None:
        raise HTTPException(404, "Reise nicht gefunden")
    return trip


@app.delete("/api/trips/{trip_id}", status_code=204)
async def delete_trip(trip_id: str) -> Response:
    if not store.delete(trip_id):
        raise HTTPException(404, "Reise nicht gefunden")
    return Response(status_code=204)


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@app.get("/api/trips/{trip_id}/calendar.ics")
async def trip_calendar(trip_id: str) -> Response:
    """The day plan as all-day calendar entries, one per day."""
    trip = store.get(trip_id)
    if trip is None or trip["kind"] != "plan":
        raise HTTPException(404, "Kein Tagesplan gefunden")
    plan = DayPlan.model_validate(trip["payload"])
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//InfraHeroes//Urlaubs-Agent//DE"]
    for day in plan.days:
        try:
            start = date.fromisoformat(day.date)
        except ValueError:
            continue
        desc = (
            f"Vormittag: {day.morning}\nNachmittag: {day.afternoon}\nAbend: {day.evening}\n"
            f"Essen: {day.food_tip}\nBei Regen: {day.bad_weather}\nWege: {day.logistics}"
        )
        lines += [
            "BEGIN:VEVENT",
            f"UID:{trip_id}-{day.day}@urlaubs-agent",
            f"DTSTAMP:{start.strftime('%Y%m%d')}T000000Z",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(start + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_ics_escape(f'Tag {day.day}: {day.theme} ({plan.destination})')}",
            f"DESCRIPTION:{_ics_escape(desc)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return Response(
        "\r\n".join(lines) + "\r\n",
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="reise-{trip_id}.ics"'},
    )


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
