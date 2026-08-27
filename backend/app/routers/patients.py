from fastapi import APIRouter

from app.services.patient_service import (
    get_patient_count,
    get_patient_count_by_condition,
    get_billing_summary
)

router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


@router.get("/count")
def patient_count():
    return {
        "patient_count": get_patient_count()
    }


@router.get("/conditions")
def patient_conditions():
    return {
        "patients_by_condition": get_patient_count_by_condition()
    }


@router.get("/billing")
def billing_summary():
    billing = get_billing_summary()

    return {
        "average": billing[0],
        "minimum": billing[1],
        "maximum": billing[2]
    }