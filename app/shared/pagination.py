import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Self

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field


class PaginationParams:
    """Query parameter dependency for paginated list endpoints."""

    def __init__(
        self,
        page: Annotated[
            int,
            Query(
                ge=1,
                description="Page number (1-indexed)",
                examples=[1],
            ),
        ] = 1,
        size: Annotated[
            int,
            Query(
                ge=1,
                le=100,
                description="Number of records per page (max: 100)",
                examples=[20],
            ),
        ] = 20,
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
    """Encapsulates raw query results with total count before serialization."""

    items: Sequence[ModelType]
    total: int
    page: int
    size: int


class Page[T](BaseModel):
    """Standardized generic paginated response payload compliant with OpenAPI/Swagger."""

    model_config = ConfigDict(from_attributes=True)

    items: Sequence[T] = Field(
        ...,
        description="List of records for the current page",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of records matching the query",
        examples=[100],
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-indexed)",
        examples=[1],
    )
    size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Page size limit",
        examples=[20],
    )
    pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
        examples=[5],
    )
    has_next: bool = Field(
        ...,
        description="Whether a subsequent page exists",
        examples=[True],
    )
    has_previous: bool = Field(
        ...,
        description="Whether a preceding page exists",
        examples=[False],
    )

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        params: PaginationParams,
    ) -> Self:
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
