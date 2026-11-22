"""The few sentences the server itself says, in German and English.

The language comes from the page (header X-Lang, set by static/i18n.js), else the browser's
Accept-Language; without either it is German, the language the pages are written in."""

from __future__ import annotations

from starlette.requests import Request

MESSAGES: dict[str, dict[str, str]] = {
    "signin": {"de": "Bitte anmelden.", "en": "Please sign in."},
    "forbidden": {"de": "Nicht erlaubt.", "en": "Not allowed."},
    "bad_email": {
        "de": "Bitte eine gültige E-Mail-Adresse eingeben.",
        "en": "Please enter a valid e-mail address.",
    },
    "too_many_requests": {
        "de": "Zu viele Anfragen. Bitte in einigen Minuten nochmal.",
        "en": "Too many requests. Please try again in a few minutes.",
    },
    "signin_unavailable": {
        "de": "Die Anmeldung ist gerade nicht möglich.",
        "en": "Signing in is not possible right now.",
    },
    "sent": {
        "de": "Wenn die Adresse stimmt, ist ein Code unterwegs. Er gilt 10 Minuten.",
        "en": "If the address is right, a code is on its way. It is valid for 10 minutes.",
    },
    "too_many_tries": {
        "de": "Zu viele Versuche. Bitte in einigen Minuten nochmal.",
        "en": "Too many attempts. Please try again in a few minutes.",
    },
    "code_expired": {
        "de": "Der Code ist abgelaufen. Bitte einen neuen anfordern.",
        "en": "The code has expired. Please request a new one.",
    },
    "code_wrong": {"de": "Der Code stimmt nicht.", "en": "The code is not correct."},
    "user_limit": {
        "de": "Du hast dein Tageslimit von {n} Anfragen erreicht. Morgen geht es weiter.",
        "en": "You have reached your daily limit of {n} requests. It continues tomorrow.",
    },
    "agent_busy": {
        "de": "Der Agent ist für heute ausgelastet. Bitte morgen wieder versuchen.",
        "en": "The agent is fully booked for today. Please try again tomorrow.",
    },
    "too_many_trips": {
        "de": "Du hast {n} Reisen gespeichert, das ist das Maximum. Bitte lösche eine.",
        "en": "You have saved {n} trips, which is the maximum. Please delete one.",
    },
    "bad_plan": {"de": "Ungültiger Reiseplan", "en": "Invalid trip plan"},
    "no_trip": {"de": "Reise nicht gefunden", "en": "Trip not found"},
    "no_plan": {"de": "Kein Tagesplan gefunden", "en": "No day plan found"},
    "share_gone": {
        "de": "Dieser Link ist abgelaufen oder wurde zurückgezogen.",
        "en": "This link has expired or was withdrawn.",
    },
    "mail_subject": {
        "de": "Dein Code für den Urlaubs-Agent",
        "en": "Your code for the holiday agent",
    },
    "mail_text": {
        "de": "Dein Code: {code}\n\nEr gilt 10 Minuten und nur einmal. "
        "Wenn du ihn nicht angefordert hast, kannst du diese Mail ignorieren.\n",
        "en": "Your code: {code}\n\nIt is valid for 10 minutes and works once. "
        "If you did not request it, you can ignore this e-mail.\n",
    },
}


def lang_of(request: Request, preferred: str | None = None) -> str:
    if preferred in ("de", "en"):
        return preferred
    header = request.headers.get("x-lang", "").lower()
    if header in ("de", "en"):
        return header
    accept = request.headers.get("accept-language", "").lower()
    if accept and not accept.startswith("de"):
        return "en"
    return "de"


def say(request: Request, key: str, preferred: str | None = None, **values: object) -> str:
    return MESSAGES[key][lang_of(request, preferred)].format(**values)
