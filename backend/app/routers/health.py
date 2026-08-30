"""Liveness route.

Owner: Dev A.
Spec: docs/06-api-contract.md §4 (FROZEN).

Also the documented pre-warm target for Render's free tier
(docs/11-deployment.md §9) — deliberately does no database work so a cold
instance answers as fast as it can.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import utc_now_iso
from app.schemas.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse, summary="Liveness check")
def health() -> dict:
    return {"data": {"status": "ok"}, "meta": {"generated_at": utc_now_iso()}}
