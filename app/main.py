"""Urlaubs-Agent: a travel planner that suggests and plans, never books.

The start page is public. The planner itself is behind an account: an e-mail address and
a one-time code sent to it (app/auth.py). Every person has a daily number of requests
and the agent as a whole has one too, because every request costs money at the model.
Saved trips belong to their user. Numbers (users per day, requests, cost) are stored
(app/store.py) and exposed for Prometheus (app/metrics.py).
"""

from __future__ import annotations

import hmac
import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from app.agent import AgentError, TravelAgent
from app.auth import (
    CODE_SECONDS,
    COOKIE,
    SESSION_SECONDS,
    Auth,
    client_address,
    is_https,
    normalize_email,
)
from app.mailer import Mailer, MailError
from app.mailtemplate import login_mail_html
from app.metrics import CONTENT_TYPE, Metrics
from app.schemas import DayPlan, DayPlanRequest, Suggestions, TripBrief
from app.store import Store

logger = logging.getLogger("travel-agent")

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
STATIC = Path(__file__).parent / "static"
USER_DAILY_QUERIES = int(os.getenv("USER_DAILY_QUERIES", "10"))
AGENT_DAILY_CALLS = int(os.getenv("AGENT_DAILY_CALLS", "200"))
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")

app = FastAPI(title="Urlaubs-Agent", docs_url=None, redoc_url=None)
store = Store(DATA_DIR / "agent.db")
auth = Auth(DATA_DIR)
mailer = Mailer()
metrics = Metrics(store, USER_DAILY_QUERIES, AGENT_DAILY_CALLS)


def _record_call(seconds: float, usage: dict[str, Any]) -> None:
    metrics.model_seconds.observe(seconds)
    metrics.tokens.labels("prompt").inc(int(usage.get("prompt_tokens") or 0))
    metrics.tokens.labels("completion").inc(int(usage.get("completion_tokens") or 0))
    metrics.cost.inc(float(usage.get("cost") or 0))


agent = TravelAgent(on_call=_record_call)


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


def current_user(request: Request) -> dict[str, Any]:
    user_id = auth.session_user(request.cookies.get(COOKIE))
    user = store.user(user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "Bitte anmelden.")
    return user


def _is_loopback(request: Request) -> bool:
    return client_address(request) in ("127.0.0.1", "::1", "localhost")


def require_operator(request: Request) -> None:
    """Metrics and statistics: a bearer token (METRICS_TOKEN) or, with none configured, only
    from the machine itself."""
    if METRICS_TOKEN:
        given = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(given, METRICS_TOKEN):
            raise HTTPException(401, "Nicht erlaubt.")
    elif not _is_loopback(request):
        raise HTTPException(403, "Nicht erlaubt.")


# -- public -------------------------------------------------------------------


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    # "mail" false means nobody can sign in: no SMTP server is configured.
    return {"status": "ok", "demo": agent.fake, "mail": mailer.configured}


@app.get("/metrics", include_in_schema=False)
async def prometheus(request: Request) -> Response:
    require_operator(request)
    return Response(metrics.render(), media_type=CONTENT_TYPE)


@app.get("/api/stats", include_in_schema=False)
async def stats(request: Request, days: int = 30) -> dict[str, Any]:
    """Users and requests per day, newest first."""
    require_operator(request)
    return {"days": store.stats(max(1, min(days, 365))), "users": store.user_count()}


@app.get("/impressum", include_in_schema=False)
async def impressum() -> FileResponse:
    return FileResponse(STATIC / "impressum.html", headers={"Cache-Control": "no-cache"})


@app.get("/datenschutz", include_in_schema=False)
async def datenschutz() -> FileResponse:
    return FileResponse(STATIC / "datenschutz.html", headers={"Cache-Control": "no-cache"})


@app.get("/robots.txt", include_in_schema=False)
async def robots() -> Response:
    return Response("User-agent: *\nDisallow: /app\nDisallow: /api/\n", media_type="text/plain")


@app.get("/", include_in_schema=False)
async def landing() -> FileResponse:
    return FileResponse(STATIC / "landing.html", headers={"Cache-Control": "no-cache"})


# -- signing in ----------------------------------------------------------------


class CodeRequest(BaseModel):
    email: str = Field(max_length=254)


class CodeEntry(BaseModel):
    email: str = Field(max_length=254)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


SENT = {"ok": True, "message": "Wenn die Adresse stimmt, ist ein Code unterwegs. Er gilt 10 Minuten."}


@app.post("/api/auth/request")
async def request_code(body: CodeRequest, request: Request) -> JSONResponse:
    email = normalize_email(body.email)
    if email is None:
        metrics.code_requests.labels("invalid").inc()
        raise HTTPException(422, "Bitte eine gültige E-Mail-Adresse eingeben.")
    address = client_address(request)
    if not (auth.ask_client.allow(address) and auth.ask_total.allow("all") and auth.ask_email.allow(email)):
        metrics.code_requests.labels("limited").inc()
        raise HTTPException(429, "Zu viele Anfragen. Bitte in einigen Minuten nochmal.")
    if not mailer.configured:
        logger.error("sign-in requested but no mail backend is configured")
        raise HTTPException(503, "Die Anmeldung ist gerade nicht möglich.")
    if not auth.allowed(email):
        # Same answer as for a known address: nobody learns who may sign up.
        metrics.code_requests.labels("not_allowed").inc()
        return JSONResponse(SENT)
    code = auth.new_code()
    store.put_code(email, auth.code_hash(email, code), CODE_SECONDS)
    try:
        await mailer.send(
            email,
            "Dein Code für den Urlaubs-Agent",
            f"Dein Code: {code}\n\nEr gilt 10 Minuten und nur einmal. "
            "Wenn du ihn nicht angefordert hast, kannst du diese Mail ignorieren.\n",
            html=login_mail_html(code),
        )
    except MailError as exc:
        logger.error("could not send the sign-in mail: %s", exc)
        metrics.code_requests.labels("mail_failed").inc()
        raise HTTPException(503, "Die Anmeldung ist gerade nicht möglich.") from exc
    metrics.code_requests.labels("sent").inc()
    return JSONResponse(SENT)


@app.post("/api/auth/verify")
async def verify_code(body: CodeEntry, request: Request) -> JSONResponse:
    email = normalize_email(body.email)
    if email is None or not auth.try_client.allow(client_address(request)):
        metrics.logins.labels("limited").inc()
        raise HTTPException(429, "Zu viele Versuche. Bitte in einigen Minuten nochmal.")
    result = store.take_code(email, auth.code_matches(email, body.code))
    metrics.logins.labels(result).inc()
    if result != "ok":
        message = (
            "Der Code ist abgelaufen. Bitte einen neuen anfordern."
            if result in ("expired", "none")
            else ("Der Code stimmt nicht.")
        )
        raise HTTPException(401, message)
    user, created = store.login(email)
    if created:
        metrics.signups.inc()
    response = JSONResponse({"ok": True, "email": user["email"]})
    response.set_cookie(
        COOKIE,
        auth.new_session(user["id"]),
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=is_https(request),
    )
    return response


@app.post("/api/auth/logout")
async def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE)
    return response


@app.delete("/api/me")
async def delete_me(request: Request) -> JSONResponse:
    """Erase the account and everything stored for it (GDPR Art. 17)."""
    user = current_user(request)
    store.delete_user(user["id"])
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE)
    return response


@app.get("/api/me")
async def me(request: Request) -> dict[str, Any]:
    user = current_user(request)
    used = store.calls_today(user["id"])
    return {
        "email": user["email"],
        "used_today": used,
        "limit": USER_DAILY_QUERIES,
        "remaining": max(0, USER_DAILY_QUERIES - used),
    }


# -- the planner (signed in) -----------------------------------------------------


@app.get("/app", include_in_schema=False)
async def planner_page(request: Request) -> Response:
    user_id = auth.session_user(request.cookies.get(COOKIE))
    if not user_id or store.user(user_id) is None:
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


def _charge(user: dict[str, Any], kind: str) -> None:
    """Take one request from the person's day and the agent's, or say which is used up."""
    result = store.try_spend(user["id"], USER_DAILY_QUERIES, AGENT_DAILY_CALLS)
    if result == "user":
        metrics.queries.labels(kind, "limited_user").inc()
        raise HTTPException(
            429, f"Du hast dein Tageslimit von {USER_DAILY_QUERIES} Anfragen erreicht. Morgen geht es weiter."
        )
    if result == "global":
        metrics.queries.labels(kind, "limited_global").inc()
        raise HTTPException(503, "Der Agent ist für heute ausgelastet. Bitte morgen wieder versuchen.")


@app.post("/api/suggest", response_model=Suggestions)
async def suggest(brief: TripBrief, request: Request) -> Suggestions:
    user = current_user(request)
    _charge(user, "suggest")
    try:
        result = await agent.suggest(brief)
    except AgentError:
        metrics.queries.labels("suggest", "error").inc()
        raise
    metrics.queries.labels("suggest", "ok").inc()
    return result


@app.post("/api/plan", response_model=DayPlan)
async def plan(req: DayPlanRequest, request: Request) -> DayPlan:
    user = current_user(request)
    _charge(user, "plan")
    try:
        result = await agent.plan_days(req)
    except AgentError:
        metrics.queries.labels("plan", "error").inc()
        raise
    metrics.queries.labels("plan", "ok").inc()
    return result


class SaveTrip(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    kind: str = Field(pattern="^(suggestions|plan)$")
    payload: dict[str, Any]


@app.get("/api/trips")
async def list_trips(request: Request) -> dict[str, Any]:
    return {"trips": store.list(current_user(request)["id"])}


@app.post("/api/trips", status_code=201)
async def save_trip(body: SaveTrip, request: Request) -> dict[str, Any]:
    user = current_user(request)
    # Validate what is stored against the shape the page will render.
    try:
        (Suggestions if body.kind == "suggestions" else DayPlan).model_validate(body.payload)
    except ValidationError as exc:
        raise HTTPException(422, "Ungültiger Reiseplan") from exc
    return store.save(user["id"], body.title, body.kind, body.payload)


@app.get("/api/trips/{trip_id}")
async def get_trip(trip_id: str, request: Request) -> dict[str, Any]:
    trip = store.get(current_user(request)["id"], trip_id)
    if trip is None:
        raise HTTPException(404, "Reise nicht gefunden")
    return trip


@app.delete("/api/trips/{trip_id}", status_code=204)
async def delete_trip(trip_id: str, request: Request) -> Response:
    if not store.delete(current_user(request)["id"], trip_id):
        raise HTTPException(404, "Reise nicht gefunden")
    return Response(status_code=204)


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@app.get("/api/trips/{trip_id}/calendar.ics")
async def trip_calendar(trip_id: str, request: Request) -> Response:
    """The day plan as all-day calendar entries, one per day."""
    trip = store.get(current_user(request)["id"], trip_id)
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
