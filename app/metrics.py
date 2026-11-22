"""Prometheus metrics: what the agent is used for, by how many, and what it costs.

Counters and the latency histogram are kept by the process. The numbers that must
survive a restart (users, users active today, queries today) are read from the database
whenever Prometheus scrapes, so they are always right and "users per day" is the
same figure here as in the table it is stored in.
"""

from __future__ import annotations

from collections.abc import Iterator

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily

from app.store import Store, today

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class DatabaseNumbers:
    """Gauges computed from the database at scrape time."""

    def __init__(self, store: Store, user_limit: int, global_limit: int) -> None:
        self.store, self.user_limit, self.global_limit = store, user_limit, global_limit

    def collect(self) -> Iterator[GaugeMetricFamily]:
        day = today()
        stats = {row["day"]: row for row in self.store.stats(days=2)}
        row = stats.get(day, {"active_users": 0, "new_users": 0, "calls": 0})

        def gauge(name: str, doc: str, value: float) -> GaugeMetricFamily:
            g = GaugeMetricFamily(name, doc)
            g.add_metric([], value)
            return g

        yield gauge("travel_agent_users", "Registered users.", self.store.user_count())
        yield gauge("travel_agent_active_users_today", "Users active today (UTC).", row["active_users"])
        yield gauge("travel_agent_new_users_today", "Users who signed up today (UTC).", row["new_users"])
        yield gauge("travel_agent_model_calls_today", "Model calls today, all users (UTC).", row["calls"])
        yield gauge(
            "travel_agent_model_calls_limit", "Model calls allowed per day, all users.", self.global_limit
        )
        yield gauge("travel_agent_user_calls_limit", "Model calls allowed per user and day.", self.user_limit)


class Metrics:
    def __init__(self, store: Store, user_limit: int, global_limit: int) -> None:
        self.registry = CollectorRegistry()
        self.registry.register(DatabaseNumbers(store, user_limit, global_limit))
        self.queries = Counter(
            "travel_agent_queries_total",
            "Trip requests by kind and result (ok, error, limited_user, limited_global).",
            ["kind", "result"],
            registry=self.registry,
        )
        self.model_seconds = Histogram(
            "travel_agent_model_seconds",
            "Time spent waiting for the model.",
            buckets=(1, 2, 5, 10, 20, 40, 80, 160),
            registry=self.registry,
        )
        self.tokens = Counter(
            "travel_agent_model_tokens_total", "Tokens used, by type.", ["type"], registry=self.registry
        )
        self.cost = Counter(
            "travel_agent_model_cost_dollars_total",
            "Model cost as reported by OpenRouter.",
            registry=self.registry,
        )
        self.code_requests = Counter(
            "travel_agent_code_requests_total",
            "One-time codes asked for (sent, limited, not_allowed, invalid, mail_failed).",
            ["result"],
            registry=self.registry,
        )
        self.logins = Counter(
            "travel_agent_logins_total",
            "Code entries by result (ok, wrong, expired, none, limited).",
            ["result"],
            registry=self.registry,
        )
        self.signups = Counter("travel_agent_signups_total", "New users.", registry=self.registry)
        self.votes = Counter(
            "travel_agent_votes_total", "Thumbs on suggested destinations.", ["vote"], registry=self.registry
        )

    def render(self) -> bytes:
        return generate_latest(self.registry)
