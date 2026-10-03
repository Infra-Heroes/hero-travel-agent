"""Saved trips, in a SQLite file on the agent's own volume.

One agent belongs to one person, so there is no user column: everything in
this file is theirs, and deleting the volume deletes all of it.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TripStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS trips (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('suggestions', 'plan')),
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self._db.commit()

    def save(self, title: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        trip = {
            "id": uuid.uuid4().hex[:12],
            "title": title[:120],
            "kind": kind,
            "payload": payload,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        self._db.execute(
            "INSERT INTO trips (id, title, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (trip["id"], trip["title"], kind, json.dumps(payload, ensure_ascii=False), trip["created_at"]),
        )
        self._db.commit()
        return trip

    def list(self) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT id, title, kind, created_at FROM trips ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get(self, trip_id: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["payload"] = json.loads(out["payload"])
        return out

    def delete(self, trip_id: str) -> bool:
        cur = self._db.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
        self._db.commit()
        return cur.rowcount > 0
