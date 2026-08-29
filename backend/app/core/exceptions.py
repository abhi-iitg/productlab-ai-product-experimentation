"""Centralized exception handling for the API boundary.

Unexpected exceptions must never leak internal details (stack traces,
exception messages, file paths) to API clients. They are logged
server-side and translated into a single safe, generic error response.

Predictable domain failures (e.g. a service looking up a missing entity)
are raised as the typed exceptions below and translated into their own
safe, well-formed responses rather than falling through to the generic
500 handler.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised by services when a requested domain entity does not exist."""

    def __init__(self, message: str = "Resource not found.") -> None:
        self.message = message
        super().__init__(message)


class InvalidRequestError(Exception):
    """Raised by services for domain-validated (DB-dependent) request errors.

    Distinct from Pydantic schema validation (structural checks FastAPI
    already turns into its own 422 response): this covers checks that need
    a database lookup, e.g. a project with no usable evidence, evidence IDs
    that don't belong to the project, or a persona context that exceeds the
    deterministic size limit.
    """

    def __init__(self, message: str = "Invalid request.") -> None:
        self.message = message
        super().__init__(message)


class ConflictError(Exception):
    """Raised when a request conflicts with the current state of a resource.

    Covers editing/deleting a non-draft experiment and attempting to execute
    an experiment a second time.
    """

    def __init__(
        self, message: str = "The request conflicts with the current resource state."
    ) -> None:
        self.message = message
        super().__init__(message)


class ProviderConfigurationError(Exception):
    """Raised when the LLM provider is not configured (e.g. no API key)."""

    def __init__(self, message: str = "The AI provider is not configured.") -> None:
        self.message = message
        super().__init__(message)


class ProviderError(Exception):
    """Raised when the LLM provider fails or returns unusable output.

    Covers timeouts, rate limits, status errors, empty output, malformed
    JSON, schema-invalid output, and fabricated evidence references. The
    message shown to clients never includes provider-internal details.
    """

    def __init__(
        self, message: str = "The AI provider was unable to complete the request."
    ) -> None:
        self.message = message
        super().__init__(message)


async def not_found_exception_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message},
    )


async def invalid_request_exception_handler(
    request: Request, exc: InvalidRequestError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.message},
    )


async def conflict_exception_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


async def provider_configuration_exception_handler(
    request: Request, exc: ProviderConfigurationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": exc.message},
    )


async def provider_exception_handler(request: Request, exc: ProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, not_found_exception_handler)
    app.add_exception_handler(InvalidRequestError, invalid_request_exception_handler)
    app.add_exception_handler(ConflictError, conflict_exception_handler)
    app.add_exception_handler(ProviderConfigurationError, provider_configuration_exception_handler)
    app.add_exception_handler(ProviderError, provider_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
