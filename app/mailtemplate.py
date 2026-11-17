"""The sign-in mail as HTML.

Mail clients ignore most of CSS, so this is the old way: tables, inline styles, system
fonts, no images and no external resources (nothing is loaded, nothing tracks the reader).
The plain-text part stays the fallback, so a client that shows no HTML still shows the code.
"""

from __future__ import annotations

from html import escape

ACCENT = "#0f766e"


def login_mail_html(code: str, minutes: int = 10) -> str:
    digits = "".join(
        f'<td style="width:44px;height:56px;margin:0 3px;background:#e6f4f2;border-radius:10px;'
        f'font:700 30px/56px ui-monospace,Menlo,Consolas,monospace;color:#0b4f4a;text-align:center">'
        f'{escape(c)}</td><td style="width:6px"></td>'
        for c in code
    )
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Dein Code fM-CM-<r den Urlaubs-Agent</title></head>
<body style="margin:0;padding:0;background:#f6f7fb">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">Dein Code: {escape(code)}. Er gilt {minutes} Minuten.</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f7fb;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="480" cellspacing="0" cellpadding="0"
  style="max-width:480px;width:100%;background:#ffffff;border-radius:16px;border:1px solid #e3e6ee">
  <tr><td style="background:{ACCENT};border-radius:16px 16px 0 0;padding:22px 28px;
    font:600 20px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#ffffff">
    &#9992;&#65039; Urlaubs-Agent</td></tr>
  <tr><td style="padding:28px 28px 8px;font:16px/1.55 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#16181d">
    <p style="margin:0 0 6px;font-size:20px;font-weight:700">Dein Anmelde-Code</p>
    <p style="margin:0;color:#646a76">Gib diesen Code auf der Seite ein, um dich anzumelden.</p>
  </td></tr>
  <tr><td align="center" style="padding:18px 28px">
    <table role="presentation" cellspacing="0" cellpadding="0"><tr>{digits}</tr></table>
  </td></tr>
  <tr><td style="padding:0 28px 26px;font:14px/1.55 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#646a76">
    Der Code gilt <strong>{minutes} Minuten</strong> und nur einmal.
    Du hast ihn nicht angefordert? Dann ignoriere diese Mail, es passiert nichts.
  </td></tr>
  <tr><td style="border-top:1px solid #e3e6ee;padding:16px 28px;font:12px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#8a909c">
    InfraHeroes UG (haftungsbeschr&auml;nkt) &middot; Lange Str. 73 &middot; 61440 Oberursel<br>
    <a href="https://urlaubs-agent.heroapp.run/datenschutz" style="color:#8a909c">Datenschutz</a> &middot;
    <a href="https://urlaubs-agent.heroapp.run/impressum" style="color:#8a909c">Impressum</a>
  </td></tr>
</table>
</td></tr></table>
</body></html>
"""
