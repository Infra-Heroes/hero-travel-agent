"""A fresh app per test: its own database, a console mailer, small limits."""

from __future__ import annotations

import importlib
import re
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient


class Harness:
    """The app plus helpers to sign people in through the real endpoints."""

    def __init__(self, monkeypatch, **env: str) -> None:
        defaults = {
            "AGENT_FAKE": "1",
            "MAIL_BACKEND": "console",
            "USER_DAILY_QUERIES": "3",
            "AGENT_DAILY_CALLS": "100",
        }
        monkeypatch.setenv("DATA_DIR", tempfile.mkdtemp())
        for key in (
            "SMTP_HOST",
            "METRICS_TOKEN",
            "ALLOWED_EMAILS",
            "ALLOWED_EMAIL_DOMAINS",
            "SESSION_SECRET",
        ):
            monkeypatch.delenv(key, raising=False)
        for key, value in {**defaults, **env}.items():
            monkeypatch.setenv(key, value)
        sys.modules.pop("app.main", None)
        self.main = importlib.import_module("app.main")

    def client(self) -> TestClient:
        return TestClient(self.main.app, follow_redirects=False)

    def last_code(self, to: str) -> str:
        for message in reversed(self.main.mailer.outbox):
            if message["To"] == to:
                match = re.search(r"Dein Code: (\d{6})", message.get_content())
                assert match, message.get_content()
                return match.group(1)
        raise AssertionError(f"no mail to {to}")

    def sign_in(self, email: str = "anna@example.com") -> TestClient:
        client = self.client()
        assert client.post("/api/auth/request", json={"email": email}).status_code == 200
        res = client.post("/api/auth/verify", json={"email": email, "code": self.last_code(email.lower())})
        assert res.status_code == 200, res.text
        return client


@pytest.fixture
def harness(monkeypatch):
    return Harness(monkeypatch)


@pytest.fixture
def make_harness(monkeypatch):
    return lambda **env: Harness(monkeypatch, **env)
