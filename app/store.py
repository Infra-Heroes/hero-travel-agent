"""Everything the agent remembers, in one SQLite file on its volume.

- users: an e-mail address is an account; it is created the first time its one-time
  code is entered, which proves the address is the person's.
- one-time codes: only a keyed hash is stored, with an expiry and a counter of wrong
  tries.
- trips: saved suggestions and plans, each belonging to one user.
- usage: model calls per user and day, and for everybody together, so a person and
  the agent as a whole both have a ceiling.
- activity: which users were active on which day. That is what "users per day" is
  counted from, and it stays when a user is deleted.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

MAX_CODE_TRIES = 5


def today() -> str:
    return datetime.now(UTC).date().isoformat()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        with self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_codes (
                    email TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    tries INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS trips (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('suggestions', 'plan')),
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS trips_by_user ON trips (user_id, created_at);
                CREATE TABLE IF NOT EXISTS user_usage (
                    user_id TEXT NOT NULL,
                    day TEXT NOT NULL,
                    calls INTEGER NOT NULL,
                    PRIMARY KEY (user_id, day)
                );
                CREATE TABLE IF NOT EXISTS usage (day TEXT PRIMARY KEY, calls INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS activity (
                    day TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    PRIMARY KEY (day, user_id)
                );
                """
            )

    # -- users ---------------------------------------------------------------

    def login(self, email: str) -> tuple[dict[str, Any], bool]:
        """The user with this address, created if new. Also marks them active today."""
        with self._lock, self._db:
            row = self._db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            created = row is None
            if created:
                user_id = uuid.uuid4().hex
                self._db.execute(
                    "INSERT INTO users (id, email, created_at, last_login_at) VALUES (?, ?, ?, ?)",
                    (user_id, email, now_iso(), now_iso()),
                )
            else:
                user_id = row["id"]
                self._db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso(), user_id))
            self._db.execute(
                "INSERT OR IGNORE INTO activity (day, user_id) VALUES (?, ?)", (today(), user_id)
            )
            user = self._db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(user), created

    def delete_user(self, user_id: str) -> bool:
        """Erase the person: account, trips (cascade), usage and activity rows.

        The agent-wide daily counter (`usage`) carries no user and stays."""
        with self._lock, self._db:
            row = self._db.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
            if row is None:
                return False
            self._db.execute("DELETE FROM login_codes WHERE email = ?", (row["email"],))
            self._db.execute("DELETE FROM user_usage WHERE user_id = ?", (user_id,))
            self._db.execute("DELETE FROM activity WHERE user_id = ?", (user_id,))
            self._db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return True

    def user(self, user_id: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def mark_active(self, user_id: str, day: str | None = None) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO activity (day, user_id) VALUES (?, ?)", (day or today(), user_id)
            )

    # -- one-time codes ------------------------------------------------------

    def put_code(self, email: str, code_hash: str, ttl_seconds: int) -> None:
        expires = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat(timespec="seconds")
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO login_codes (email, code_hash, expires_at, tries) VALUES (?, ?, ?, 0) "
                "ON CONFLICT(email) DO UPDATE SET code_hash = excluded.code_hash, "
                "expires_at = excluded.expires_at, tries = 0",
                (email, code_hash, expires),
            )

    def take_code(self, email: str, matches) -> str:  # type: ignore[no-untyped-def]
        """Check a code. Returns "ok" (the code is used up), "wrong", "expired" or "none".

        `matches(stored_hash)` does the comparison, so the secret stays in the auth
        module. A code is dead after MAX_CODE_TRIES wrong tries, whatever it is."""
        with self._lock, self._db:
            row = self._db.execute("SELECT * FROM login_codes WHERE email = ?", (email,)).fetchone()
            if row is None:
                return "none"
            if row["expires_at"] < now_iso() or row["tries"] >= MAX_CODE_TRIES:
                self._db.execute("DELETE FROM login_codes WHERE email = ?", (email,))
                return "expired"
            if matches(row["code_hash"]):
                self._db.execute("DELETE FROM login_codes WHERE email = ?", (email,))
                return "ok"
            self._db.execute("UPDATE login_codes SET tries = tries + 1 WHERE email = ?", (email,))
            return "wrong"

    # -- limits --------------------------------------------------------------

    def try_spend(self, user_id: str, user_limit: int, global_limit: int, day: str | None = None) -> str:
        """Count one model call, or say why not: "ok", "user" (the person's limit) or
        "global" (the agent's). The check and the increment are one statement each, so two
        requests at once cannot both take the last call."""
        day = day or today()
        with self._lock, self._db:
            self._db.execute("INSERT OR IGNORE INTO usage (day, calls) VALUES (?, 0)", (day,))
            self._db.execute(
                "INSERT OR IGNORE INTO user_usage (user_id, day, calls) VALUES (?, ?, 0)", (user_id, day)
            )
            if (
                self._db.execute(
                    "UPDATE usage SET calls = calls + 1 WHERE day = ? AND calls < ?", (day, global_limit)
                ).rowcount
                != 1
            ):
                return "global"
            if (
                self._db.execute(
                    "UPDATE user_usage SET calls = calls + 1 WHERE user_id = ? AND day = ? AND calls < ?",
                    (user_id, day, user_limit),
                ).rowcount
                != 1
            ):
                # The agent-wide count was taken first; give it back.
                self._db.execute("UPDATE usage SET calls = calls - 1 WHERE day = ?", (day,))
                return "user"
        self.mark_active(user_id, day)
        return "ok"

    def calls_today(self, user_id: str | None = None, day: str | None = None) -> int:
        day = day or today()
        if user_id is None:
            row = self._db.execute("SELECT calls FROM usage WHERE day = ?", (day,)).fetchone()
        else:
            row = self._db.execute(
                "SELECT calls FROM user_usage WHERE user_id = ? AND day = ?", (user_id, day)
            ).fetchone()
        return int(row["calls"]) if row else 0

    # -- numbers -------------------------------------------------------------

    def stats(self, days: int = 30) -> list[dict[str, Any]]:
        """Per day, newest first: users active, new users, model calls."""
        since = (datetime.now(UTC).date() - timedelta(days=days - 1)).isoformat()
        rows = self._db.execute(
            """
            SELECT d.day,
                   (SELECT COUNT(*) FROM activity a WHERE a.day = d.day) AS active_users,
                   (SELECT COUNT(*) FROM users u WHERE substr(u.created_at, 1, 10) = d.day) AS new_users,
                   COALESCE((SELECT calls FROM usage g WHERE g.day = d.day), 0) AS calls
            FROM (SELECT day FROM activity WHERE day >= ?
                  UNION SELECT day FROM usage WHERE day >= ?
                  UNION SELECT substr(created_at, 1, 10) FROM users WHERE substr(created_at, 1, 10) >= ?) d
            ORDER BY d.day DESC
            """,
            (since, since, since),
        ).fetchall()
        return [dict(r) for r in rows]

    def user_count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    # -- trips (always a user's own) ------------------------------------------

    def save(self, user_id: str, title: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        trip = {
            "id": uuid.uuid4().hex[:12],
            "title": title[:120],
            "kind": kind,
            "payload": payload,
            "created_at": now_iso(),
        }
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO trips (id, user_id, title, kind, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    trip["id"],
                    user_id,
                    trip["title"],
                    kind,
                    json.dumps(payload, ensure_ascii=False),
                    trip["created_at"],
                ),
            )
        return trip

    def list(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT id, title, kind, created_at FROM trips WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get(self, user_id: str, trip_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT * FROM trips WHERE id = ? AND user_id = ?", (trip_id, user_id)
        ).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["payload"] = json.loads(out["payload"])
        return out

    def delete(self, user_id: str, trip_id: str) -> bool:
        with self._lock, self._db:
            cur = self._db.execute("DELETE FROM trips WHERE id = ? AND user_id = ?", (trip_id, user_id))
        return cur.rowcount > 0
