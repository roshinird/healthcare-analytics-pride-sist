"""SQLite connection and frozen-schema management.

Integrated responsibility:
- Dev A infrastructure/configuration and database readiness helpers.
- Dev B frozen SQLite schema and schema initialization.

The schema is intentionally limited to:
    1. ref_medical_condition
    2. encounters
    3. vw_encounter_enriched

Query/analytics SQL belongs in the query layer, not here.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings

DATABASE_PATH = get_settings().database_path
# ---------------------------------------------------------------------------
# Required database objects
# ---------------------------------------------------------------------------

REQUIRED_TABLES = (
    "encounters",
    "ref_medical_condition",
)


# ---------------------------------------------------------------------------
# Frozen schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ref_medical_condition (
    condition_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_name     TEXT NOT NULL UNIQUE,
    condition_category TEXT NOT NULL
        CHECK (condition_category IN ('Chronic', 'Acute'))
);

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    age                 INTEGER NOT NULL
        CHECK (age >= 0 AND age <= 120),
    gender              TEXT NOT NULL
        CHECK (gender IN ('Male', 'Female')),
    blood_type          TEXT NOT NULL,
    condition_id        INTEGER NOT NULL
        REFERENCES ref_medical_condition(condition_id),
    hospital_name       TEXT NOT NULL,
    insurance_provider  TEXT NOT NULL,
    admission_date      TEXT NOT NULL,
    discharge_date      TEXT NOT NULL,
    length_of_stay_days INTEGER NOT NULL
        CHECK (length_of_stay_days > 0),
    admission_type      TEXT NOT NULL
        CHECK (admission_type IN ('Emergency', 'Urgent', 'Elective')),
    billing_amount      REAL NOT NULL,
    billing_is_valid    INTEGER NOT NULL
        CHECK (billing_is_valid IN (0, 1)),
    test_result         TEXT NOT NULL
        CHECK (test_result IN ('Normal', 'Abnormal', 'Inconclusive'))
);

CREATE INDEX IF NOT EXISTS idx_encounters_condition_id
    ON encounters(condition_id);

CREATE INDEX IF NOT EXISTS idx_encounters_admission_date
    ON encounters(admission_date);

CREATE INDEX IF NOT EXISTS idx_encounters_hospital_name
    ON encounters(hospital_name);

CREATE INDEX IF NOT EXISTS idx_encounters_insurance_provider
    ON encounters(insurance_provider);

CREATE INDEX IF NOT EXISTS idx_encounters_admission_type
    ON encounters(admission_type);

CREATE VIEW IF NOT EXISTS vw_encounter_enriched AS
SELECT
    e.encounter_id,
    e.age,
    e.gender,
    e.blood_type,
    e.hospital_name,
    e.insurance_provider,
    e.admission_date,
    e.discharge_date,
    e.length_of_stay_days,
    e.admission_type,
    e.billing_amount,
    e.billing_is_valid,
    e.test_result,
    c.condition_id,
    c.condition_name,
    c.condition_category
FROM encounters AS e
JOIN ref_medical_condition AS c
    ON e.condition_id = c.condition_id;
"""


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_connection(database_path=None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enforced.

    If database_path is provided, connect to that path directly.
    Otherwise, use the configured database path from application settings.
    """

    if database_path is None:
        settings = get_settings()
        database_path = settings.database_path

    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(database_path),
        timeout=30,
    )

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


# ---------------------------------------------------------------------------
# Context-managed connection
# ---------------------------------------------------------------------------

@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    """Provide a database connection that is always closed."""

    conn = get_connection()

    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialization
# ---------------------------------------------------------------------------

def initialize_database() -> None:
    """Create the frozen database schema if it does not already exist.

    This function creates tables, indexes, and the enriched encounter view.
    It does not insert data.

    Data loading belongs exclusively to seed.py.
    """

    with connection_scope() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


# ---------------------------------------------------------------------------
# Database readiness
# ---------------------------------------------------------------------------

def database_is_ready() -> bool:
    """Return True when the SQLite database contains the required tables.

    Used at startup and by the data-source resolver to determine whether
    the live database layer can serve requests.
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


# ---------------------------------------------------------------------------
# Table counts
# ---------------------------------------------------------------------------

def table_counts() -> dict[str, int]:
    """Return row counts for required database tables."""

    statements = {
        "encounters": "SELECT COUNT(*) AS n FROM encounters",
        "ref_medical_condition": (
            "SELECT COUNT(*) AS n FROM ref_medical_condition"
        ),
    }

    counts: dict[str, int] = {}

    with connection_scope() as conn:
        for table, sql in statements.items():
            counts[table] = conn.execute(sql).fetchone()["n"]

    return counts


# ---------------------------------------------------------------------------
# Compatibility helper
# ---------------------------------------------------------------------------

def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Yield a database connection for dependency injection/tests."""

    conn = get_connection()

    try:
        yield conn
    finally:
        conn.close()