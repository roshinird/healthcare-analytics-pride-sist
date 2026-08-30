"""
SQLite database connection and schema management.

Dev B responsibility:
- Provide the single SQLite connection helper.
- Enable foreign-key enforcement on every connection.
- Apply the frozen Healthcare Analytics schema.
- Keep all SQL schema definitions in this module.

The schema is intentionally limited to:
    1. ref_medical_condition
    2. encounters
    3. vw_encounter_enriched

No additional tables, dimensions, or relationships are permitted.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Database location
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BACKEND_DIR / "data" / "database" / "healthcare.db"


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

def get_connection(
    database_path: Path | str = DATABASE_PATH,
) -> sqlite3.Connection:
    """
    Open a SQLite connection with the required database settings.

    Every connection:
    - enables foreign-key enforcement;
    - returns sqlite3.Row objects;
    - uses a reasonable timeout for local development.
    """

    path = Path(database_path)

    # Ensure the database directory exists before connecting.
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        path,
        timeout=30,
    )

    # Required by the frozen architecture.
    connection.execute("PRAGMA foreign_keys = ON;")

    # Allows callers to access columns by name as well as by index.
    connection.row_factory = sqlite3.Row

    return connection


# ---------------------------------------------------------------------------
# Schema initialization
# ---------------------------------------------------------------------------

def initialize_database(
    database_path: Path | str = DATABASE_PATH,
) -> None:
    """
    Create the frozen database schema if it does not already exist.

    This function does not insert data.

    Data loading belongs exclusively to seed.py.
    """

    connection = get_connection(database_path)

    try:
        connection.executescript(SCHEMA_SQL)
        connection.commit()
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Development/testing helper
# ---------------------------------------------------------------------------

def get_db_connection() -> Iterator[sqlite3.Connection]:
    """
    Context-manager-friendly database connection generator.

    Useful later for FastAPI dependency injection and tests.
    """

    connection = get_connection()

    try:
        yield connection
    finally:
        connection.close()