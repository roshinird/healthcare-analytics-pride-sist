"""Error envelope and exception handlers.

Owner: Dev A.
Spec: docs/06-api-contract.md §1/§6 (FROZEN), docs/10-security-privacy.md §1.6.

Hard rule: a client never receives a traceback, a raw exception string, a SQL
fragment, or a file path. Those go to the server log only.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("healthcare_analytics")

VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"
NOT_FOUND = "NOT_FOUND"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

GENERIC_INTERNAL_MESSAGE = "An unexpected error occurred."


def error_payload(code: str, message: str) -> dict:
    """The frozen error envelope."""
    return {"error": {"code": code, "message": message}}


def error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_payload(code, message))


class ApiError(Exception):
    """Raised inside the app when a specific, client-safe error must be returned."""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _first_validation_message(exc: RequestValidationError) -> str:
    """Turn FastAPI's structured error list into one client-safe sentence."""
    for err in exc.errors():
        message = str(err.get("msg", "")).removeprefix("Value error, ").strip()
        location = [part for part in err.get("loc", ()) if isinstance(part, str)]
        field = location[-1] if location else None
        if message:
            if field and field not in message and field != "body":
                return f"{field}: {message}"
            return message
    return "One or more query parameters are invalid."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(VALIDATION_ERROR, _first_validation_message(exc), 422)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(NOT_FOUND, "The requested resource does not exist.", 404)
        detail = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
        return error_response(
            VALIDATION_ERROR if exc.status_code == 422 else INTERNAL_ERROR,
            detail if exc.status_code < 500 else GENERIC_INTERNAL_MESSAGE,
            exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Full detail server-side only.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(INTERNAL_ERROR, GENERIC_INTERNAL_MESSAGE, 500)
