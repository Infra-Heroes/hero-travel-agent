# Security

## Reporting a vulnerability

Please do not open a public issue. Write to **info@infra-heroes.de** with the subject
"Security Urlaubs-Agent". We will get back to you as soon as we can.

## How the agent is protected

### Sign-in

- Accounts are e-mail addresses; you sign in with a six-digit code, no password.
- A code is valid for 10 minutes, once, for at most 5 attempts. Only an HMAC-SHA256 of the code
  with the server key is stored.
- "Send code" answers the same for known and unknown addresses; nobody can find out who has an
  account.
- Rate limited: asking for codes (3 per address and 10 per client in 10 minutes, 200 an hour in
  total) and trying codes (20 per client in 10 minutes).
- The session is a signed cookie: HttpOnly, SameSite=Strict, Secure over HTTPS, 14 days.
- `ALLOWED_EMAILS` and `ALLOWED_EMAIL_DOMAINS` restrict who may sign in.

### Data

- Every saved trip, profile and rating belongs to exactly one person; every query filters by them.
- Share links are random tokens (144 bits), expire, can be withdrawn and show nothing about the
  person. The page sends only the domain as referrer and is not indexed.
- Saved plans are validated against the schema before they are stored.

### Page

- Content Security Policy: scripts, styles and connections from the own host only, images also
  from `tile.openstreetmap.org`; no inline scripts, no framing by other sites.
- Everything that comes from a model answer is set as text, never as HTML.
- Also `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`,
  `Cross-Origin-Opener-Policy` and, over HTTPS, `Strict-Transport-Security`.
- Requests over 256 KB are refused before they are read.

### Cost

Daily limits per person and in total cap what one account, or an attack, can cost in model calls.

### Operations

- The server runs in the container as an unprivileged user.
- Secrets come from the platform, never from the repository.
- CI checks every pull request with `bandit` (code patterns) and `pip-audit` (known vulnerabilities
  in dependencies); Renovate keeps dependencies up to date.
