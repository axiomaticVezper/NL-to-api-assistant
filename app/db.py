"""
Tiny SQLite layer. SQLite ships with Python, so there is nothing to install,
and the data survives server restarts (unlike the in-memory dicts in routes).
Everything that touches the database goes through get_conn(), so swapping
SQLite for Postgres later (Phase 5) only means changing this one file.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    event_id    TEXT PRIMARY KEY,
    plan_id     TEXT NOT NULL,
    workflow_id TEXT,
    event_type  TEXT NOT NULL,
    actor       TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    risk_tier   TEXT NOT NULL,
    detail      TEXT NOT NULL,
    timestamp   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_plan ON audit_events(plan_id);
"""


def _db_path() -> Path:
    # Read at call time so tests can point this at a temporary file.
    return Path(os.environ.get("APP_DB_PATH", "data/app.db"))


@contextmanager
def get_conn():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)  # idempotent: only creates what's missing
        yield conn
        conn.commit()
    finally:
        conn.close()