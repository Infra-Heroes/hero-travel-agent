"""One password in front of the whole agent.

A customer app on InfraHeroes has no login in front of it: the platform routes the
address to the app and nothing else. This agent holds one person's saved trips and
spends money on a model for every request, so it brings its own gate.

- AGENT_PASSWORD (a platform secret) is the password. Without it the agent refuses
  to serve anything but /healthz: a missing secret must not mean "open".
- A correct password sets a signed session cookie (HttpOnly, SameSite=Strict, Secure
  behind https). The signing key is derived from the password, so changing the
  password logs everybody out.
- Wrong passwords are limited per client address and for everybody together, so
  guessing is slow even if the address cannot be trusted.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import deque
from html import escape

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

COOKIE = "agent_session"
SESSION_SECONDS = 14 * 24 * 3600

# Paths that never need a session: the health check, the login itself and the
# static files the login page uses (they contain nothing private).
OPEN_PATHS = ("/healthz", "/login")
OPEN_PREFIXES = ("/static/",)

# Failed logins: 5 per address and 20 in total per 10 minutes.
WINDOW_SECONDS = 600
PER_ADDRESS = 5
IN_TOTAL = 20


class Gate:
    def __init__(self, password: str | None = None, clock=time.time) -> None:
        self._password = os.getenv("AGENT_PASSWORD", "") if password is None else password
        self._clock = clock
        self._key = hashlib.sha256(b"urlaubs-agent-session\0" + self._password.encode()).digest()
        self._failures: dict[str, deque[float]] = {}
        self._all: deque[float] = deque()

    @property
    def configured(self) -> bool:
        return len(self._password) >= 8

    # -- sessions --------------------------------------------------------------

    def new_session(self) -> str:
        expires = int(self._clock()) + SESSION_SECONDS
        return f"{expires}.{self._sign(str(expires))}"

    def valid_session(self, value: str | None) -> bool:
        if not self.configured or not value or "." not in value:
            return False
        expires, _, signature = value.partition(".")
        if not expires.isdigit() or int(expires) < self._clock():
            return False
        return hmac.compare_digest(signature, self._sign(expires))

    def _sign(self, message: str) -> str:
        return hmac.new(self._key, message.encode(), hashlib.sha256).hexdigest()

    # -- passwords -------------------------------------------------------------

    def check_password(self, candidate: str) -> bool:
        return self.configured and hmac.compare_digest(
            hashlib.sha256(candidate.encode()).digest(), hashlib.sha256(self._password.encode()).digest()
        )

    def locked(self, address: str) -> bool:
        now = self._clock()
        self._trim(now)
        return len(self._all) >= IN_TOTAL or len(self._failures.get(address, ())) >= PER_ADDRESS

    def record_failure(self, address: str) -> None:
        now = self._clock()
        self._trim(now)
        self._all.append(now)
        self._failures.setdefault(address, deque()).append(now)

    def _trim(self, now: float) -> None:
        horizon = now - WINDOW_SECONDS
        while self._all and self._all[0] < horizon:
            self._all.popleft()
        for address in list(self._failures):
            q = self._failures[address]
            while q and q[0] < horizon:
                q.popleft()
            if not q:
                del self._failures[address]


def client_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


LOGIN_PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Urlaubs-Agent</title><link rel="stylesheet" href="/static/style.css"></head>
<body><main style="max-width:22rem;margin:4rem auto;padding:0 1rem">
<h1>Urlaubs-Agent</h1>
{message}
<form method="post" action="/login">
<label for="password">Passwort</label>
<input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
<button type="submit">Anmelden</button>
</form></main></body></html>"""


def login_page(message: str = "", status: int = 200) -> HTMLResponse:
    note = f'<p role="alert">{escape(message)}</p>' if message else ""
    return HTMLResponse(LOGIN_PAGE.replace("{message}", note), status_code=status)


async def gate_middleware(request: Request, call_next, gate: Gate) -> Response:  # type: ignore[no-untyped-def]
    path = request.url.path
    if path in OPEN_PATHS or path.startswith(OPEN_PREFIXES):
        return await call_next(request)
    if not gate.configured:
        # Fail closed: no password configured means nobody gets in.
        return JSONResponse(
            {"detail": "Der Agent ist nicht eingerichtet (AGENT_PASSWORD fehlt)."}, status_code=503
        )
    if gate.valid_session(request.cookies.get(COOKIE)):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Bitte anmelden."}, status_code=401)
    return RedirectResponse("/login", status_code=303)
