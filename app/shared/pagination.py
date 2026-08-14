import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams:
    """Query parameter dependency for list pagination."""

    def __init__(
        self,
        page: int = Query(
            default=1,
            ge=1,
            description="Page number (1-indexed)",
        ),
        size: int = Query(
            default=20,
            ge=1,
            le=100,
            description="Number of items per page (maximum 100)",
        ),
    ) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


@dataclass(frozen=True, slots=True)
class PaginatedResult[ModelType]:
    """Internal database result encapsulation holding items and total count."""

    items: Sequence[ModelType]
    total: int
    page: int
    size: int


class Page[T](BaseModel):
    """Standardized generic paginated response payload."""

    items: Sequence[T] = Field(..., description="List of items for the current page")
    total: int = Field(..., ge=0, description="Total number of items matching the query")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    size: int = Field(..., ge=1, description="Page size limit")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether a subsequent page exists")
    has_previous: bool = Field(..., description="Whether a preceding page exists")

    @classmethod
    def create(
        cls,
        items: Sequence[Any],
        total: int,
        params: PaginationParams,
    ) -> "Page[T]":
        pages = math.ceil(total / params.size) if total > 0 else 0
        has_next = params.page < pages
        has_previous = params.page > 1 and total > 0

        return cls(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=pages,
            has_next=has_next,
            has_previous=has_previous,
        )
