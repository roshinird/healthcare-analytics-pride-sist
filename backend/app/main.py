"""FastAPI application entrypoint.

Owner: Dev A.
Spec: docs/07-backend-architecture.md §1/§2/§6/§8, docs/10-security-privacy.md.

Contains app instantiation, CORS, router mounting, exception handlers and the
startup sanity log — and deliberately no business logic, no SQL and no Pandas.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.database import database_is_ready, table_counts
from app.errors import register_exception_handlers
from app.routers import analytics, health

logger = logging.getLogger("healthcare_analytics")

DESCRIPTION = """
Read-only operational analytics over a **synthetic** hospital admissions dataset.

Each row in the source data is an independent admission/encounter record. The
dataset has no patient identifier, so this API never counts patients, never
implies readmission, and never exposes row-level identity. It performs
descriptive analytics only — it does not diagnose, predict or recommend
treatment.

Contract: `docs/06-api-contract.md` (frozen).
"""


def _configure_logging(environment: str) -> None:
    logging.basicConfig(
        level=logging.INFO if environment == "production" else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.environment)

    logger.info("Starting Healthcare Analytics API v%s (%s)", __version__, settings.environment)
    logger.info("Database path: %s", settings.database_path)

    if database_is_ready():
        try:
            counts = table_counts()
            logger.info(
                "Database ready — encounters=%s, ref_medical_condition=%s",
                counts.get("encounters"),
                counts.get("ref_medical_condition"),
            )
        except Exception:  # noqa: BLE001 - startup logging must never block boot
            logger.exception("Database present but row counts could not be read")
    else:
        # Seeding is Dev B's `python -m app.seed` (docs/11-deployment.md §7).
        logger.warning(
            "No seeded database at %s — the API will serve development fixtures. "
            "Run `python -m app.seed` to build it.",
            settings.database_path,
        )

    yield
    logger.info("Healthcare Analytics API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Healthcare Analytics API",
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
        # No redoc: one docs surface is enough and keeps the free-tier image lean.
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # no cookies, no auth — nothing to send
        allow_methods=["GET", "OPTIONS"],  # read-only API
        allow_headers=["*"],
        max_age=600,
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(analytics.router)

    return app


app = create_app()
