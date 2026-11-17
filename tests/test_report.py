"""The daily report: numbers only, sent once a day."""

from __future__ import annotations

from app.report import build_report, render


def test_the_report_counts_users_signups_and_calls(harness):
    store = harness.main.store
    client = harness.sign_in("a@example.com")
    harness.sign_in("b@example.com")
    assert client.get("/api/me").status_code == 200
    day = next(iter(store.stats(1)))["day"]

    report = build_report(store, 10, 200, today=day)
    assert report["last"]["active_users"] == 2
    assert report["last"]["new_users"] == 2
    assert report["total_users"] == 2
    assert len(report["series"]) == 14

    subject, text, html = render(report)
    assert "2 Nutzer" in subject and "2 neu" in subject
    assert "Aktive Nutzer" in text and "Tagesbericht" in html
    # numbers only: no address anywhere
    assert "example.com" not in subject + text + html


def test_the_report_can_be_sent_on_demand_and_only_by_the_operator(harness, monkeypatch):
    monkeypatch.setenv("REPORT_TO", "ops@example.org")
    c = harness.client()
    # the test app has no METRICS_TOKEN: operator pages are for the machine itself only
    assert c.post("/api/report/send").status_code == 403


def test_meta_remembers_the_day_of_the_last_report(harness):
    store = harness.main.store
    assert store.get_meta("last_report") is None
    store.set_meta("last_report", "2026-11-17")
    store.set_meta("last_report", "2026-11-18")
    assert store.get_meta("last_report") == "2026-11-18"
