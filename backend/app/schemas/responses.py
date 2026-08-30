"""Response models — a field-for-field mirror of docs/06-api-contract.md (FROZEN).

Owner: Dev A.

These models are attached to the routes as `response_model`, which does three
useful things at once:
  1. enforces the frozen contract at the type level on every response,
  2. guarantees SHOULD-HAVE keys are emitted as `null` rather than omitted,
  3. produces the auto-generated OpenAPI documentation at `/docs`.

Renaming or removing any field here is a contract change and requires explicit
developer approval (docs/14-ai-agent-instructions.md §2).
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_count: int = 0
    generated_at: str
    note: Optional[str] = None


class HealthMeta(BaseModel):
    """`/api/health` carries only `generated_at` in its meta block."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str


class Envelope(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")

    data: T
    meta: Meta


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


# --------------------------------------------------------------------------
# GET /api/health
# --------------------------------------------------------------------------
class HealthData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: HealthData
    meta: HealthMeta


# --------------------------------------------------------------------------
# GET /api/kpis
# --------------------------------------------------------------------------
class KpiData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_encounters: int = 0
    avg_length_of_stay: Optional[float] = None
    avg_billing_amount: Optional[float] = None
    earliest_admission: Optional[str] = None
    latest_admission: Optional[str] = None


KpiResponse = Envelope[KpiData]


# --------------------------------------------------------------------------
# GET /api/analytics/admissions-trend
# --------------------------------------------------------------------------
class TrendPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str
    encounter_count: int
    prev_month_count: Optional[int] = None
    pct_change: Optional[float] = None
    # SHOULD HAVE (docs/05-sql-analytics.md S2): always present, null when unbuilt.
    rolling_avg_3mo: Optional[float] = None


TrendResponse = Envelope[List[TrendPoint]]


# --------------------------------------------------------------------------
# GET /api/analytics/top-hospitals
# --------------------------------------------------------------------------
class HospitalRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hospital_name: str
    encounter_count: int
    volume_rank: int


TopHospitalsResponse = Envelope[List[HospitalRow]]


# --------------------------------------------------------------------------
# GET /api/analytics/conditions
# --------------------------------------------------------------------------
class ConditionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_name: str
    condition_category: str
    encounter_count: int
    percentage_share: float
    avg_length_of_stay: Optional[float] = None


ConditionsResponse = Envelope[List[ConditionRow]]


# --------------------------------------------------------------------------
# GET /api/analytics/demographics
# --------------------------------------------------------------------------
class AgeGroupRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_group: str
    encounter_count: int
    percentage_share: float


class GenderRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gender: str
    encounter_count: int
    percentage_share: float


class BloodTypeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blood_type: str
    encounter_count: int
    percentage_share: float


class DemographicsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_groups: List[AgeGroupRow] = Field(default_factory=list)
    genders: List[GenderRow] = Field(default_factory=list)
    blood_types: List[BloodTypeRow] = Field(default_factory=list)


DemographicsResponse = Envelope[DemographicsData]


# --------------------------------------------------------------------------
# GET /api/analytics/billing
# --------------------------------------------------------------------------
class BillingByInsuranceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insurance_provider: str
    encounter_count: int
    avg_billing: float
    total_billing: float
    pct_of_total_billing: float


class BillingByAdmissionTypeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admission_type: str
    encounter_count: int
    avg_billing: float


class AboveAverageBlock(BaseModel):
    """Q8. Deliberately NOT called "outliers" (docs/05-sql-analytics.md, terminology rule)."""

    model_config = ConfigDict(extra="forbid")

    above_average_count: Optional[int] = None
    overall_avg_billing: Optional[float] = None


class StatisticalOutliersBlock(BaseModel):
    """S1 (SHOULD HAVE, NumPy IQR). Key is always present; values null when unbuilt."""

    model_config = ConfigDict(extra="forbid")

    outlier_count: Optional[int] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class BillingData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    by_insurance_provider: List[BillingByInsuranceRow] = Field(default_factory=list)
    by_admission_type: List[BillingByAdmissionTypeRow] = Field(default_factory=list)
    above_average: AboveAverageBlock = Field(default_factory=AboveAverageBlock)
    statistical_outliers: StatisticalOutliersBlock = Field(
        default_factory=StatisticalOutliersBlock
    )
    excluded_invalid_billing_count: int = 0


BillingResponse = Envelope[BillingData]


# --------------------------------------------------------------------------
# GET /api/analytics/test-results
# --------------------------------------------------------------------------
class TestResultRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admission_type: str
    test_result: str
    encounter_count: int


TestResultsResponse = Envelope[List[TestResultRow]]


__all__ = [
    "Meta",
    "HealthMeta",
    "Envelope",
    "ErrorBody",
    "ErrorResponse",
    "HealthData",
    "HealthResponse",
    "KpiData",
    "KpiResponse",
    "TrendPoint",
    "TrendResponse",
    "HospitalRow",
    "TopHospitalsResponse",
    "ConditionRow",
    "ConditionsResponse",
    "DemographicsData",
    "DemographicsResponse",
    "BillingData",
    "BillingResponse",
    "TestResultRow",
    "TestResultsResponse",
    "Any",
]
