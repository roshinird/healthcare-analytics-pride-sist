"""
Healthcare Analytics database seed / ingestion pipeline.

Dev B responsibility:
- Read the raw Kaggle Healthcare Dataset.
- Transform the source dataset into the frozen application schema.
- Rebuild the SQLite database reproducibly.
- Preserve invalid-billing encounters with billing_is_valid = 0.
- Populate ref_medical_condition and encounters.
- Validate the resulting database.

Run from backend/ with:

    python -m app.seed

The pipeline is intentionally deterministic and does not modify the
raw CSV.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from app.database import DATABASE_PATH, SCHEMA_SQL, get_connection


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = BACKEND_DIR / "data" / "raw" / "healthcare_dataset.csv"


# ---------------------------------------------------------------------------
# Source contract
# ---------------------------------------------------------------------------

REQUIRED_SOURCE_COLUMNS = {
    "Name",
    "Age",
    "Gender",
    "Blood Type",
    "Medical Condition",
    "Date of Admission",
    "Doctor",
    "Hospital",
    "Insurance Provider",
    "Billing Amount",
    "Room Number",
    "Admission Type",
    "Discharge Date",
    "Medication",
    "Test Results",
}


# ---------------------------------------------------------------------------
# Curated medical-condition reference data
# ---------------------------------------------------------------------------
#
# This is the one analyst-added classification permitted by the frozen
# architecture. The condition_name values come from the source dataset.
#
# Chronic conditions:
#   Arthritis, Asthma, Cancer, Diabetes, Hypertension, Obesity
#
# The source dataset contains these six medical conditions.
# ---------------------------------------------------------------------------

CONDITION_CATEGORIES = {
    "Arthritis": "Chronic",
    "Asthma": "Chronic",
    "Cancer": "Acute",
    "Diabetes": "Chronic",
    "Hypertension": "Chronic",
    "Obesity": "Chronic",
}


# ---------------------------------------------------------------------------
# Transformation helpers
# ---------------------------------------------------------------------------

def validate_source_columns(df: pd.DataFrame) -> None:
    """Ensure the raw CSV matches the expected Kaggle source structure."""

    actual = set(df.columns)

    missing = REQUIRED_SOURCE_COLUMNS - actual

    if missing:
        raise ValueError(
            "Raw dataset is missing required columns: "
            + ", ".join(sorted(missing))
        )


def clean_string_series(series: pd.Series) -> pd.Series:
    """Strip surrounding whitespace without changing legitimate values."""

    return series.astype("string").str.strip()


def transform_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform the raw source dataframe into the frozen encounters contract.

    Rows with invalid dates or invalid structural fields are rejected because
    they cannot satisfy the database constraints. Negative billing is NOT
    rejected: it is retained and flagged through billing_is_valid.
    """

    validate_source_columns(df)

    working = df.copy()

    # ---------------------------------------------------------------
    # Normalize retained source columns.
    # ---------------------------------------------------------------

    working["Age"] = pd.to_numeric(working["Age"], errors="coerce")

    for column in [
        "Gender",
        "Blood Type",
        "Medical Condition",
        "Hospital",
        "Insurance Provider",
        "Admission Type",
        "Test Results",
    ]:
        working[column] = clean_string_series(working[column])

    working["Billing Amount"] = pd.to_numeric(
        working["Billing Amount"],
        errors="coerce",
    )

    working["Date of Admission"] = pd.to_datetime(
        working["Date of Admission"],
        errors="coerce",
    )

    working["Discharge Date"] = pd.to_datetime(
        working["Discharge Date"],
        errors="coerce",
    )

    # ---------------------------------------------------------------
    # Structural validation.
    # ---------------------------------------------------------------

    required_for_database = [
        "Age",
        "Gender",
        "Blood Type",
        "Medical Condition",
        "Hospital",
        "Insurance Provider",
        "Admission Type",
        "Test Results",
        "Billing Amount",
        "Date of Admission",
        "Discharge Date",
    ]

    before_structural = len(working)

    working = working.dropna(subset=required_for_database).copy()

    dropped_structural = before_structural - len(working)

    # ---------------------------------------------------------------
    # Validate categorical values against the frozen schema.
    # ---------------------------------------------------------------

    valid_gender = {"Male", "Female"}
    valid_admission_type = {"Emergency", "Urgent", "Elective"}
    valid_test_results = {"Normal", "Abnormal", "Inconclusive"}

    valid_mask = (
        working["Gender"].isin(valid_gender)
        & working["Admission Type"].isin(valid_admission_type)
        & working["Test Results"].isin(valid_test_results)
        & working["Age"].between(0, 120)
    )

    dropped_constraint = (~valid_mask).sum()

    working = working.loc[valid_mask].copy()

    # ---------------------------------------------------------------
    # Date validation and derived length of stay.
    # ---------------------------------------------------------------

    valid_dates = working["Discharge Date"] >= working["Date of Admission"]

    dropped_date_rows = (~valid_dates).sum()

    working = working.loc[valid_dates].copy()

    working["length_of_stay_days"] = (
        working["Discharge Date"] - working["Date of Admission"]
    ).dt.days

    # The frozen schema requires LOS > 0.
    valid_los = working["length_of_stay_days"] > 0

    dropped_los_rows = (~valid_los).sum()

    working = working.loc[valid_los].copy()

    # ---------------------------------------------------------------
    # Billing quality flag.
    # ---------------------------------------------------------------
    #
    # Negative billing is intentionally preserved.
    # ---------------------------------------------------------------

    working["billing_is_valid"] = (
        working["Billing Amount"] >= 0
    ).astype(int)

    invalid_billing_count = int(
        (working["billing_is_valid"] == 0).sum()
    )

    # ---------------------------------------------------------------
    # Condition reference validation.
    # ---------------------------------------------------------------

    unknown_conditions = sorted(
        set(working["Medical Condition"].dropna())
        - set(CONDITION_CATEGORIES)
    )

    if unknown_conditions:
        raise ValueError(
            "Unexpected medical conditions found in source dataset: "
            + ", ".join(unknown_conditions)
        )

    # ---------------------------------------------------------------
    # Build final encounters dataframe.
    # ---------------------------------------------------------------

    transformed = pd.DataFrame(
        {
            "age": working["Age"].astype(int),
            "gender": working["Gender"].astype(str),
            "blood_type": working["Blood Type"].astype(str),
            "condition_name": working["Medical Condition"].astype(str),
            "hospital_name": working["Hospital"].astype(str),
            "insurance_provider": working["Insurance Provider"].astype(str),
            "admission_date": working["Date of Admission"].dt.strftime(
                "%Y-%m-%d"
            ),
            "discharge_date": working["Discharge Date"].dt.strftime(
                "%Y-%m-%d"
            ),
            "length_of_stay_days": working["length_of_stay_days"].astype(int),
            "admission_type": working["Admission Type"].astype(str),
            "billing_amount": working["Billing Amount"].astype(float),
            "billing_is_valid": working["billing_is_valid"].astype(int),
            "test_result": working["Test Results"].astype(str),
        }
    )

    transformed.attrs["dropped_structural"] = int(dropped_structural)
    transformed.attrs["dropped_constraint"] = int(dropped_constraint)
    transformed.attrs["dropped_date_rows"] = int(dropped_date_rows)
    transformed.attrs["dropped_los_rows"] = int(dropped_los_rows)
    transformed.attrs["invalid_billing_count"] = invalid_billing_count

    return transformed


# ---------------------------------------------------------------------------
# Database rebuild
# ---------------------------------------------------------------------------

def rebuild_database(
    transformed: pd.DataFrame,
    database_path: Path | str = DATABASE_PATH,
) -> None:
    """
    Rebuild the SQLite database from the transformed dataframe.

    The database is deleted first so repeated seed runs always produce a
    clean, reproducible result.
    """

    database_path = Path(database_path)

    database_path.parent.mkdir(parents=True, exist_ok=True)

    # Close/delete the previous database completely.
    if database_path.exists():
        database_path.unlink()

    connection = get_connection(database_path)

    try:
        # Create the frozen schema.
        connection.executescript(SCHEMA_SQL)

        # -----------------------------------------------------------
        # Populate reference table.
        # -----------------------------------------------------------

        condition_rows = [
            (condition_name, category)
            for condition_name, category in sorted(
                CONDITION_CATEGORIES.items()
            )
        ]

        connection.executemany(
            """
            INSERT INTO ref_medical_condition (
                condition_name,
                condition_category
            )
            VALUES (?, ?)
            """,
            condition_rows,
        )

        # -----------------------------------------------------------
        # Resolve condition names → generated condition IDs.
        # -----------------------------------------------------------

        condition_id_by_name = {
            row["condition_name"]: row["condition_id"]
            for row in connection.execute(
                """
                SELECT condition_id, condition_name
                FROM ref_medical_condition
                """
            )
        }

        # -----------------------------------------------------------
        # Insert encounters.
        # -----------------------------------------------------------

        encounter_rows = [
            (
                int(row.age),
                row.gender,
                row.blood_type,
                condition_id_by_name[row.condition_name],
                row.hospital_name,
                row.insurance_provider,
                row.admission_date,
                row.discharge_date,
                int(row.length_of_stay_days),
                row.admission_type,
                float(row.billing_amount),
                int(row.billing_is_valid),
                row.test_result,
            )
            for row in transformed.itertuples(index=False)
        ]

        connection.executemany(
            """
            INSERT INTO encounters (
                age,
                gender,
                blood_type,
                condition_id,
                hospital_name,
                insurance_provider,
                admission_date,
                discharge_date,
                length_of_stay_days,
                admission_type,
                billing_amount,
                billing_is_valid,
                test_result
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            encounter_rows,
        )

        connection.commit()

        # -----------------------------------------------------------
        # Integrity verification.
        # -----------------------------------------------------------

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            raise RuntimeError(
                f"Foreign-key integrity check failed: {foreign_key_errors}"
            )

        encounter_count = connection.execute(
            "SELECT COUNT(*) FROM encounters"
        ).fetchone()[0]

        condition_count = connection.execute(
            "SELECT COUNT(*) FROM ref_medical_condition"
        ).fetchone()[0]

        view_count = connection.execute(
            "SELECT COUNT(*) FROM vw_encounter_enriched"
        ).fetchone()[0]

        if encounter_count != len(transformed):
            raise RuntimeError(
                "Encounter row-count mismatch: "
                f"database={encounter_count}, "
                f"transformed={len(transformed)}"
            )

        if view_count != encounter_count:
            raise RuntimeError(
                "View fan-out / row-count violation: "
                f"encounters={encounter_count}, view={view_count}"
            )

        if condition_count != len(CONDITION_CATEGORIES):
            raise RuntimeError(
                "Unexpected condition reference count: "
                f"{condition_count}"
            )

    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Main seed operation
# ---------------------------------------------------------------------------

def seed_database(
    raw_data_path: Path | str = RAW_DATA_PATH,
    database_path: Path | str = DATABASE_PATH,
) -> dict[str, int | str]:
    """
    Execute the complete ingestion and database-seeding pipeline.
    """

    raw_data_path = Path(raw_data_path)

    if not raw_data_path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: {raw_data_path}"
        )

    print(f"Reading raw dataset: {raw_data_path}")

    source_df = pd.read_csv(raw_data_path)

    print(
        f"Source rows: {len(source_df):,} | "
        f"Source columns: {len(source_df.columns)}"
    )

    transformed = transform_dataset(source_df)

    rebuild_database(transformed, database_path)

    summary = {
        "source_rows": int(len(source_df)),
        "seeded_encounters": int(len(transformed)),
        "condition_count": len(CONDITION_CATEGORIES),
        "invalid_billing_rows": int(
            transformed.attrs["invalid_billing_count"]
        ),
        "dropped_structural_rows": int(
            transformed.attrs["dropped_structural"]
        ),
        "dropped_constraint_rows": int(
            transformed.attrs["dropped_constraint"]
        ),
        "dropped_date_rows": int(
            transformed.attrs["dropped_date_rows"]
        ),
        "dropped_los_rows": int(
            transformed.attrs["dropped_los_rows"]
        ),
        "database": str(Path(database_path).resolve()),
    }

    return summary


def main() -> None:
    """CLI entry point."""

    print("=" * 72)
    print("HEALTHCARE ANALYTICS — DATABASE SEED")
    print("=" * 72)

    summary = seed_database()

    print()
    print("Seed completed successfully.")
    print("-" * 72)
    print(f"Source rows:             {summary['source_rows']:,}")
    print(f"Seeded encounters:       {summary['seeded_encounters']:,}")
    print(f"Medical conditions:      {summary['condition_count']}")
    print(f"Invalid billing rows:    {summary['invalid_billing_rows']:,}")
    print(f"Structural drops:        {summary['dropped_structural_rows']:,}")
    print(f"Constraint drops:        {summary['dropped_constraint_rows']:,}")
    print(f"Invalid-date drops:      {summary['dropped_date_rows']:,}")
    print(f"Invalid-LOS drops:       {summary['dropped_los_rows']:,}")
    print(f"Database:                {summary['database']}")
    print("=" * 72)


if __name__ == "__main__":
    main()
