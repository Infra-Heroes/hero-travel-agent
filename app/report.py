"""The daily report for the operator: how many people used the agent.

Sent once a day by the app itself (no cron, no extra service). What it says comes from the
counters the app already keeps for its limits: users active per day, new sign-ups, model
calls. It names no person and no address, only numbers.

REPORT_TO       who gets it (a secret in the deployment); empty means no report
REPORT_HOUR_UTC the hour it is sent, default 6 (07:00 or 08:00 in Germany)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from html import escape
from typing import Any

from app.mailer import Mailer, MailError
from app.store import Store

logger = logging.getLogger("travel-agent")

DAYS = 14
FONT = "-apple-system,Segoe UI,Helvetica,Arial,sans-serif"


def build_report(
    store: Store, daily_user_limit: int, agent_daily_calls: int, today: str | None = None
) -> dict[str, Any]:
    """Numbers for the last DAYS days; `today` is the day being reported on (yesterday if sent in
    the morning, so the figures are complete)."""
    day = today or (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    rows = {r["day"]: r for r in store.stats(DAYS + 2)}
    series: list[dict[str, Any]] = []
    for offset in range(DAYS):
        d = (datetime.fromisoformat(day) - timedelta(days=offset)).date().isoformat()
        r = rows.get(d, {})
        series.append(
            {
                "day": d,
                "active_users": int(r.get("active_users", 0)),
                "new_users": int(r.get("new_users", 0)),
                "calls": int(r.get("calls", 0)),
            }
        )
    last = series[0]
    week = series[:7]
    return {
        "day": day,
        "last": last,
        "series": series,
        "total_users": store.user_count(),
        "week_active_peak": max((r["active_users"] for r in week), default=0),
        "week_new": sum(r["new_users"] for r in week),
        "week_calls": sum(r["calls"] for r in week),
        "user_limit": daily_user_limit,
        "agent_limit": agent_daily_calls,
    }


def _bar(value: int, top: int) -> str:
    width = 0 if top <= 0 else max(2 if value else 0, round(120 * value / top))
    return (
        f'<div style="background:#0f766e;height:10px;border-radius:5px;width:{width}px;'
        f'display:inline-block;vertical-align:middle"></div>'
    )


def render(report: dict[str, Any]) -> tuple[str, str, str]:
    """(subject, plain text, html)."""
    last = report["last"]
    subject = (
        f"Urlaubs-Agent {report['day']}: {last['active_users']} Nutzer, "
        f"{last['new_users']} neu, {last['calls']} Anfragen"
    )
    text_lines = [
        f"Urlaubs-Agent, Tagesbericht für {report['day']}",
        "",
        f"Aktive Nutzer:    {last['active_users']}",
        f"Neue Nutzer:      {last['new_users']}",
        f"Anfragen an KI:   {last['calls']} (Tageslimit gesamt {report['agent_limit']})",
        f"Nutzer insgesamt: {report['total_users']}",
        "",
        "Letzte Tage (aktiv / neu / Anfragen):",
    ]
    text_lines += [
        f"  {r['day']}  {r['active_users']:>3} / {r['new_users']:>3} / {r['calls']:>4}"
        for r in report["series"]
    ]
    top_active = max((r["active_users"] for r in report["series"]), default=0)
    top_calls = max((r["calls"] for r in report["series"]), default=0)
    rows = "".join(
        f'<tr><td style="padding:6px 10px;border-top:1px solid #e3e6ee">{escape(r["day"])}</td>'
        f'<td style="padding:6px 10px;border-top:1px solid #e3e6ee;text-align:right">{r["active_users"]}</td>'
        f'<td style="padding:6px 10px;border-top:1px solid #e3e6ee">{_bar(r["active_users"], top_active)}</td>'
        f'<td style="padding:6px 10px;border-top:1px solid #e3e6ee;text-align:right">{r["new_users"]}</td>'
        f'<td style="padding:6px 10px;border-top:1px solid #e3e6ee;text-align:right">{r["calls"]}</td>'
        f'<td style="padding:6px 10px;border-top:1px solid #e3e6ee">{_bar(r["calls"], top_calls)}</td></tr>'
        for r in report["series"]
    )

    def tile(label: str, value: object, note: str = "") -> str:
        return (
            f'<td style="padding:6px"><div style="background:#e6f4f2;border-radius:12px;padding:14px 16px">'
            f'<div style="font:12px {FONT};color:#646a76;text-transform:uppercase;letter-spacing:.04em">{label}</div>'
            f'<div style="font:700 30px {FONT};color:#0b4f4a">{value}</div>'
            f'<div style="font:12px {FONT};color:#646a76">{note}</div></div></td>'
        )

    html = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(subject)}</title></head>
<body style="margin:0;padding:0;background:#f6f7fb">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f7fb;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0"
  style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;border:1px solid #e3e6ee">
  <tr><td style="background:#0f766e;border-radius:16px 16px 0 0;padding:20px 28px;font:600 20px {FONT};color:#ffffff">
    &#9992;&#65039; Urlaubs-Agent &middot; Tagesbericht</td></tr>
  <tr><td style="padding:22px 28px 6px;font:15px/1.5 {FONT};color:#16181d">
    Zahlen für <strong>{escape(report["day"])}</strong> (UTC-Tag).</td></tr>
  <tr><td style="padding:8px 22px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>
    {tile("Aktive Nutzer", last["active_users"], f"Spitze 7 Tage: {report['week_active_peak']}")}
    {tile("Neue Nutzer", last["new_users"], f"7 Tage: {report['week_new']}")}
  </tr><tr>
    {tile("Anfragen an die KI", last["calls"], f"von {report['agent_limit']} am Tag, 7 Tage: {report['week_calls']}")}
    {tile("Nutzer insgesamt", report["total_users"], f"{report['user_limit']} Anfragen pro Person und Tag")}
  </tr></table></td></tr>
  <tr><td style="padding:14px 28px 6px;font:600 15px {FONT};color:#16181d">Verlauf</td></tr>
  <tr><td style="padding:0 18px 22px">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font:13px {FONT};color:#16181d">
      <tr style="color:#646a76;font-size:12px"><td style="padding:6px 10px">Tag</td>
        <td style="padding:6px 10px;text-align:right">Aktiv</td><td></td>
        <td style="padding:6px 10px;text-align:right">Neu</td>
        <td style="padding:6px 10px;text-align:right">Anfragen</td><td></td></tr>
      {rows}
    </table>
  </td></tr>
  <tr><td style="border-top:1px solid #e3e6ee;padding:14px 28px;font:12px/1.5 {FONT};color:#8a909c">
    Nur Zahlen, keine Namen oder Adressen. Quelle: Zähler der App (Tageslimit und Aktivität).
  </td></tr>
</table></td></tr></table></body></html>
"""
    return subject, "\n".join(text_lines) + "\n", html


async def send_report(store: Store, mailer: Mailer, to: str, user_limit: int, agent_limit: int) -> None:
    subject, text, html = render(build_report(store, user_limit, agent_limit))
    await mailer.send(to, subject, text, html=html)


async def report_loop(store: Store, mailer: Mailer, user_limit: int, agent_limit: int) -> None:
    """Once a day at REPORT_HOUR_UTC; a restart on the same day does not send it twice."""
    to = os.getenv("REPORT_TO", "").strip()
    if not to or not mailer.configured:
        logger.info("daily report off (REPORT_TO or the mail backend is not set)")
        return
    hour = int(os.getenv("REPORT_HOUR_UTC", "6"))
    while True:
        now = datetime.now(UTC)
        due = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if now >= due and store.get_meta("last_report") != now.date().isoformat():
            try:
                await send_report(store, mailer, to, user_limit, agent_limit)
                store.set_meta("last_report", now.date().isoformat())
                logger.info("daily report sent")
            except MailError as exc:
                logger.error("daily report not sent: %s", exc)
        await asyncio.sleep(600)
