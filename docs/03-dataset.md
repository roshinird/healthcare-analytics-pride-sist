# 03 — Dataset

**Status:** Authoritative. Precision matters here — this file resolves any ambiguity about what the data does and does not represent.

---

## 1. Exact Dataset Identity

- **Name:** "Healthcare Dataset"
- **Source:** Kaggle (`prasad22/healthcare-dataset`), a widely mirrored synthetic dataset also republished under other Kaggle usernames and a Hugging Face dataset viewer copy.
- **Nature:** **Entirely synthetic** — patient names, doctor names, hospital names, and admission details are generator-produced, not real-world records.
- **Approximate size:** ~55,500 rows, 15 original columns.
- **License:** Public Kaggle dataset intended for educational/research use. No PHI/PII risk because no real individuals are represented.

## 2. Original Source Columns (as published)

`Name, Age, Gender, Blood Type, Medical Condition, Date of Admission, Doctor, Hospital, Insurance Provider, Billing Amount, Room Number, Admission Type, Discharge Date, Medication, Test Results`

## 3. Verified Semantics

- **Unit of analysis: one row = one independent admission/encounter record.** There is no `patient_id` or equivalent column in the source data.
- `Name` is a generated string (verified sample values include deliberately irregular capitalization, e.g., "Bobby JacksOn", "LesLie TErRy"), confirming it is generator output, not a real or stable identifier.
- Independent third-party analysis of this exact dataset found ~10,977 rows sharing identical Name + Date of Admission + Medical Condition + Insurance Provider but *differing* Age — this is generator noise, **not evidence of repeat patients**. It further confirms Name cannot be trusted as an identity key.
- `Doctor` and `Hospital` are high-cardinality generated free-text strings (e.g., "Sons and Miller", "Kim Inc" as hospital names) with little meaningful repeat structure — they do not represent a small, stable, real-world network of clinicians or facilities.
- `Billing Amount` contains **negative values** in the raw data (observed range approximately -2,008.49 to ~52,800) — this is a genuine data-quality issue, not a "refund" semantic documented anywhere in the source.
- `Room Number` (101–500) is a bed-slot number with no departmental or clinical meaning attached — there is **no department/ward field** in this dataset at all.
- `Medical Condition` is low-cardinality (6 fixed values: e.g., Cancer, Obesity, Diabetes, Asthma, Hypertension, Arthritis) and is the **only** column suitable for genuine relational normalization.
- `Admission Type` (3 values), `Test Results` (3 values), `Insurance Provider` (5 values), `Medication` (5 values) are all low-cardinality categorical fields.

## 4. Absence of Patient Identifier — Hard Rule

**There is no reliable way to determine whether two rows refer to the same real-world patient.** Therefore, this project:
- Does **not** claim to count "unique patients."
- Does **not** implement or imply readmission analytics.
- Does **not** build any patient dimension/entity table.
- Reports all encounter counts as **"Total Encounters"** or **"Total Admission Records"** — never "Total Patients."

This is treated as a correctness rule, not a style preference. See `14-ai-agent-instructions.md` §"Prohibited Assumptions."

## 5. Column Retention Rule

Every retained column must satisfy at least one of: (a) supports an implemented analytics question, (b) supports a dashboard filter, (c) supports a derived metric, (d) supports a data-quality check, (e) is a necessary relational constraint. Columns failing all five are dropped.

### Dropped columns and justification

| Column | Reason dropped |
|---|---|
| `Name` | No identity value (see §4); privacy-minimization discipline — never stored or exposed |
| `Doctor` | High-cardinality generated text with no repeat structure; earns no analytics question, filter, metric, or constraint |
| `Room Number` | No departmental/clinical meaning; earns no analytics question, filter, metric, or constraint |
| `Medication` | No MUST-have question depends on it; dropped to protect the 8–10h budget |

### Retained columns and justification

| Retained column (final name) | Earns its place via |
|---|---|
| `encounter_id` (generated) | Relational constraint — surrogate PK replacing the unreliable Name field |
| `age` | Demographic analytics question (Q6), age-group filter |
| `gender` | Demographic analytics question (Q6), filter |
| `blood_type` | Folded into demographic breakdown question (Q6) |
| `condition_id` (FK, derived) | Relational constraint; drives condition distribution (Q4) and LOS-by-condition (Q5) |
| `hospital_name` | Top-10 hospitals analytics question (Q3) |
| `insurance_provider` | Billing-by-insurance question (Q7), filter |
| `admission_date` | Trend question (Q2), date-function demonstration, filter |
| `discharge_date` | Source for derived `length_of_stay_days` |
| `length_of_stay_days` (derived) | KPI metric, LOS question (Q5) |
| `admission_type` | Billing/test-result questions (Q7, Q9), filter |
| `billing_amount` | Billing questions (Q7, Q8) |
| `billing_is_valid` (derived) | Data-quality check — flags negative billing values |
| `test_result` | Test-result distribution question (Q9) |

## 6. Cleaning & Ingestion Rules

1. Load the raw CSV as-is into a Pandas DataFrame.
2. **Drop** `Name`, `Doctor`, `Room Number`, `Medication` columns immediately — never write these to the database, never log their raw values.
3. Generate a synthetic sequential `encounter_id` (integer, 1-indexed) as the primary key. This replaces any implied identity from `Name`.
4. Parse `Date of Admission` and `Discharge Date` into ISO `DATE` (`YYYY-MM-DD`) values.
5. Derive `length_of_stay_days = discharge_date - admission_date` (integer, days). Flag (log + exclude from row count, do not silently drop) any row where this is `<= 0` — treat as invalid and exclude from the seeded table, recording the excluded count in the ingestion log.
6. Derive `billing_is_valid = (billing_amount >= 0)`. **Do not drop** negative-billing rows — retain them in the table but exclude them from financial aggregate queries (AVG/SUM) by filtering on `billing_is_valid = 1`. Surface the excluded count via the data-quality summary (see `07-backend-architecture.md`).
7. **Duplicate handling:** drop only **exact full-row duplicates** (identical across all retained columns) via a straightforward `DISTINCT`/`drop_duplicates()` pass. **Do not** perform fuzzy/partial matching on Name + Date + Condition + Insurance to infer "the same patient" — that inference is explicitly prohibited (see §4).
8. Standardize categorical casing (Title Case) for `Gender`, `Blood Type`, `Medical Condition`, `Admission Type`, `Test Results`, `Insurance Provider`.
9. Build `ref_medical_condition` from the 6 distinct `Medical Condition` values, adding one curated column `condition_category` (`Chronic` or `Acute`) — **explicitly disclosed as an analyst-added enrichment, not present in the source data.** Suggested mapping (adjust only with a documented rationale): Diabetes → Chronic, Hypertension → Chronic, Arthritis → Chronic, Asthma → Chronic, Obesity → Chronic, Cancer → Acute (or split by treatment phase if the team prefers — mapping must be documented in the seed script's docstring, not silently chosen).
10. Load cleaned data into SQLite per `04-database-schema.md`. Run once; script must be idempotent (re-running does not duplicate rows — truncate-and-reload, not append).

## 7. Prohibited Derivations (repeat, for emphasis)

An AI coding agent implementing this project **must not**:
- Use `Name` (even transiently, even if reintroduced from the raw CSV in a later step) as a join key, grouping key, or identity proxy.
- Infer or display "returning patient" / "readmission" status from any combination of fields.
- Build a `patients` table, `doctors` table, or `hospitals` table with descriptive attributes implying a stable real-world entity.
- Add a `department` field or department-based analytics — this field does not exist in the source data.

## 8. Educational / Privacy Framing (for UI copy and README)

> "This dashboard analyzes a synthetic, publicly available dataset of independent hospital admission records for educational purposes. The dataset contains no real patients, clinicians, or facilities. The system performs descriptive/operational analytics only — it does not diagnose, predict, or recommend clinical treatment."

This exact framing (or a close paraphrase) must appear in the frontend footer and the project README.
