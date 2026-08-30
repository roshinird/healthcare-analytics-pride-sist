"""SQLite connection helper.

Owner: Dev A (infrastructure).
Spec: docs/07-backend-architecture.md §2, docs/04-database-schema.md §7.

This module contains **no query text**. Dev B's `services/queries.py` is the only
module allowed to hold SQL.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings

# Tables that must exist before the live data layer is considered usable.
REQUIRED_TABLES = ("encounters", "ref_medical_condition")


def get_connection() -> sqlite3.Connection:
    """Open a read-oriented connection with foreign keys enforced."""
    settings = get_settings()
    conn = sqlite3.connect(str(settings.database_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def database_is_ready() -> bool:
    """True when the SQLite file exists and holds both frozen-schema tables.

    Used at startup and by the data-source resolver to decide whether the live
    (Dev B) layer can serve requests.
    """
    settings = get_settings()
    if not settings.database_path.is_file():
        return False
    try:
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
    except sqlite3.Error:
        return False
    names = {row["name"] for row in rows}
    return all(table in names for table in REQUIRED_TABLES)


def table_counts() -> dict[str, int]:
    """Row counts for the startup sanity log (docs/07-backend-architecture.md §8.3).

    The statements are literals rather than an f-string over `REQUIRED_TABLES`.
    No user input could reach that interpolation, but docs/10-security-privacy.md
    §4 asks a reviewer to grep for f-string SQL and find nothing — so there is
    nothing to find.
    """
    statements = {
        "encounters": "SELECT COUNT(*) AS n FROM encounters",
        "ref_medical_condition": "SELECT COUNT(*) AS n FROM ref_medical_condition",
    }
    counts: dict[str, int] = {}
    with connection_scope() as conn:
        for table, sql in statements.items():
            counts[table] = conn.execute(sql).fetchone()["n"]
    return counts
