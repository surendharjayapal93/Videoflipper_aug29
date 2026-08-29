"""Custom application exceptions and their FastAPI exception handlers.

Business logic (services, routers, auth) should raise these exceptions
instead of `fastapi.HTTPException` directly, so error handling stays
consistent across the API. The handlers are registered onto the app
instance in `main.py`.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all custom application exceptions."""

    def __init__(self, message: str, code: str, status_code: int) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    """Raised when a request conflicts with the current state of a resource."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppError):
    """Raised when input data fails business-level validation."""

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, code="VALIDATION_ERROR", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


class UnauthorizedError(AppError):
    """Raised when a request lacks valid authentication/authorization."""

    def __init__(self, message: str = "Not authorized") -> None:
        super().__init__(message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert an `AppError` into a consistent JSON error response."""
    logger.warning("AppError handled: %s (%s) on %s", exc.message, exc.code, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions.

    Logs the full exception server-side and returns a generic 500
    response so internal details are never leaked to clients.
    """
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers onto the FastAPI app."""
    # FastAPI's documented pattern types the handler for the specific
    # exception subclass rather than the generic `Exception` the stub
    # expects; FastAPI dispatches by the registered class at runtime.
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
