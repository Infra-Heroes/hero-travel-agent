"""Refining a day, sharing, facts, the map's places, the checks, votes and the profile."""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from app.checks import check_plan, km_between, leg_minutes
from app.facts import FactFinder, facts_prompt
from app.schemas import DayPlan, Facts, Holiday, Profile, Weather

PLAN_BODY = {"destination": "Lissabon, Portugal", "days": 3, "start_date": "2026-12-07", "pace": "ausgewogen"}


def _plan(client) -> dict:
    res = client.post("/api/plan", json=PLAN_BODY)
    assert res.status_code == 200, res.text
    return res.json()


# ── Plan, map places and checks ───────────────────────────────────────────────


def test_plan_has_places_and_routes(harness):
    plan = _plan(harness.sign_in())
    assert all(d["places"] for d in plan["days"])
    assert {r["day"] for r in plan["routes"]} == {1, 2, 3}
    # Day 1 is 2026-12-07, a Monday, and the demo museum is closed on Mondays.
    assert any(c["day"] == 1 and "geschlossen" in c["text"] for c in plan["checks"])


def _day(n: int, places: list[dict], date_: str = "2026-12-08") -> dict:
    return {
        "day": n,
        "date": date_,
        "theme": "t",
        "morning": "m",
        "afternoon": "a",
        "evening": "e",
        "food_tip": "f",
        "bad_weather": "b",
        "logistics": "l",
        "places": places,
    }


def _p(name, slot, lat, lon, closed=()):
    return {"name": name, "slot": slot, "lat": lat, "lon": lon, "closed_on": list(closed)}


def test_checks_drop_far_places_and_warn():
    plan = DayPlan.model_validate(
        {
            "destination": "Lissabon",
            "overview": "o",
            "packing_list": [],
            "days": [
                _day(1, []),
                _day(
                    2,
                    [
                        _p("Belém", "morning", 38.697, -9.206),
                        _p("Sintra", "afternoon", 38.797, -9.390),
                        _p("Évora", "evening", 38.571, -7.909),
                        _p("Madrid", "evening", 40.416, -3.703),
                    ],
                ),
                _day(3, [], "2026-12-25"),
            ],
        }
    )
    facts = Facts(
        lat=38.722,
        lon=-9.139,
        country="PT",
        holidays=[Holiday(name="Natal", start="2026-12-25", end="2026-12-25", kind="public")],
    )
    result = check_plan(plan, facts, pace="entspannt", lang="de")
    names = [p.name for p in result.days[1].places]
    assert "Madrid" not in names and "Évora" in names
    texts = [c.text for c in result.checks]
    assert any("Viel unterwegs" in t for t in texts)
    assert any("Sintra nach Évora" in t for t in texts)
    assert any(c.level == "info" and c.day == 3 and "Natal" in c.text for c in result.checks)
    assert result.routes[0].day == 2


def test_checks_in_english_and_without_facts():
    plan = DayPlan.model_validate(
        {
            "destination": "x",
            "overview": "o",
            "packing_list": [],
            "days": [
                _day(1, []),
                _day(2, [_p("A", "morning", 0, 0, ["Di"]), _p("B", "evening", 0, 1.5)], "2026-12-08"),
                _day(3, [], "kein Datum"),
            ],
        }
    )
    result = check_plan(plan, None, pace="aktiv", lang="en")
    texts = " ".join(c.text for c in result.checks)
    assert "usually closed on Tuesdays" in texts and "From A to B" in texts
    assert result.facts is None


def test_leg_minutes_walk_or_ride():
    assert leg_minutes(1.0) < 20
    assert leg_minutes(30.0) > 60
    assert round(km_between(0, 0, 0, 1)) == 111


# ── Refining a day ────────────────────────────────────────────────────────────


def test_refine_changes_one_day_and_updates_the_saved_trip(harness):
    client = harness.sign_in()
    plan = _plan(client)
    trip = client.post("/api/trips", json={"title": "T", "kind": "plan", "payload": plan}).json()
    res = client.post(
        "/api/plan/refine", json={"plan": plan, "day": 2, "wish": "mehr Strand", "trip_id": trip["id"]}
    )
    assert res.status_code == 200, res.text
    out = res.json()
    assert "mehr Strand" in out["days"][1]["morning"]
    assert out["days"][0] == plan["days"][0]
    assert out["days"][1]["date"] == plan["days"][1]["date"]
    saved = client.get(f"/api/trips/{trip['id']}").json()["payload"]
    assert "mehr Strand" in saved["days"][1]["morning"]
    # One plan, one refine: two of the three requests of the day.
    assert client.get("/api/me").json()["used_today"] == 2


def test_refine_refuses_unknown_day_and_foreign_trip(harness):
    client = harness.sign_in()
    plan = _plan(client)
    assert client.post("/api/plan/refine", json={"plan": plan, "day": 9, "wish": "anders"}).status_code == 422
    other = harness.sign_in("bob@example.com")
    trip = other.post("/api/trips", json={"title": "B", "kind": "plan", "payload": plan}).json()
    res = client.post(
        "/api/plan/refine", json={"plan": plan, "day": 1, "wish": "anders", "trip_id": trip["id"]}
    )
    assert res.status_code == 404
    assert client.get("/api/me").json()["used_today"] == 1


# ── Sharing ───────────────────────────────────────────────────────────────────


def test_share_read_only_and_withdraw(harness):
    client = harness.sign_in()
    plan = _plan(client)
    trip = client.post("/api/trips", json={"title": "Lissabon", "kind": "plan", "payload": plan}).json()
    assert client.get(f"/api/trips/{trip['id']}").json()["share"] is None
    share = client.post(f"/api/trips/{trip['id']}/share", json={"days": 7})
    assert share.status_code == 201
    token = share.json()["token"]
    assert client.get(f"/api/trips/{trip['id']}").json()["share"]["token"] == token

    anyone = harness.client()
    page = anyone.get(f"/s/{token}")
    assert page.status_code == 200 and "noindex" in page.headers["x-robots-tag"]
    shared = anyone.get(f"/api/shared/{token}").json()
    assert shared["title"] == "Lissabon" and "user_id" not in shared and "email" not in json.dumps(shared)

    # Sharing again replaces the link.
    token2 = client.post(f"/api/trips/{trip['id']}/share", json={}).json()["token"]
    assert anyone.get(f"/api/shared/{token}").status_code == 404
    assert client.delete(f"/api/trips/{trip['id']}/share").status_code == 204
    assert anyone.get(f"/api/shared/{token2}").status_code == 404
    assert anyone.get("/api/shared/" + "x" * 80).status_code == 404


def test_share_needs_the_owner_and_expires(harness):
    client = harness.sign_in()
    trip = client.post("/api/trips", json={"title": "T", "kind": "plan", "payload": _plan(client)}).json()
    other = harness.sign_in("bob@example.com")
    assert other.post(f"/api/trips/{trip['id']}/share", json={}).status_code == 404
    assert client.post(f"/api/trips/{trip['id']}/share", json={"days": 365}).status_code == 422
    token = client.post(f"/api/trips/{trip['id']}/share", json={"days": 1}).json()["token"]
    harness.main.store._db.execute("UPDATE shares SET expires_at = '2000-01-01T00:00:00+00:00'")
    assert harness.client().get(f"/api/shared/{token}").status_code == 404
    # Deleting the trip takes the link along.
    client.post(f"/api/trips/{trip['id']}/share", json={})
    client.delete(f"/api/trips/{trip['id']}")
    assert harness.main.store._db.execute("SELECT COUNT(*) FROM shares").fetchone()[0] == 0


# ── Votes and profile ─────────────────────────────────────────────────────────


def test_votes_go_into_the_next_suggestions(harness):
    client = harness.sign_in()
    for dest, vote in (("Madeira", 1), ("Kreta", -1), ("Rom", 1), ("Rom", 0)):
        assert client.post("/api/votes", json={"destination": dest, "vote": vote}).status_code == 200
    assert client.get("/api/votes").json() == {"liked": ["Madeira"], "disliked": ["Kreta"]}
    assert client.post("/api/votes", json={"destination": "x", "vote": 2}).status_code == 422
    user_id = harness.main.store.login("anna@example.com")[0]["id"]
    context = harness.main._suggest_context(user_id)
    assert "Madeira" in context and "nicht erneut" in context and "Rom" not in context
    assert harness.main.store.vote_counts() == {1: 1, -1: 1}


def test_profile_round_trip_and_prompt(harness):
    client = harness.sign_in()
    first = client.get("/api/profile").json()
    assert first["saved"] is False and first["profile"]["adults"] == 2
    body = {
        "origin": "Köln",
        "adults": 1,
        "children": 2,
        "avoid": "lange Flüge",
        "accessibility": "Kinderwagen",
    }
    assert client.put("/api/profile", json=body).status_code == 200
    got = client.get("/api/profile").json()
    assert got["saved"] and got["profile"]["origin"] == "Köln"
    user_id = harness.main.store.login("anna@example.com")[0]["id"]
    context = harness.main._suggest_context(user_id)
    assert "lange Flüge" in context and "Kinderwagen" in context
    assert client.put("/api/profile", json={"adults": 0}).status_code == 422
    # A broken stored profile is ignored, not a 500.
    harness.main.store.set_profile(user_id, {"adults": "viele"})
    assert client.get("/api/profile").json()["profile"]["adults"] == 2


def test_profile_prompt_empty_and_full():
    assert Profile().as_prompt() == ""
    assert "Allgemein: vegetarisch" in Profile(notes="vegetarisch").as_prompt()


def test_deleting_the_account_removes_profile_votes_and_shares(harness):
    client = harness.sign_in()
    client.put("/api/profile", json={"origin": "Bonn"})
    client.post("/api/votes", json={"destination": "Malta", "vote": 1})
    trip = client.post("/api/trips", json={"title": "T", "kind": "plan", "payload": _plan(client)}).json()
    client.post(f"/api/trips/{trip['id']}/share", json={})
    assert client.delete("/api/me").status_code in (200, 204)
    db = harness.main.store._db
    for table in ("profiles", "votes", "shares"):
        assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table


# ── Facts ─────────────────────────────────────────────────────────────────────


def _facts_transport(fail: set[str] | None = None):
    fail = fail or set()

    def handler(req: httpx.Request) -> httpx.Response:
        host, path = req.url.host, req.url.path
        if any(f in host + path for f in fail):
            return httpx.Response(500)
        if "geocoding" in host:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "latitude": 10.16,
                            "longitude": -68.0,
                            "country_code": "VE",
                            "country": "Venezuela",
                            "population": 10,
                        },
                        {
                            "latitude": 39.47,
                            "longitude": -0.37,
                            "country_code": "ES",
                            "country": "Spanien",
                            "population": 800000,
                        },
                    ]
                },
            )
        if "archive" in host:
            return httpx.Response(
                200,
                json={
                    "daily": {
                        "temperature_2m_max": [20.0, 22.0],
                        "temperature_2m_min": [10.0, None],
                        "precipitation_sum": [0.0, 3.0],
                    }
                },
            )
        if path.endswith("PublicHolidays"):
            return httpx.Response(
                200,
                json=[
                    {
                        "startDate": "2027-01-06",
                        "endDate": "2027-01-06",
                        "name": [{"language": "DE", "text": "Heilige Drei Könige"}],
                        "nationwide": True,
                    },
                    {"startDate": "x", "name": []},
                ],
            )
        if path.endswith("SchoolHolidays"):
            return httpx.Response(
                200,
                json=[
                    {
                        "startDate": "2026-12-23",
                        "endDate": "2027-01-07",
                        "name": [{"language": "EN", "text": "Christmas"}],
                        "nationwide": False,
                    }
                ],
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_facts_pick_the_country_and_measure():
    finder = FactFinder(transport=_facts_transport())
    facts = await finder.for_plan("Valencia, Spanien", date(2027, 1, 5), 3, "de")
    assert facts and facts.country == "ES"
    assert facts.weather and facts.weather.temp_max_c == 21.0 and facts.weather.rainy_days_share == 0.5
    kinds = {(h.kind, h.name, h.regional) for h in facts.holidays}
    assert ("public", "Heilige Drei Könige", False) in kinds and ("school", "Christmas", True) in kinds
    text = facts_prompt(facts)
    assert "Gemessenes Wetter" in text and "Feiertag am Ziel" in text and "Schulferien (regional)" in text
    # Cached: a second lookup does not ask again.
    again = await finder.for_plan("Valencia, Spanien", date(2027, 1, 5), 3, "de")
    assert again == facts


@pytest.mark.asyncio
async def test_facts_fail_quietly():
    finder = FactFinder(transport=_facts_transport({"geocoding"}))
    assert await finder.for_plan("Valencia", date(2027, 1, 5), 3, "de") is None
    finder = FactFinder(transport=_facts_transport({"archive", "Holidays"}))
    facts = await finder.for_plan("Valencia", date(2027, 1, 5), 3, "de")
    assert facts and facts.weather is None and facts.holidays == [] and facts.country == "ES"
    assert facts_prompt(facts) == "" and facts_prompt(None) == ""
    assert await FactFinder(enabled=False).locate("x") is None
    # Without a start date only the place is known.
    plain = await FactFinder(transport=_facts_transport()).for_plan("Valencia", None, 3, "de")
    assert plain and plain.weather is None


@pytest.mark.asyncio
async def test_facts_empty_geocode_and_future_years():
    empty = httpx.MockTransport(lambda req: httpx.Response(200, json={}))
    assert await FactFinder(transport=empty).locate("Nirgendwo") is None
    # A country hint that no result matches: no place rather than the wrong one.
    assert await FactFinder(transport=_facts_transport()).locate("Valencia, Portugal") is None
    finder = FactFinder(transport=_facts_transport())
    # 29 February: past years without it take the 28th.
    assert await finder.weather(1, 1, date(2028, 2, 29), 2) is not None
    # A window that reaches into today in every past year: nothing measured yet.
    assert await finder.weather(1, 1, date(2027, 1, 1), 2000) is None
    w = Weather(years=3, temp_max_c=1, temp_min_c=0, rainy_days_share=0)
    assert "0 bis 1 °C" in facts_prompt(Facts(weather=w))
