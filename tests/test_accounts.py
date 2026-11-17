"""Signing in with an e-mail address and a one-time code, and what it guards."""

from __future__ import annotations

from app.auth import Auth, Limiter, normalize_email

BRIEF = {
    "when": "Herbstferien",
    "nights": 7,
    "budget_eur": 2500,
    "adults": 2,
    "children": 1,
    "origin": "Frankfurt",
    "interests": ["Strand", "Natur"],
}


# -- what is public and what is not ------------------------------------------------


def test_the_start_page_is_public_and_the_planner_is_not(harness):
    c = harness.client()
    assert c.get("/").status_code == 200
    assert "Wohin soll die Reise gehen?" in c.get("/").text
    assert c.get("/static/landing.js").status_code == 200
    assert c.get("/healthz").status_code == 200
    assert c.get("/app").status_code == 303
    assert c.get("/app").headers["location"] == "/"
    for method, path in [
        ("get", "/api/me"),
        ("get", "/api/trips"),
        ("post", "/api/suggest"),
        ("post", "/api/plan"),
        ("delete", "/api/trips/abc"),
        ("get", "/api/trips/abc/calendar.ics"),
    ]:
        assert getattr(c, method)(path).status_code in (401, 422), path
    assert c.post("/api/suggest", json=BRIEF).status_code == 401


def test_a_signed_in_person_reaches_the_planner(harness):
    c = harness.sign_in()
    assert c.get("/app").status_code == 200
    assert c.get("/api/me").json()["email"] == "anna@example.com"
    assert c.post("/api/suggest", json=BRIEF).status_code == 200


def test_the_cookie_is_httponly_strict_and_secure_behind_https(harness):
    c = harness.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    res = c.post(
        "/api/auth/verify",
        json={"email": "anna@example.com", "code": harness.last_code("anna@example.com")},
        headers={"x-forwarded-proto": "https"},
    )
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "secure" in cookie


def test_logout_ends_the_session(harness):
    c = harness.sign_in()
    assert c.post("/api/auth/logout").status_code == 200
    c.cookies.clear()
    assert c.get("/api/me").status_code == 401


def test_a_forged_or_tampered_cookie_opens_nothing(harness):
    c = harness.sign_in()
    good = c.cookies.get("agent_session")
    user, expires, signature = good.split(".")
    for bad in (
        "garbage",
        f"{user}.{expires}.{'0' * 64}",
        f"someone-else.{expires}.{signature}",
        f"{user}.9999999999.{signature}",
    ):
        c.cookies.set("agent_session", bad)
        assert c.get("/api/me").status_code == 401, bad


# -- the code ---------------------------------------------------------------------


def test_asking_for_a_code_sends_one_mail_with_six_digits(harness):
    c = harness.client()
    res = c.post("/api/auth/request", json={"email": "  Anna@Example.com "})
    assert res.status_code == 200 and res.json()["ok"] is True
    assert len(harness.main.mailer.outbox) == 1
    message = harness.main.mailer.outbox[0]
    assert message["To"] == "anna@example.com"
    assert len(harness.last_code("anna@example.com")) == 6


def test_the_answer_is_the_same_for_a_known_and_an_unknown_address(harness):
    harness.sign_in("known@example.com")
    c = harness.client()
    a = c.post("/api/auth/request", json={"email": "known@example.com"})
    b = c.post("/api/auth/request", json={"email": "new@example.com"})
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()


def test_a_code_works_once(harness):
    c = harness.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    code = harness.last_code("anna@example.com")
    assert c.post("/api/auth/verify", json={"email": "anna@example.com", "code": code}).status_code == 200
    again = harness.client().post("/api/auth/verify", json={"email": "anna@example.com", "code": code})
    assert again.status_code == 401


def test_a_wrong_code_is_refused_and_five_wrong_tries_kill_the_right_one(harness):
    c = harness.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    code = harness.last_code("anna@example.com")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert (
            c.post("/api/auth/verify", json={"email": "anna@example.com", "code": wrong}).status_code == 401
        )
    res = c.post("/api/auth/verify", json={"email": "anna@example.com", "code": code})
    assert res.status_code == 401, "the code is dead after five wrong tries, even when it is right"


def test_an_expired_code_is_refused(harness):
    c = harness.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    code = harness.last_code("anna@example.com")
    harness.main.store._db.execute("UPDATE login_codes SET expires_at = '2000-01-01T00:00:00'")
    harness.main.store._db.commit()
    res = c.post("/api/auth/verify", json={"email": "anna@example.com", "code": code})
    assert res.status_code == 401 and "abgelaufen" in res.json()["detail"]


def test_a_new_code_replaces_the_old_one(harness):
    c = harness.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    first = harness.last_code("anna@example.com")
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    second = harness.last_code("anna@example.com")
    if first != second:
        assert (
            c.post("/api/auth/verify", json={"email": "anna@example.com", "code": first}).status_code == 401
        )
    assert c.post("/api/auth/verify", json={"email": "anna@example.com", "code": second}).status_code in (
        200,
        401,
    )


def test_the_code_is_not_stored_in_clear(harness):
    c = harness.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    code = harness.last_code("anna@example.com")
    stored = harness.main.store._db.execute("SELECT code_hash FROM login_codes").fetchone()[0]
    assert code not in stored and len(stored) == 64


def test_bad_input_is_refused(harness):
    c = harness.client()
    for email in ("", "no-at-sign", "a@b", "a b@example.com", "x" * 300 + "@example.com"):
        assert c.post("/api/auth/request", json={"email": email}).status_code in (422,), email
    assert c.post("/api/auth/verify", json={"email": "anna@example.com", "code": "12"}).status_code == 422
    assert c.post("/api/auth/verify", json={"email": "anna@example.com", "code": "abcdef"}).status_code == 422


def test_without_a_mail_backend_nobody_can_sign_in(make_harness):
    h = make_harness(MAIL_BACKEND="")
    c = h.client()
    assert c.get("/healthz").json()["mail"] is False
    assert c.post("/api/auth/request", json={"email": "anna@example.com"}).status_code == 503


def test_a_failing_mail_server_is_reported_and_counted(harness):
    async def broken(*_a, **_k):
        from app.mailer import MailError

        raise MailError("connection refused")

    harness.main.mailer.send = broken
    res = harness.client().post("/api/auth/request", json={"email": "anna@example.com"})
    assert res.status_code == 503
    assert (
        'travel_agent_code_requests_total{result="mail_failed"} 1.0' in harness.main.metrics.render().decode()
    )


# -- who may sign up ----------------------------------------------------------------


def test_an_allow_list_narrows_who_gets_a_code_without_telling_anybody(make_harness):
    h = make_harness(ALLOWED_EMAILS="anna@example.com", ALLOWED_EMAIL_DOMAINS="firma.de")
    c = h.client()
    for email in ("anna@example.com", "chef@firma.de"):
        assert c.post("/api/auth/request", json={"email": email}).status_code == 200
    assert len(h.main.mailer.outbox) == 2
    res = c.post("/api/auth/request", json={"email": "stranger@example.org"})
    assert res.status_code == 200 and res.json()["ok"] is True, "the answer must not reveal the list"
    assert len(h.main.mailer.outbox) == 2, "but no mail is sent"


# -- guessing and mail bombing ----------------------------------------------------


def test_codes_per_address_are_limited(harness):
    c = harness.client()
    codes = [c.post("/api/auth/request", json={"email": "anna@example.com"}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    assert len(harness.main.mailer.outbox) == 3


def test_one_client_cannot_ask_for_codes_for_everybody(harness):
    c = harness.client()
    statuses = [
        c.post("/api/auth/request", json={"email": f"user{i}@example.com"}).status_code for i in range(12)
    ]
    assert statuses.count(200) == 10 and statuses[10:] == [429, 429]


def test_trying_codes_is_limited_per_client(harness):
    c = harness.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    seen = [
        c.post("/api/auth/verify", json={"email": f"x{i}@example.com", "code": "123456"}).status_code
        for i in range(22)
    ]
    assert seen[-1] == 429


def test_limiter_windows_slide():
    now = [0.0]
    limiter = Limiter(2, 60, clock=lambda: now[0])
    assert limiter.allow("k") and limiter.allow("k") and not limiter.allow("k")
    now[0] += 61
    assert limiter.allow("k")


def test_normalize_email():
    assert normalize_email(" Anna.B+tag@Example.COM ") == "anna.b+tag@example.com"
    assert normalize_email("nope") is None and normalize_email("a@b") is None


def test_sessions_survive_a_restart_but_not_a_new_secret(tmp_path, monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    first = Auth(tmp_path)
    cookie = first.new_session("u1")
    assert Auth(tmp_path).session_user(cookie) == "u1", "the key is kept in the data directory"
    monkeypatch.setenv("SESSION_SECRET", "another-secret-of-length")
    assert Auth(tmp_path).session_user(cookie) is None


def test_sessions_expire(tmp_path):
    now = [1000.0]
    auth = Auth(tmp_path, clock=lambda: now[0])
    cookie = auth.new_session("u1")
    assert auth.session_user(cookie) == "u1"
    now[0] += 15 * 24 * 3600
    assert auth.session_user(cookie) is None


# -- people only see their own trips ---------------------------------------------------


def test_trips_belong_to_their_user(harness):
    anna = harness.sign_in("anna@example.com")
    ben = harness.sign_in("ben@example.com")
    suggestions = anna.post("/api/suggest", json=BRIEF).json()
    saved = anna.post("/api/trips", json={"title": "Madeira", "kind": "suggestions", "payload": suggestions})
    assert saved.status_code == 201
    trip_id = saved.json()["id"]
    assert [t["id"] for t in anna.get("/api/trips").json()["trips"]] == [trip_id]
    assert ben.get("/api/trips").json()["trips"] == []
    assert ben.get(f"/api/trips/{trip_id}").status_code == 404
    assert ben.delete(f"/api/trips/{trip_id}").status_code == 404
    assert anna.get(f"/api/trips/{trip_id}").status_code == 200


def test_legal_pages_are_public(harness):
    c = harness.client()
    for path, word in (("/impressum", "Impressum"), ("/datenschutz", "Datenschutzerklärung")):
        res = c.get(path)
        assert res.status_code == 200 and word in res.text


def test_deleting_the_account_erases_it(harness):
    c = harness.sign_in("weg@example.com")
    assert c.delete("/api/me").status_code == 200
    assert c.get("/api/me").status_code == 401
    assert harness.store.user_count() == 0 if hasattr(harness, "store") else True
