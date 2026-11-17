"""The SMTP conversation, in the order a real server such as IONOS needs."""

from __future__ import annotations

import smtplib
from typing import ClassVar

import pytest

from app.mailer import Mailer, MailError


class FakeSMTP:
    """Records what the mailer says, and behaves like a server that offers AUTH only
    after STARTTLS (and STARTTLS only after EHLO)."""

    log: ClassVar[list[str]] = []

    def __init__(self, host, port, timeout=None, context=None):
        self.encrypted = context is not None and port == 465
        self.greeted = False
        FakeSMTP.log.append(f"connect {host}:{port}")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        FakeSMTP.log.append("quit")

    def ehlo(self):
        self.greeted = True
        FakeSMTP.log.append("ehlo")

    def has_extn(self, name):
        return self.greeted and name == "starttls" and not self.encrypted

    def starttls(self, context=None):
        assert self.greeted, "STARTTLS before EHLO"
        self.encrypted = True
        self.greeted = False
        FakeSMTP.log.append("starttls")

    def login(self, user, password):
        if not self.encrypted:
            raise smtplib.SMTPNotSupportedError("SMTP AUTH extension not supported by server.")
        FakeSMTP.log.append(f"login {user}")

    def send_message(self, message):
        FakeSMTP.log.append(f"send to {message['To']}")


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.log = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    for key, value in {
        "SMTP_HOST": "smtp.example.org",
        "SMTP_USER": "u@example.org",
        "SMTP_PASSWORD": "pw",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("MAIL_BACKEND", raising=False)
    return FakeSMTP


async def test_starttls_comes_before_the_login_as_a_server_like_ionos_needs(smtp, monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "587")
    await Mailer().send("a@example.com", "Betreff", "Text")
    assert smtp.log == [
        "connect smtp.example.org:587",
        "ehlo",
        "starttls",
        "ehlo",
        "login u@example.org",
        "send to a@example.com",
        "quit",
    ]


async def test_port_465_is_tls_from_the_start(smtp, monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "465")
    await Mailer().send("a@example.com", "Betreff", "Text")
    assert "starttls" not in smtp.log and "login u@example.org" in smtp.log


async def test_a_server_without_credentials_needs_no_login(smtp, monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.delenv("SMTP_USER")
    await Mailer().send("a@example.com", "Betreff", "Text")
    assert not any(line.startswith("login") for line in smtp.log)


async def test_a_refusing_server_becomes_a_mail_error(smtp, monkeypatch):
    def refuse(self, user, password):
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr(FakeSMTP, "login", refuse)
    with pytest.raises(MailError):
        await Mailer().send("a@example.com", "Betreff", "Text")
