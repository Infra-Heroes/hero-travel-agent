"""The sign-in mail as HTML, in German or English.

Mail clients ignore most of CSS, so this is the old way: tables, inline styles, system
fonts, no images and no external resources (nothing is loaded, nothing tracks the reader).
The plain-text part stays the fallback, so a client that shows no HTML still shows the code.
"""

from __future__ import annotations

from html import escape

ACCENT = "#0f766e"

TEXTS = {
    "de": {
        "title": "Dein Code für den Urlaubs-Agent",
        "brand": "Urlaubs-Agent",
        "heading": "Dein Anmelde-Code",
        "intro": "Gib diesen Code auf der Seite ein, um dich anzumelden.",
        "valid": "Der Code gilt <strong>{minutes} Minuten</strong> und nur einmal. "
        "Du hast ihn nicht angefordert? Dann ignoriere diese Mail, es passiert nichts.",
        "pre": "Dein Code: {code}. Er gilt {minutes} Minuten.",
        "privacy": "Datenschutz",
        "legal": "Impressum",
    },
    "en": {
        "title": "Your code for the holiday agent",
        "brand": "Holiday agent",
        "heading": "Your sign-in code",
        "intro": "Enter this code on the page to sign in.",
        "valid": "The code is valid for <strong>{minutes} minutes</strong> and works once. "
        "You did not request it? Then ignore this e-mail, nothing happens.",
        "pre": "Your code: {code}. It is valid for {minutes} minutes.",
        "privacy": "Privacy",
        "legal": "Legal notice",
    },
}

FONT = "-apple-system,Segoe UI,Helvetica,Arial,sans-serif"


def login_mail_html(code: str, minutes: int = 10, lang: str = "de") -> str:
    x = TEXTS.get(lang, TEXTS["de"])
    digits = "".join(
        f'<td style="width:44px;height:56px;background:#e6f4f2;border-radius:10px;'
        f'font:700 30px/56px ui-monospace,Menlo,Consolas,monospace;color:#0b4f4a;text-align:center">'
        f'{escape(c)}</td><td style="width:6px"></td>'
        for c in code
    )
    preheader = escape(x["pre"].format(code=code, minutes=minutes))
    return f"""<!doctype html>
<html lang="{lang if lang in TEXTS else "de"}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>{x["title"]}</title></head>
<body style="margin:0;padding:0;background:#f6f7fb">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{preheader}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f7fb;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="480" cellspacing="0" cellpadding="0"
  style="max-width:480px;width:100%;background:#ffffff;border-radius:16px;border:1px solid #e3e6ee">
  <tr><td style="background:{ACCENT};border-radius:16px 16px 0 0;padding:22px 28px;
    font:600 20px {FONT};color:#ffffff">&#9992;&#65039; {x["brand"]}</td></tr>
  <tr><td style="padding:28px 28px 8px;font:16px/1.55 {FONT};color:#16181d">
    <p style="margin:0 0 6px;font-size:20px;font-weight:700">{x["heading"]}</p>
    <p style="margin:0;color:#646a76">{x["intro"]}</p>
  </td></tr>
  <tr><td align="center" style="padding:18px 28px">
    <table role="presentation" cellspacing="0" cellpadding="0"><tr>{digits}</tr></table>
  </td></tr>
  <tr><td style="padding:0 28px 26px;font:14px/1.55 {FONT};color:#646a76">
    {x["valid"].format(minutes=minutes)}
  </td></tr>
  <tr><td style="border-top:1px solid #e3e6ee;padding:16px 28px;font:12px/1.5 {FONT};color:#8a909c">
    InfraHeroes UG (haftungsbeschr&auml;nkt) &middot; Lange Str. 73 &middot; 61440 Oberursel<br>
    <a href="https://urlaubs-agent.heroapp.run/datenschutz" style="color:#8a909c">{x["privacy"]}</a> &middot;
    <a href="https://urlaubs-agent.heroapp.run/impressum" style="color:#8a909c">{x["legal"]}</a>
  </td></tr>
</table>
</td></tr></table>
</body></html>
"""
