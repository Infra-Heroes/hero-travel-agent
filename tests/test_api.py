"""The agent's API, in demo mode (no network, no API key)."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["AGENT_FAKE"] = "1"
os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.modules.pop("app.main", None)
main = importlib.import_module("app.main")

from app.agent import _schema
from app.schemas import DayPlan, Suggestions

BRIEF = {
    "when": "Herbstferien",
    "nights": 7,
    "budget_eur": 2500,
    "adults": 2,
    "children": 1,
    "origin": "Frankfurt",
    "interests": ["Strand", "Natur"],
}


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_reports_demo_mode(client):
    assert client.get("/healthz").json() == {"status": "ok", "demo": True}


def test_three_suggestions_with_a_cost_breakdown(client):
    data = client.post("/api/suggest", json=BRIEF).json()
    assert len(data["suggestions"]) == 3
    for s in data["suggestions"]:
        assert s["total_estimate_eur"] == sum(c["eur"] for c in s["cost_estimate"])
        assert s["highlights"]


@pytest.mark.parametrize(
    "field,value", [("nights", 0), ("budget_eur", 10), ("adults", 0), ("when", ""), ("notes", "x" * 1001)]
)
def test_a_bad_brief_is_refused_before_the_agent_runs(client, field, value):
    assert client.post("/api/suggest", json={**BRIEF, field: value}).status_code == 422


def test_a_day_plan_has_one_entry_per_day_with_dates(client):
    plan = client.post(
        "/api/plan", json={"destination": "Lissabon", "days": 4, "start_date": "2026-10-10"}
    ).json()
    assert [d["day"] for d in plan["days"]] == [1, 2, 3, 4]
    assert plan["days"][0]["date"] == "2026-10-10"
    assert plan["days"][-1]["date"] == "2026-10-13"
    assert plan["packing_list"]


def test_day_plans_are_capped_at_two_weeks(client):
    assert client.post("/api/plan", json={"destination": "Rom", "days": 15}).status_code == 422


def test_save_open_export_and_delete_a_plan(client):
    plan = client.post(
        "/api/plan", json={"destination": "Lissabon", "days": 2, "start_date": "2026-10-10"}
    ).json()
    trip = client.post("/api/trips", json={"title": "Lissabon", "kind": "plan", "payload": plan})
    assert trip.status_code == 201
    trip_id = trip.json()["id"]

    assert any(t["id"] == trip_id for t in client.get("/api/trips").json()["trips"])
    assert client.get(f"/api/trips/{trip_id}").json()["payload"] == plan

    ics = client.get(f"/api/trips/{trip_id}/calendar.ics")
    assert ics.headers["content-type"].startswith("text/calendar")
    assert ics.text.count("BEGIN:VEVENT") == 2
    assert "DTSTART;VALUE=DATE:20261010" in ics.text

    assert client.delete(f"/api/trips/{trip_id}").status_code == 204
    assert client.get(f"/api/trips/{trip_id}").status_code == 404


def test_only_well_formed_payloads_are_saved(client):
    r = client.post("/api/trips", json={"title": "x", "kind": "plan", "payload": {"nope": 1}})
    assert r.status_code == 422


def test_the_page_and_security_headers(client):
    r = client.get("/")
    assert "Urlaubs-Agent" in r.text
    assert r.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in r.headers["content-security-policy"]


def test_schemas_sent_to_claude_are_closed_and_fully_required():
    """Structured output needs every object closed and every field required."""
    for model in (Suggestions, DayPlan):

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    assert node["additionalProperties"] is False
                    assert set(node["required"]) == set(node["properties"])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        schema = _schema(model)
        assert "$ref" not in str(schema)
        walk(schema)
