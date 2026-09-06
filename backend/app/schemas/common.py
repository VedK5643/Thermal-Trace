"""
Common/shared Pydantic schemas.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int
    page_size: int
    total: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    data: list[T]
    pagination: PaginationMeta
