"""What the person sees when something goes wrong, and that it is counted."""

from __future__ import annotations

import pytest

from app.agent import AgentError
from app.mailer import MailError

PLAN = {"destination": "Lissabon", "days": 2}


async def _fail(*_args, **_kwargs):
    raise AgentError("Der Agent ist gerade nicht erreichbar.")


@pytest.mark.parametrize(
    ("method", "path", "body"), [("suggest", "/api/suggest", None), ("plan_days", "/api/plan", PLAN)]
)
def test_a_model_failure_is_a_503_with_a_readable_message(harness, monkeypatch, method, path, body):
    client = harness.sign_in()
    monkeypatch.setattr(harness.main.agent, method, _fail)
    body = body or {
        "when": "Mai",
        "nights": 3,
        "budget_eur": 900,
        "adults": 2,
        "origin": "Köln",
    }
    res = client.post(path, json=body)
    assert res.status_code == 503
    assert "nicht erreichbar" in res.json()["detail"]
    kind = "suggest" if method == "suggest" else "plan"
    assert harness.main.metrics.queries.labels(kind, "error")._value.get() == 1


def test_a_failed_refine_leaves_the_saved_trip_alone(harness, monkeypatch):
    client = harness.sign_in()
    plan = client.post("/api/plan", json=PLAN).json()
    trip = client.post("/api/trips", json={"title": "T", "kind": "plan", "payload": plan}).json()
    monkeypatch.setattr(harness.main.agent, "refine_day", _fail)
    res = client.post(
        "/api/plan/refine", json={"plan": plan, "day": 1, "wish": "anders", "trip_id": trip["id"]}
    )
    assert res.status_code == 503
    assert client.get(f"/api/trips/{trip['id']}").json()["payload"] == plan


def test_the_calendar_skips_days_without_a_date(harness):
    client = harness.sign_in()
    plan = client.post("/api/plan", json=PLAN).json()
    plan["days"][0]["date"] = "offen"
    trip = client.post("/api/trips", json={"title": "T", "kind": "plan", "payload": plan}).json()
    ics = client.get(f"/api/trips/{trip['id']}/calendar.ics").text
    assert ics.count("BEGIN:VEVENT") == 1


def test_sending_the_report_now(make_harness, monkeypatch):
    harness = make_harness(METRICS_TOKEN="op-token")
    operator = {"Authorization": "Bearer op-token"}
    client = harness.client()
    monkeypatch.delenv("REPORT_TO", raising=False)
    assert client.post("/api/report/send", headers=operator).status_code == 409

    monkeypatch.setenv("REPORT_TO", "ops@example.org")
    assert client.post("/api/report/send", headers=operator).json() == {"sent": True}

    async def broken(*_args, **_kwargs):
        raise MailError("down")

    monkeypatch.setattr(harness.main.mailer, "send", broken)
    assert client.post("/api/report/send", headers=operator).status_code == 502
