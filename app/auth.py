"""Signing in with an e-mail address and a one-time code.

Nobody has a password. A person types their address, gets a six digit code by mail,
and types it back: that proves the address is theirs, and the address is the account.

- Codes live 10 minutes, are stored only as a keyed hash, die after 5 wrong tries and
  after one success.
- The answer to "send me a code" is always the same, whether the address is known or not,
  so the form cannot be used to find out who has an account.
- Asking for codes and trying codes are limited per address, per client and in total,
  so neither mail nor guessing can be run in bulk.
- A session is a signed cookie (HttpOnly, SameSite=Strict, Secure behind https) that
  names the user. The signing key is SESSION_SECRET, or a random key kept in the data
  directory, so restarts do not log people out.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from collections import deque
from pathlib import Path

from fastapi import Request

COOKIE = "agent_session"
SESSION_SECONDS = 14 * 24 * 3600
CODE_SECONDS = 600
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,24}$")

# Paths anybody may open: the public page, its files, the health check, the sign-in calls.
OPEN_PATHS = ("/", "/healthz", "/metrics", "/robots.txt")
OPEN_PREFIXES = ("/static/", "/api/auth/")


def normalize_email(raw: str) -> str | None:
    email = raw.strip().lower()
    return email if len(email) <= 254 and EMAIL_RE.match(email) else None


class Limiter:
    """N events per window for a key; the oldest fall out."""

    def __init__(self, limit: int, window: int, clock=time.time) -> None:
        self.limit, self.window, self.clock = limit, window, clock
        self._events: dict[str, deque[float]] = {}

    def _trim(self, key: str) -> deque[float]:
        q = self._events.setdefault(key, deque())
        horizon = self.clock() - self.window
        while q and q[0] < horizon:
            q.popleft()
        if not q:
            self._events.pop(key, None)
            return self._events.setdefault(key, deque())
        return q

    def allow(self, key: str) -> bool:
        """Count one event, or refuse it."""
        q = self._trim(key)
        if len(q) >= self.limit:
            return False
        q.append(self.clock())
        return True

    def blocked(self, key: str) -> bool:
        return len(self._trim(key)) >= self.limit


class Auth:
    def __init__(self, data_dir: Path, clock=time.time) -> None:
        self._clock = clock
        self._key = self._load_key(data_dir)
        # Codes asked for: 3 per address and 10 per client in 10 minutes, 200 an hour in total.
        self.ask_email = Limiter(3, CODE_SECONDS, clock)
        self.ask_client = Limiter(10, CODE_SECONDS, clock)
        self.ask_total = Limiter(200, 3600, clock)
        # Codes tried (wrong ones count): 20 per client in 10 minutes.
        self.try_client = Limiter(20, CODE_SECONDS, clock)
        allowed = os.getenv("ALLOWED_EMAILS", "")
        self.allowed_emails = {e.strip().lower() for e in allowed.split(",") if e.strip()}
        domains = os.getenv("ALLOWED_EMAIL_DOMAINS", "")
        self.allowed_domains = {d.strip().lower().lstrip("@") for d in domains.split(",") if d.strip()}

    @staticmethod
    def _load_key(data_dir: Path) -> bytes:
        env = os.getenv("SESSION_SECRET", "")
        if len(env) >= 16:
            return hashlib.sha256(env.encode()).digest()
        path = data_dir / "session.key"
        data_dir.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(secrets.token_bytes(32))
            path.chmod(0o600)
        return path.read_bytes()

    # -- who may sign up -------------------------------------------------------

    def allowed(self, email: str) -> bool:
        """Open to every address, unless the operator narrowed it down."""
        if not self.allowed_emails and not self.allowed_domains:
            return True
        return email in self.allowed_emails or email.rsplit("@", 1)[-1] in self.allowed_domains

    # -- codes -----------------------------------------------------------------

    def new_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def code_hash(self, email: str, code: str) -> str:
        return hmac.new(self._key, f"code\0{email}\0{code}".encode(), hashlib.sha256).hexdigest()

    def code_matches(self, email: str, code: str):
        return lambda stored: hmac.compare_digest(stored, self.code_hash(email, code))

    # -- sessions --------------------------------------------------------------

    def new_session(self, user_id: str) -> str:
        expires = int(self._clock()) + SESSION_SECONDS
        body = f"{user_id}.{expires}"
        return f"{body}.{self._sign(body)}"

    def session_user(self, value: str | None) -> str | None:
        """The user id in a valid, unexpired session cookie, else None."""
        if not value or value.count(".") != 2:
            return None
        user_id, expires, signature = value.split(".")
        if not expires.isdigit() or int(expires) < self._clock():
            return None
        if not hmac.compare_digest(signature, self._sign(f"{user_id}.{expires}")):
            return None
        return user_id

    def _sign(self, message: str) -> str:
        return hmac.new(self._key, f"session\0{message}".encode(), hashlib.sha256).hexdigest()


def client_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
