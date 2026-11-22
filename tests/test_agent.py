"""The OpenRouter client, against a simulated network: no key, no bill."""

from __future__ import annotations

import json

import httpx
import pytest

from app import agent as agent_module
from app.agent import AgentError, TravelAgent
from app.schemas import Suggestions, TripBrief

BRIEF = TripBrief(
    when="Herbstferien",
    nights=7,
    budget_eur=2500,
    adults=2,
    children=1,
    origin="Frankfurt",
    interests=["Strand"],
)


def valid_answer() -> str:
    # The demo answer is valid by construction.
    return agent_module.fake_suggestions(BRIEF).model_dump_json()


def completion(content: str, finish: str = "stop") -> dict:
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


def make_agent(monkeypatch, handler, on_call=None) -> TravelAgent:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    monkeypatch.delenv("AGENT_FAKE", raising=False)
    return TravelAgent(transport=httpx.MockTransport(handler), on_call=on_call)


async def test_without_a_key_the_agent_runs_in_demo_mode(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    a = TravelAgent()
    assert a.fake
    assert len((await a.suggest(BRIEF)).suggestions) == 3


async def test_a_call_names_the_model_the_schema_and_sends_the_key(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=completion(valid_answer()))

    result = await make_agent(monkeypatch, handler).suggest(BRIEF)
    assert isinstance(result, Suggestions)
    assert seen["auth"] == "Bearer sk-or-test-key"
    assert seen["url"].endswith("/chat/completions")
    body = seen["body"]
    assert body["model"] == "deepseek/deepseek-v4-flash"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["provider"] == {"require_parameters": True, "data_collection": "deny"}
    assert body["max_tokens"] == agent_module.MAX_TOKENS
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


async def test_an_answer_that_does_not_match_the_schema_is_asked_for_once_more(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(
            200, json=completion("Hier sind meine Ideen: ..." if len(calls) == 1 else valid_answer())
        )

    result = await make_agent(monkeypatch, handler).suggest(BRIEF)
    assert len(result.suggestions) == 3
    assert len(calls) == 2
    assert "ausschließlich mit gültigem JSON" in calls[1]["messages"][1]["content"]


async def test_two_unusable_answers_end_in_a_message_not_a_crash(monkeypatch):
    handler = lambda request: httpx.Response(200, json=completion("{not json"))
    with pytest.raises(AgentError, match="keine brauchbare Antwort"):
        await make_agent(monkeypatch, handler).suggest(BRIEF)


@pytest.mark.parametrize(
    ("status", "message"),
    [(429, "ausgelastet"), (402, "nicht bearbeiten"), (401, "nicht bearbeiten"), (500, "nicht bearbeiten")],
)
async def test_http_errors_become_a_message_for_the_person(monkeypatch, status, message):
    handler = lambda request: httpx.Response(status, json={"error": {"message": "x"}})
    with pytest.raises(AgentError, match=message):
        await make_agent(monkeypatch, handler).suggest(BRIEF)


async def test_a_network_failure_is_reported_as_unreachable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(AgentError, match="nicht erreichbar"):
        await make_agent(monkeypatch, handler).suggest(BRIEF)


async def test_a_cut_off_answer_says_the_plan_was_too_long(monkeypatch):
    handler = lambda request: httpx.Response(200, json=completion("{", "length"))
    with pytest.raises(AgentError, match="zu lang"):
        await make_agent(monkeypatch, handler).suggest(BRIEF)


async def test_the_error_text_never_carries_the_key(monkeypatch):
    handler = lambda request: httpx.Response(401, text="bad key sk-or-test-key")
    with pytest.raises(AgentError) as info:
        await make_agent(monkeypatch, handler).suggest(BRIEF)
    assert "sk-or-test-key" not in str(info.value)


async def test_the_model_call_reports_its_time_and_the_usage_openrouter_returned(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["usage"] == {"include": True}
        body = completion(valid_answer())
        body["usage"] = {"prompt_tokens": 120, "completion_tokens": 340, "cost": 0.0002}
        return httpx.Response(200, json=body)

    a = make_agent(monkeypatch, handler, on_call=lambda seconds, usage: seen.append((seconds, usage)))
    await a.suggest(BRIEF)
    assert len(seen) == 1
    seconds, usage = seen[0]
    assert seconds >= 0
    assert usage == {"prompt_tokens": 120, "completion_tokens": 340, "cost": 0.0002}


async def test_suggestions_run_without_thinking_and_plans_with_it(monkeypatch):
    efforts = []

    def handler(request: httpx.Request) -> httpx.Response:
        efforts.append(json.loads(request.content)["reasoning"])
        return httpx.Response(200, json=completion(valid_answer()))

    await make_agent(monkeypatch, handler).suggest(BRIEF)
    assert efforts[0] == {"enabled": False}


async def test_a_plan_with_the_wrong_number_of_days_is_asked_for_again(monkeypatch):
    from app.schemas import DayPlanRequest

    req = DayPlanRequest(destination="Lissabon", days=4)
    full = agent_module.fake_day_plan(req)
    short = full.model_copy(update={"days": full.days[:2]})
    answers = [short.model_dump_json(), full.model_dump_json()]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=completion(answers.pop(0)))

    result = await make_agent(monkeypatch, handler).plan_days(req)
    assert len(result.days) == 4 and not answers


async def test_refine_asks_for_one_day_and_keeps_number_and_date(monkeypatch):
    from app.schemas import DayPlanRequest, PlanResult, RefineRequest

    plan = agent_module.fake_day_plan(DayPlanRequest(destination="Lissabon", days=3))
    req = RefineRequest(plan=PlanResult.model_validate(plan.model_dump()), day=2, wish="mehr Strand")
    seen = {}
    answer = plan.days[0].model_copy(update={"day": 7, "date": "1999-01-01", "theme": "Strandtag"})

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=completion(answer.model_dump_json()))

    day = await make_agent(monkeypatch, handler).refine_day(req, "\nBitte vermeiden: Treppen")
    assert (day.day, day.date, day.theme) == (2, plan.days[1].date, "Strandtag")
    prompt = seen["body"]["messages"][1]["content"]
    assert "Ändere nur Tag 2" in prompt and "mehr Strand" in prompt and "Treppen" in prompt
    assert "places" in seen["body"]["response_format"]["json_schema"]["schema"]["properties"]


async def test_context_reaches_the_suggest_and_plan_prompts(monkeypatch):
    from app.schemas import DayPlanRequest

    prompts = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompts.append(body["messages"][1]["content"])
        if "Tagesplan" in prompts[-1]:
            req = DayPlanRequest(destination="Lissabon", days=2)
            return httpx.Response(200, json=completion(agent_module.fake_day_plan(req).model_dump_json()))
        return httpx.Response(200, json=completion(valid_answer()))

    a = make_agent(monkeypatch, handler)
    await a.suggest(BRIEF, "\nFrüher gefallen: Madeira")
    await a.plan_days(DayPlanRequest(destination="Lissabon", days=2), "\nFakten: warm")
    assert "Madeira" in prompts[0] and "Fakten: warm" in prompts[1] and "places" in prompts[1]
