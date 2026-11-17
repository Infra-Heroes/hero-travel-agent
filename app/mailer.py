"""Sending the one-time code by e-mail.

Two backends, chosen by MAIL_BACKEND:
- smtp (default when SMTP_HOST is set): a real server, STARTTLS on port 587 or implicit
  TLS on 465. SMTP_USER / SMTP_PASSWORD are optional (a local catcher needs none).
- console: the message is logged and kept in memory (`outbox`). For tests and for trying
  the agent on a laptop without a mail server. It is never the default in production:
  without SMTP_HOST and without MAIL_BACKEND=console nothing can log in.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger("travel-agent")


class MailError(Exception):
    """The message could not be handed to the mail server."""


class Mailer:
    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "")
        self.backend = os.getenv("MAIL_BACKEND") or ("smtp" if self.host else "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.sender = os.getenv("MAIL_FROM", "Urlaubs-Agent <noreply@localhost>")
        self.outbox: list[EmailMessage] = []

    @property
    def configured(self) -> bool:
        return self.backend in ("smtp", "console")

    async def send(self, to: str, subject: str, body: str) -> None:
        if not self.configured:
            raise MailError("no mail backend configured (SMTP_HOST or MAIL_BACKEND=console)")
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        if self.backend == "console":
            self.outbox.append(message)
            logger.info("mail to %s: %s | %s", to, subject, body.replace("\n", " "))
            return
        try:
            await asyncio.to_thread(self._smtp, message)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailError(str(exc)) from exc

    def _smtp(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        if self.port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(self.host, self.port, timeout=20, context=context)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=20)
        with server:
            # EHLO first: the server's capabilities (STARTTLS) are only known after it, and
            # a server such as IONOS offers AUTH only once the connection is encrypted.
            server.ehlo()
            if self.port != 465 and server.has_extn("starttls"):
                server.starttls(context=context)
                server.ehlo()
            if self.user:
                server.login(self.user, self.password)
            server.send_message(message)
