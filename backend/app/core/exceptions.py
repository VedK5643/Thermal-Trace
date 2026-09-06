"""
ThermalTrace custom exceptions and FastAPI exception handlers.
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, resource_id: str):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} with id '{resource_id}' not found")


class DatabaseError(Exception):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "A database error occurred"):
        self.message = message
        super().__init__(message)


async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": str(exc),
        },
    )


async def database_error_handler(
    _request: Request, exc: DatabaseError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "database_error",
            "message": "An internal database error occurred. Please try again later.",
        },
    )


async def generic_error_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred.",
        },
    )
