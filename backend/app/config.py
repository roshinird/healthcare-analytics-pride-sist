"""Application configuration.

Owner: Dev A.
Spec: docs/07-backend-architecture.md §5, docs/10-security-privacy.md §1.5.

Every value is read from the environment. Nothing is hardcoded in source, and no
secret is required by this project (there is no paid or authenticated upstream).
`pydantic-settings` is deliberately not used: it is an extra dependency that
would buy nothing over ~30 lines of stdlib code (docs/02-tech-stack.md,
"Dependency Minimization Rule").
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# backend/app/config.py -> backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DATABASE_PATH = "./data/database/healthcare.db"
DEFAULT_CORS_ALLOWED_ORIGIN = "http://localhost:5173"
DEFAULT_ENVIRONMENT = "development"


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader. Existing environment variables always win.

    Avoids adding python-dotenv for a five-line job.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    database_path: Path
    cors_allowed_origin: str
    environment: str

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        """Allowed origins for CORS.

        Production is restricted to the single named origin (docs/10-security-privacy.md §1.4).
        Local development additionally allows the Vite dev server on either loopback host.
        """
        origin = self.cors_allowed_origin.rstrip("/")
        if self.is_production:
            return [origin]
        return sorted(
            {origin, "http://localhost:5173", "http://127.0.0.1:5173"}
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv(BACKEND_ROOT / ".env")

    raw_db_path = os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH)
    db_path = Path(raw_db_path)
    if not db_path.is_absolute():
        # Resolved against backend/, so the app behaves identically no matter
        # which directory uvicorn was launched from (deployment requirement).
        db_path = (BACKEND_ROOT / db_path).resolve()

    return Settings(
        database_path=db_path,
        cors_allowed_origin=os.environ.get(
            "CORS_ALLOWED_ORIGIN", DEFAULT_CORS_ALLOWED_ORIGIN
        ),
        environment=os.environ.get("ENVIRONMENT", DEFAULT_ENVIRONMENT),
    )
