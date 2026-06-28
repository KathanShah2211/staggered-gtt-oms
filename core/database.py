"""
core/database.py
================
SQLite database layer using Python's built-in sqlite3.

Tables
------
app_config   — key/value store for salt, tokens, and settings.
clients      — encrypted API credentials per ICICI Direct account.
order_logs   — immutable audit trail of every GTT order placement attempt.

All writes use parameterized queries (zero f-string SQL).
"""

import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

# Resolve data directory relative to this file's parent-parent (project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "oms.db"


# -----------------------------------------------------------------
# Internal connection factory
# -----------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    """Open (or create) the SQLite DB and return a connection with row_factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# -----------------------------------------------------------------
# Schema init
# -----------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they do not already exist."""
    conn = _get_conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name   TEXT    NOT NULL UNIQUE,
                app_key_enc   TEXT    NOT NULL,
                secret_key_enc TEXT   NOT NULL,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name   TEXT,
                stock_code    TEXT,
                batch_number  INTEGER,
                trigger_price REAL,
                quantity      INTEGER,
                status        TEXT,
                response_json TEXT,
                timestamp     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
    finally:
        conn.close()


# -----------------------------------------------------------------
# app_config helpers
# -----------------------------------------------------------------

def get_config(key: str) -> str | None:
    """Retrieve a value from app_config by key. Returns None if not found."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM app_config WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_config(key: str, value: str) -> None:
    """Insert or replace a key/value pair in app_config."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------------------------------------------------
# Client management
# -----------------------------------------------------------------

def add_client(client_name: str, app_key: str, secret_key: str) -> None:
    """
    Encrypt and persist a new client's API credentials.
    Raises sqlite3.IntegrityError if client_name already exists.
    """
    from core.encryption import encrypt

    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO clients (client_name, app_key_enc, secret_key_enc)
            VALUES (?, ?, ?)
            """,
            (client_name, encrypt(app_key), encrypt(secret_key)),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_clients() -> list[dict]:
    """
    Return a list of dicts with: id, client_name, created_at.
    API keys are NOT decrypted here — call decrypt() explicitly when needed.
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, client_name, created_at FROM clients ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_client_keys(client_name: str) -> tuple[str, str]:
    """
    Return the decrypted (app_key, secret_key) for the given client.
    Raises ValueError if client not found.
    """
    from core.encryption import decrypt

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT app_key_enc, secret_key_enc FROM clients WHERE client_name = ?",
            (client_name,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Client '{client_name}' not found in database.")
        return decrypt(row["app_key_enc"]), decrypt(row["secret_key_enc"])
    finally:
        conn.close()


def delete_client(client_name: str) -> None:
    """Remove a client record by name."""
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM clients WHERE client_name = ?", (client_name,)
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------------------------------------------------
# Order logging
# -----------------------------------------------------------------

def log_order(
    client_name: str,
    stock_code: str,
    batch_number: int,
    trigger_price: float,
    quantity: int,
    status: str,
    response_data: dict | str | None = None,
) -> None:
    """
    Append a GTT order placement result to order_logs.

    Parameters
    ----------
    status        : 'SUCCESS' | 'FAILED' | 'SKIPPED'
    response_data : raw API response dict or error string; serialized to JSON.
    """
    if isinstance(response_data, dict):
        response_json = json.dumps(response_data)
    elif response_data is not None:
        response_json = str(response_data)
    else:
        response_json = None

    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO order_logs
                (client_name, stock_code, batch_number, trigger_price,
                 quantity, status, response_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_name,
                stock_code,
                batch_number,
                trigger_price,
                quantity,
                status,
                response_json,
                datetime.now().isoformat(sep=" ", timespec="seconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_order_logs(
    client_name: str | None = None,
    date_str: str | None = None,
) -> list[dict]:
    """
    Query order_logs with optional filters.

    Parameters
    ----------
    client_name : filter by client (None = all clients)
    date_str    : ISO date string 'YYYY-MM-DD' to filter by day (None = all dates)
    """
    conditions = []
    params: list = []

    if client_name:
        conditions.append("client_name = ?")
        params.append(client_name)

    if date_str:
        conditions.append("DATE(timestamp) = ?")
        params.append(date_str)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT id, client_name, stock_code, batch_number, trigger_price,
               quantity, status, response_json, timestamp
        FROM order_logs
        {where_clause}
        ORDER BY timestamp DESC
    """

    conn = _get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_distinct_clients_from_logs() -> list[str]:
    """Return distinct client names that appear in order_logs (for log filter dropdown)."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT client_name FROM order_logs ORDER BY client_name"
        ).fetchall()
        return [r["client_name"] for r in rows if r["client_name"]]
    finally:
        conn.close()
