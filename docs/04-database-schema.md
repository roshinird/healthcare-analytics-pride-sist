# 04 — Database Schema

**Status: 🔒 FROZEN AND AUTHORITATIVE.**
No AI coding agent may add tables, columns, or relationships beyond what is defined here without explicit written developer approval. If an agent believes a change is needed, it must stop and document the proposed change rather than implementing it silently (see `14-ai-agent-instructions.md`).

---

## 1. Database Engine

SQLite. Single file: `backend/data/healthcare.db`, built by `backend/app/seed.py` from the cleaned dataset. Rebuilt at container start (see `11-deployment.md`) — never assumed to persist across redeploys.

## 2. Model Description

**"Core encounter table + medical-condition reference table."**
This is explicitly **not** a star schema, dimensional warehouse, or multi-dimension OLTP model. It is one fact/core table and exactly one lookup table, joined by a single foreign key.

## 3. Exact DDL

```sql
CREATE TABLE ref_medical_condition (
    condition_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_name   TEXT NOT NULL UNIQUE,
    condition_category TEXT NOT NULL CHECK (condition_category IN ('Chronic', 'Acute'))
);

CREATE TABLE encounters (
    encounter_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    age                 INTEGER NOT NULL CHECK (age >= 0 AND age <= 120),
    gender              TEXT NOT NULL CHECK (gender IN ('Male', 'Female')),
    blood_type          TEXT NOT NULL,
    condition_id        INTEGER NOT NULL REFERENCES ref_medical_condition(condition_id),
    hospital_name       TEXT NOT NULL,
    insurance_provider  TEXT NOT NULL,
    admission_date      TEXT NOT NULL,          -- ISO 'YYYY-MM-DD'
    discharge_date      TEXT NOT NULL,          -- ISO 'YYYY-MM-DD'
    length_of_stay_days INTEGER NOT NULL CHECK (length_of_stay_days > 0),
    admission_type      TEXT NOT NULL CHECK (admission_type IN ('Emergency', 'Urgent', 'Elective')),
    billing_amount      REAL NOT NULL,
    billing_is_valid    INTEGER NOT NULL CHECK (billing_is_valid IN (0, 1)),  -- 0 = negative/invalid billing
    test_result         TEXT NOT NULL CHECK (test_result IN ('Normal', 'Abnormal', 'Inconclusive'))
);

CREATE INDEX idx_encounters_condition_id       ON encounters(condition_id);
CREATE INDEX idx_encounters_admission_date     ON encounters(admission_date);
CREATE INDEX idx_encounters_hospital_name      ON encounters(hospital_name);
CREATE INDEX idx_encounters_insurance_provider ON encounters(insurance_provider);
CREATE INDEX idx_encounters_admission_type     ON encounters(admission_type);

CREATE VIEW vw_encounter_enriched AS
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
FROM encounters e
JOIN ref_medical_condition c ON e.condition_id = c.condition_id;
```

## 4. Table Purpose Summary

| Table | Grain | Row count (approx) |
|---|---|---|
| `encounters` | One row per admission/encounter | ~55,000 (minus rows excluded for invalid LOS during ingestion) |
| `ref_medical_condition` | One row per distinct medical condition | 6 |

## 5. Fan-Out / Aggregation Correctness Rule — NON-NEGOTIABLE

There is exactly **one** dimension/reference table (`ref_medical_condition`), and its relationship to `encounters` is strictly **many-to-one** (`encounters.condition_id → ref_medical_condition.condition_id`). Because of this:

> **Any query joining `encounters` to `ref_medical_condition` returns exactly one reference row per encounter row. `COUNT`, `SUM`, and `AVG` over `encounters` can never be inflated by this join.**

**Hard rule for all future SQL and schema changes:** no query in this system may JOIN `encounters` to more than one table at a time. If a second reference/lookup table is ever proposed, this fan-out analysis must be re-run and documented before implementation — this requires developer approval, not just an AI agent's judgment call.

## 6. Why Certain Tables Do NOT Exist (explicit record)

| Not built | Why |
|---|---|
| `patients` table | No patient identifier exists in the source data. Building this table would fabricate a real-world entity the data cannot support. See `03-dataset.md` §4. |
| `doctors` table | `Doctor` is a high-cardinality generated free-text field with no meaningful repeat structure — not a stable real-world entity. Normalizing it adds JOIN cost for zero deduplication or analytical benefit. |
| `hospitals` table | Same reasoning as `doctors` — `hospital_name` is kept as a flat text column on `encounters` and aggregated directly via `GROUP BY`, not JOIN. |
| Any `room_number` column/table | No departmental or clinical meaning attaches to room number in this dataset; dropped at ingestion per `03-dataset.md` §5. |
| Any `medication` column/table | Earns no MUST-have analytics question; dropped at ingestion to protect the time budget. |

## 7. Referential Integrity

- `encounters.condition_id` is `NOT NULL` and constrained by `REFERENCES ref_medical_condition(condition_id)`. SQLite foreign keys must be enabled at connection time: `PRAGMA foreign_keys = ON;` (set this in `backend/app/database.py` on every connection — see `07-backend-architecture.md`).
- No `ON DELETE`/`ON UPDATE` cascade rules are needed — `ref_medical_condition` is static reference data, never mutated at runtime (this system has no write endpoints).

## 8. Seed Process (summary — full script responsibility of Dev B)

1. Load and clean the raw CSV per `03-dataset.md` §6.
2. `CREATE` both tables and the view (drop-and-recreate on each run — idempotent).
3. Insert the 6 rows into `ref_medical_condition` first (with `condition_category` mapping documented in the script docstring).
4. Bulk-insert cleaned encounter rows into `encounters`, resolving `condition_id` via a lookup against `ref_medical_condition.condition_name`.
5. Log final row counts and the count of rows excluded for invalid LOS, plus the count of rows flagged `billing_is_valid = 0`.

## 9. Validation Checks (must pass after every seed run — see `13-testing-checklist.md`)

- `SELECT COUNT(*) FROM encounters` returns a plausible value (tens of thousands, not zero, not equal to raw CSV row count if any rows were excluded — difference must match the logged exclusion count).
- `SELECT COUNT(*) FROM ref_medical_condition` returns exactly 6.
- No `NULL` values in any `NOT NULL` column.
- No `encounters.condition_id` value exists that is absent from `ref_medical_condition.condition_id` (should be structurally impossible given the FK constraint, but verify at seed time).
- `SELECT COUNT(*) FROM encounters WHERE billing_is_valid = 0` matches the logged negative-billing count.
- `SELECT COUNT(*) FROM vw_encounter_enriched` equals `SELECT COUNT(*) FROM encounters` exactly (confirms the view introduces no fan-out).
