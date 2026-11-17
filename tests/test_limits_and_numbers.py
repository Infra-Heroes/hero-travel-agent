"""Requests per person and per day, users per day, and the Prometheus numbers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.store import Store

BRIEF = {
    "when": "Mai",
    "nights": 5,
    "budget_eur": 1500,
    "adults": 2,
    "origin": "Berlin",
}


def metric(harness, line: str) -> float:
    for row in harness.main.metrics.render().decode().splitlines():
        if row.startswith(line + " "):
            return float(row.split()[-1])
    raise AssertionError(f"no metric {line!r}")


# -- per person ----------------------------------------------------------------------


def test_a_person_has_a_daily_number_of_requests(harness):
    c = harness.sign_in()
    assert c.get("/api/me").json() | {} == {
        "email": "anna@example.com",
        "used_today": 0,
        "limit": 3,
        "remaining": 3,
    }
    assert [c.post("/api/suggest", json=BRIEF).status_code for _ in range(3)] == [200, 200, 200]
    res = c.post("/api/plan", json={"destination": "Rom", "days": 2})
    assert res.status_code == 429
    assert "3 Anfragen" in res.json()["detail"]
    assert c.get("/api/me").json()["remaining"] == 0


def test_the_limit_is_per_person(harness):
    anna, ben = harness.sign_in("anna@example.com"), harness.sign_in("ben@example.com")
    for _ in range(3):
        anna.post("/api/suggest", json=BRIEF)
    assert anna.post("/api/suggest", json=BRIEF).status_code == 429
    assert ben.post("/api/suggest", json=BRIEF).status_code == 200


def test_a_refused_request_is_not_counted_against_the_person(harness):
    c = harness.sign_in()
    assert c.post("/api/suggest", json={**BRIEF, "nights": 0}).status_code == 422
    assert c.get("/api/me").json()["used_today"] == 0


# -- for everybody ---------------------------------------------------------------------


def test_the_whole_agent_has_a_daily_ceiling_too(make_harness):
    h = make_harness(AGENT_DAILY_CALLS="2", USER_DAILY_QUERIES="10")
    anna, ben = h.sign_in("anna@example.com"), h.sign_in("ben@example.com")
    assert anna.post("/api/suggest", json=BRIEF).status_code == 200
    assert ben.post("/api/suggest", json=BRIEF).status_code == 200
    res = anna.post("/api/suggest", json=BRIEF)
    assert res.status_code == 503 and "ausgelastet" in res.json()["detail"]
    assert anna.get("/api/me").json()["used_today"] == 1, "the refused request did not use the person's day"


def test_a_day_starts_at_zero(tmp_path):
    store = Store(tmp_path / "t.db")
    user, _ = store.login("anna@example.com")
    assert [store.try_spend(user["id"], 2, 100, "2026-11-17") for _ in range(3)] == ["ok", "ok", "user"]
    assert store.try_spend(user["id"], 2, 100, "2026-11-18") == "ok"
    assert store.calls_today(user["id"], "2026-11-17") == 2
    assert store.calls_today(None, "2026-11-17") == 2, "a refused request gives the agent-wide call back"


# -- users per day ---------------------------------------------------------------------


def test_users_per_day_are_stored(harness):
    harness.sign_in("anna@example.com")
    harness.sign_in("ben@example.com")
    harness.sign_in("anna@example.com")  # the same person signing in again is one user that day
    rows = harness.main.store.stats(days=7)
    today = datetime.now(UTC).date().isoformat()
    assert rows[0]["day"] == today
    assert rows[0]["active_users"] == 2
    assert rows[0]["new_users"] == 2


def test_a_returning_user_is_active_but_not_new(tmp_path):
    store = Store(tmp_path / "t.db")
    user, created = store.login("anna@example.com")
    assert created
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    store._db.execute("UPDATE users SET created_at = ?", (yesterday + "T10:00:00",))
    store._db.execute("DELETE FROM activity")
    store._db.execute("INSERT INTO activity (day, user_id) VALUES (?, ?)", (yesterday, user["id"]))
    store._db.commit()
    _, created_again = store.login("anna@example.com")
    assert not created_again
    by_day = {r["day"]: r for r in store.stats(days=3)}
    today = datetime.now(UTC).date().isoformat()
    assert by_day[yesterday]["new_users"] == 1 and by_day[yesterday]["active_users"] == 1
    assert by_day[today]["new_users"] == 0 and by_day[today]["active_users"] == 1


def test_using_the_agent_marks_the_user_active(tmp_path):
    store = Store(tmp_path / "t.db")
    user, _ = store.login("anna@example.com")
    store._db.execute("DELETE FROM activity")
    store._db.commit()
    store.try_spend(user["id"], 5, 100, "2026-11-17")
    assert store._db.execute("SELECT COUNT(*) FROM activity WHERE day = '2026-11-17'").fetchone()[0] == 1


def test_the_statistics_are_for_the_operator_only(make_harness):
    h = make_harness(METRICS_TOKEN="operator-token-1234")
    c = h.client()
    assert c.get("/api/stats").status_code == 401
    assert c.get("/api/stats", headers={"authorization": "Bearer wrong"}).status_code == 401
    h.sign_in()
    ok = c.get("/api/stats", headers={"authorization": "Bearer operator-token-1234"})
    assert ok.status_code == 200 and ok.json()["users"] == 1 and ok.json()["days"][0]["active_users"] == 1


# -- metrics -----------------------------------------------------------------------------


def test_metrics_are_closed_to_the_outside_without_a_token(harness):
    # The test client does not come from loopback.
    assert harness.client().get("/metrics").status_code == 403


def test_metrics_with_a_token(make_harness):
    h = make_harness(METRICS_TOKEN="operator-token-1234")
    c = h.client()
    assert c.get("/metrics").status_code == 401
    res = c.get("/metrics", headers={"authorization": "Bearer operator-token-1234"})
    assert res.status_code == 200 and "travel_agent_users" in res.text


def test_the_numbers_follow_what_happens(make_harness):
    h = make_harness()
    anna = h.sign_in("anna@example.com")
    h.sign_in("ben@example.com")
    anna.post("/api/suggest", json=BRIEF)
    anna.post("/api/plan", json={"destination": "Rom", "days": 2})
    anna.post("/api/suggest", json=BRIEF)
    anna.post("/api/suggest", json=BRIEF)  # the fourth is over the limit of three

    assert metric(h, "travel_agent_users") == 2
    assert metric(h, "travel_agent_active_users_today") == 2
    assert metric(h, "travel_agent_new_users_today") == 2
    assert metric(h, "travel_agent_model_calls_today") == 3
    assert metric(h, "travel_agent_user_calls_limit") == 3
    assert metric(h, "travel_agent_signups_total") == 2
    assert metric(h, 'travel_agent_queries_total{kind="suggest",result="ok"}') == 2
    assert metric(h, 'travel_agent_queries_total{kind="plan",result="ok"}') == 1
    assert metric(h, 'travel_agent_queries_total{kind="suggest",result="limited_user"}') == 1
    assert metric(h, 'travel_agent_code_requests_total{result="sent"}') == 2
    assert metric(h, 'travel_agent_logins_total{result="ok"}') == 2


def test_a_wrong_code_is_counted(make_harness):
    h = make_harness()
    c = h.client()
    c.post("/api/auth/request", json={"email": "anna@example.com"})
    code = h.last_code("anna@example.com")
    c.post(
        "/api/auth/verify",
        json={"email": "anna@example.com", "code": "000000" if code != "000000" else "111111"},
    )
    assert metric(h, 'travel_agent_logins_total{result="wrong"}') == 1


def test_no_metric_carries_an_address_or_a_code(make_harness):
    h = make_harness()
    h.sign_in("anna@example.com")
    text = h.main.metrics.render().decode()
    assert "anna" not in text and "example.com" not in text
