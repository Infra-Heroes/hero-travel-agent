"""The report loop: once a day at the configured hour, never twice, survives a mail failure."""

from __future__ import annotations

import asyncio

import pytest

from app import report as report_module
from app.mailer import Mailer, MailError
from app.report import report_loop


class StopLoop(Exception):
    """Raised instead of sleeping, so the loop runs exactly as often as a test wants."""


def _sleep_then_stop(rounds: int):
    seen = {"n": 0}

    async def sleep(_seconds: float) -> None:
        seen["n"] += 1
        if seen["n"] >= rounds:
            raise StopLoop

    return sleep


@pytest.fixture
def console_mailer(monkeypatch) -> Mailer:
    monkeypatch.setenv("MAIL_BACKEND", "console")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    return Mailer()


async def test_sends_once_a_day_and_remembers_it(harness, console_mailer, monkeypatch):
    monkeypatch.setenv("REPORT_TO", "ops@example.org")
    monkeypatch.setenv("REPORT_HOUR_UTC", "0")
    monkeypatch.setattr(report_module.asyncio, "sleep", _sleep_then_stop(2))
    with pytest.raises(StopLoop):
        await report_loop(harness.main.store, console_mailer, 10, 200)
    # Two rounds on the same day, one mail.
    assert [m["To"] for m in console_mailer.outbox] == ["ops@example.org"]
    assert harness.main.store.get_meta("last_report")


async def test_a_mail_failure_is_logged_and_retried_later(harness, console_mailer, monkeypatch, caplog):
    monkeypatch.setenv("REPORT_TO", "ops@example.org")
    monkeypatch.setenv("REPORT_HOUR_UTC", "0")
    monkeypatch.setattr(report_module.asyncio, "sleep", _sleep_then_stop(1))

    async def broken(*_args, **_kwargs):
        raise MailError("smtp down")

    monkeypatch.setattr(console_mailer, "send", broken)
    with pytest.raises(StopLoop):
        await report_loop(harness.main.store, console_mailer, 10, 200)
    assert "daily report not sent" in caplog.text
    # Not marked as sent: the next round tries again.
    assert harness.main.store.get_meta("last_report") is None


@pytest.mark.parametrize(("to", "backend"), [("", "console"), ("ops@example.org", "")])
async def test_off_without_recipient_or_mail(harness, monkeypatch, to, backend):
    monkeypatch.setenv("REPORT_TO", to)
    monkeypatch.setenv("MAIL_BACKEND", backend)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    # Returns at once instead of looping.
    await asyncio.wait_for(report_loop(harness.main.store, Mailer(), 10, 200), timeout=1)
