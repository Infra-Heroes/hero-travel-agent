"""The password gate: closed unless configured, sessions, and slow guessing."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.auth import PER_ADDRESS, Gate

FORM = {"content-type": "application/x-www-form-urlencoded"}


def load_app(password: str | None):
    os.environ["AGENT_FAKE"] = "1"
    os.environ["DATA_DIR"] = tempfile.mkdtemp()
    if password is None:
        os.environ.pop("AGENT_PASSWORD", None)
    else:
        os.environ["AGENT_PASSWORD"] = password
    sys.modules.pop("app.main", None)
    return importlib.import_module("app.main")


@pytest.fixture
def secured():
    main = load_app("a-good-password")
    return TestClient(main.app, follow_redirects=False)


def test_without_a_password_configured_nothing_is_served_but_the_health_check():
    main = load_app(None)
    c = TestClient(main.app, follow_redirects=False)
    assert c.get("/healthz").json()["auth"] is False
    for path in ("/", "/api/trips"):
        assert c.get(path).status_code == 503, path
    assert c.post("/login", content="password=anything", headers=FORM).status_code == 503


def test_a_password_that_is_too_short_counts_as_not_configured():
    main = load_app("short")
    c = TestClient(main.app, follow_redirects=False)
    assert c.get("/api/trips").status_code == 503


def test_without_a_session_the_page_redirects_and_the_api_says_401(secured):
    assert secured.get("/").status_code == 303
    assert secured.get("/").headers["location"] == "/login"
    assert secured.get("/api/trips").status_code == 401
    assert secured.post("/api/suggest", json={}).status_code == 401
    assert secured.delete("/api/trips/abc").status_code == 401


def test_the_login_page_and_static_files_are_open(secured):
    assert secured.get("/login").status_code == 200
    assert "Passwort" in secured.get("/login").text
    assert secured.get("/static/style.css").status_code == 200
    assert secured.get("/healthz").status_code == 200


def test_a_wrong_password_is_refused_and_a_right_one_opens_everything(secured):
    assert secured.post("/login", content="password=nope", headers=FORM).status_code == 401
    assert "agent_session" not in secured.cookies
    res = secured.post("/login", content="password=a-good-password", headers=FORM)
    assert res.status_code == 303
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert secured.get("/api/trips").status_code == 200
    assert secured.get("/").status_code == 200


def test_the_secure_flag_follows_https(secured):
    res = secured.post(
        "/login", content="password=a-good-password", headers={**FORM, "x-forwarded-proto": "https"}
    )
    assert "secure" in res.headers["set-cookie"].lower()


def test_logout_ends_the_session(secured):
    secured.post("/login", content="password=a-good-password", headers=FORM)
    assert secured.get("/api/trips").status_code == 200
    assert secured.post("/logout").status_code == 303
    secured.cookies.clear()
    assert secured.get("/api/trips").status_code == 401


def test_a_forged_or_expired_cookie_does_not_open_anything(secured):
    for value in ("garbage", "9999999999.deadbeef", "1.00", ""):
        secured.cookies.set("agent_session", value)
        assert secured.get("/api/trips").status_code == 401, value


def test_guessing_is_limited_per_address(secured):
    for _ in range(PER_ADDRESS):
        assert secured.post("/login", content="password=wrong", headers=FORM).status_code == 401
    res = secured.post("/login", content="password=a-good-password", headers=FORM)
    assert res.status_code == 429, "even the right password waits once an address is locked"


# -- Gate on its own: time -------------------------------------------------------


def test_sessions_expire_and_a_changed_password_invalidates_them():
    now = [1000.0]
    gate = Gate("first-password", clock=lambda: now[0])
    session = gate.new_session()
    assert gate.valid_session(session)
    assert not Gate("second-password", clock=lambda: now[0]).valid_session(session)
    now[0] += 15 * 24 * 3600
    assert not gate.valid_session(session)


def test_the_lock_lifts_after_the_window_and_the_total_limit_covers_many_addresses():
    now = [0.0]
    gate = Gate("a-good-password", clock=lambda: now[0])
    for i in range(20):
        gate.record_failure(f"10.0.0.{i}")
    assert gate.locked("10.9.9.9"), "20 failures from many addresses lock everybody"
    now[0] += 601
    assert not gate.locked("10.9.9.9")
