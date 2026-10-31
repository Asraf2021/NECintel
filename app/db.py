"""SQLite qatı: sxem, əlaqə və sadə sorğu köməkçiləri."""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS routes (
    id TEXT PRIMARY KEY,
    number TEXT NOT NULL,
    name TEXT NOT NULL,
    carrier TEXT,
    color TEXT NOT NULL,
    peak_bias REAL NOT NULL DEFAULT 0.2,
    monitored INTEGER NOT NULL DEFAULT 0,
    length_m REAL NOT NULL DEFAULT 0,
    duration_min REAL,
    avg_speed_kmh REAL NOT NULL DEFAULT 18
);
CREATE TABLE IF NOT EXISTS route_points (
    route_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    PRIMARY KEY (route_id, seq)
);
CREATE TABLE IF NOT EXISTS stops (
    id TEXT PRIMARY KEY,
    code TEXT,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stops_name ON stops(name);
CREATE TABLE IF NOT EXISTS route_stops (
    route_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    stop_id TEXT NOT NULL,
    direction INTEGER NOT NULL,
    position_m REAL NOT NULL,
    PRIMARY KEY (route_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_route_stops_stop ON route_stops(stop_id);
CREATE TABLE IF NOT EXISTS buses (
    id TEXT PRIMARY KEY,
    route_id TEXT NOT NULL,
    plate TEXT NOT NULL,
    position_m REAL NOT NULL,
    speed_kmh REAL NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_buses_route ON buses(route_id);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id TEXT NOT NULL,
    bus_id TEXT,
    stop_id TEXT,
    user_id INTEGER,
    level TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'passenger',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_route_time ON reports(route_id, created_at);
CREATE TABLE IF NOT EXISTS line_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    score REAL NOT NULL,
    report_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_line_state_route_ts ON line_state(route_id, ts);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id TEXT NOT NULL,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    acknowledged_at TEXT,
    resolved_at TEXT
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def from_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Database:
    """Tək əlaqə + kilid. Prototip üçün kifayətdir; istehsalda PostgreSQL ilə əvəz olunur."""

    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            self._conn.commit()
            return cur

    def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        with self._lock:
            self._conn.executemany(sql, [tuple(r) for r in rows])
            self._conn.commit()

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def transaction(self):
        """`with db.transaction(): ...` – bir neçə yazını tək commit ilə icra etmək üçün."""
        return _Tx(self)

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class _Tx:
    def __init__(self, db: Database) -> None:
        self.db = db

    def __enter__(self):
        self.db._lock.acquire()
        return self.db._conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.db._conn.commit()
            else:
                self.db._conn.rollback()
        finally:
            self.db._lock.release()
        return False
