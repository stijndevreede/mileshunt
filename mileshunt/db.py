"""SQLite database for search logs and user accounts."""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get("MILESHUNT_DB", "mileshunt.db"))

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_email TEXT,
    origin TEXT NOT NULL,
    trip_type TEXT NOT NULL,
    cabin TEXT NOT NULL,
    outbound_date TEXT NOT NULL,
    return_date TEXT,
    groups TEXT,
    destinations_searched INTEGER DEFAULT 0,
    results_found INTEGER DEFAULT 0,
    best_per_xp REAL,
    duration_ms INTEGER DEFAULT 0,
    ip_address TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS best_deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    found_at TEXT NOT NULL,
    found_by TEXT,
    route TEXT NOT NULL,
    return_route TEXT,
    trip_type TEXT NOT NULL,
    price REAL NOT NULL,
    xp_total INTEGER NOT NULL,
    per_xp REAL NOT NULL,
    cabin TEXT NOT NULL,
    airlines TEXT,
    segments INTEGER,
    rating TEXT,
    outbound_date TEXT
);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript(_CREATE_SQL)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


# ── Users ───────────────────────────────────────────────────

def create_user(email: str, name: str, password: str, is_admin: bool = False) -> int:
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, name, password_hash, salt, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (email.lower(), name, pw_hash, salt, int(is_admin), datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def verify_user(email: str, password: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        if not row:
            return None
        pw_hash = _hash_password(password, row["salt"])
        if pw_hash != row["password_hash"]:
            return None
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.utcnow().isoformat(), row["id"]))
        return dict(row)


def list_users() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, email, name, is_admin, created_at, last_login FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def delete_user(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ── Sessions ────────────────────────────────────────────────

def create_session(user_id: int, hours: int = 720) -> str:  # 30 days
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires = now + timedelta(hours=hours)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now.isoformat(), expires.isoformat()),
        )
    return token


def get_session_user(token: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ? AND s.expires_at > ?",
            (token, datetime.utcnow().isoformat()),
        ).fetchone()
        return dict(row) if row else None


def delete_session(token: str):
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


# ── Search Logs ─────────────────────────────────────────────

def log_search(
    origin: str, trip_type: str, cabin: str, outbound_date: str,
    return_date: str | None, groups: str | None,
    destinations_searched: int, results_found: int,
    best_per_xp: float | None, duration_ms: int,
    user_email: str | None = None, ip_address: str | None = None,
):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO search_log
               (timestamp, user_email, origin, trip_type, cabin, outbound_date, return_date,
                groups, destinations_searched, results_found, best_per_xp, duration_ms, ip_address)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), user_email, origin, trip_type, cabin,
             outbound_date, return_date, groups, destinations_searched,
             results_found, best_per_xp, duration_ms, ip_address),
        )


def save_best_deals(deals: list[dict], user_email: str | None, cabin: str, outbound_date: str):
    """Save the top deals from a search to the all-time leaderboard."""
    with get_db() as conn:
        for d in deals[:20]:  # save top 20 from each search
            if d.get("xp_total", 0) <= 0 or d.get("price", 0) <= 0:
                continue
            conn.execute(
                """INSERT INTO best_deals
                   (found_at, found_by, route, return_route, trip_type, price, xp_total,
                    per_xp, cabin, airlines, segments, rating, outbound_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), user_email,
                 d.get("route", ""), d.get("return_route"),
                 d.get("trip_type", "oneway"), d.get("price", 0),
                 d.get("xp_total", 0), d.get("per_xp", 999),
                 cabin, ",".join(d.get("airlines", [])),
                 d.get("total_segments", 0), d.get("rating", ""),
                 outbound_date),
            )


def get_best_deals(limit: int = 10) -> list[dict]:
    """Return the all-time best deals by per_xp, deduplicated by route."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM best_deals
               WHERE per_xp < 999
               ORDER BY per_xp ASC
               LIMIT ?""",
            (limit * 3,),  # fetch extra to allow dedup
        ).fetchall()

    # Deduplicate by route
    seen: set[str] = set()
    result: list[dict] = []
    for r in rows:
        d = dict(r)
        key = f"{d['route']}_{d.get('return_route', '')}"
        if key in seen:
            continue
        seen.add(key)
        result.append(d)
        if len(result) >= limit:
            break
    return result


def get_search_stats() -> dict:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM search_log").fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM search_log WHERE timestamp >= date('now')"
        ).fetchone()[0]
        avg_results = conn.execute(
            "SELECT AVG(results_found) FROM search_log WHERE results_found > 0"
        ).fetchone()[0]
        top_origins = conn.execute(
            "SELECT origin, COUNT(*) as cnt FROM search_log GROUP BY origin ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        top_cabins = conn.execute(
            "SELECT cabin, COUNT(*) as cnt FROM search_log GROUP BY cabin ORDER BY cnt DESC"
        ).fetchall()
        recent = conn.execute(
            "SELECT * FROM search_log ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()

    return {
        "total_searches": total,
        "searches_today": today,
        "avg_results": round(avg_results or 0, 1),
        "top_origins": [{"origin": r[0], "count": r[1]} for r in top_origins],
        "top_cabins": [{"cabin": r[0], "count": r[1]} for r in top_cabins],
        "recent": [dict(r) for r in recent],
    }
