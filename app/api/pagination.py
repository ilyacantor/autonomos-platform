"""
Reusable Pagination Utility for API Endpoints

Provides standardized pagination patterns:
- PaginationParams: Query parameter handling with validation
- paginate_query: Apply pagination to SQLAlchemy queries
- PaginatedResponse: Generic response model for paginated data
"""

from typing import Any, Generic, List, TypeVar, Callable
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query as SQLAlchemyQuery


# Generic type for paginated items
T = TypeVar("T")


class PaginationParams:
    """
    Pagination parameters with validation and defaults.

    Usage in endpoints:
        def list_items(pagination: PaginationParams = Depends()):
            ...
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """Calculate offset from page number."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size for compatibility."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response model.

    Usage:
        class ItemListResponse(PaginatedResponse[ItemResponse]):
            pass

    Or directly:
        response_model=PaginatedResponse[ItemResponse]
    """
    items: List[T]
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    has_more: bool = Field(..., description="Whether more pages exist")

    class Config:
        from_attributes = True


class PaginationResult(Generic[T]):
    """
    Result of paginating a query, containing items and metadata.

    Use build_response() to convert to a PaginatedResponse.
    """

    def __init__(
        self,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.has_more = (page * page_size) < total

    def build_response(self, response_class: type = None) -> dict[str, Any]:
        """
        Build a response dict that can be returned from an endpoint.

        Args:
            response_class: Optional Pydantic model class to instantiate.
                          If None, returns a dict.

        Returns:
            Response dict or model instance.
        """
        data = {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "has_more": self.has_more,
        }

        if response_class:
            return response_class(**data)
        return data


def paginate_query(
    query: SQLAlchemyQuery,
    params: PaginationParams,
    order_by: Any = None,
) -> PaginationResult:
    """
    Apply pagination to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        params: PaginationParams instance
        order_by: Optional column or expression to order by (e.g., Model.created_at.desc())

    Returns:
        PaginationResult with items, total count, and pagination metadata.

    Example:
        query = db.query(Agent).filter(Agent.tenant_id == tenant_id)
        result = paginate_query(query, params, order_by=Agent.created_at.desc())
        return result.build_response(AgentListResponse)
    """
    # Get total count before pagination
    total = query.count()

    # Apply ordering if provided
    if order_by is not None:
        query = query.order_by(order_by)

    # Apply pagination
    items = query.offset(params.offset).limit(params.limit).all()

    return PaginationResult(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


async def paginate_async(
    fetch_items: Callable,
    count_total: Callable,
    params: PaginationParams,
) -> PaginationResult:
    """
    Paginate async data sources (non-SQLAlchemy).

    Args:
        fetch_items: Async callable that returns items for the given offset/limit
        count_total: Async callable that returns total count
        params: PaginationParams instance

    Returns:
        PaginationResult with items and metadata.

    Example:
        async def fetch(offset, limit):
            return await external_api.list_items(offset=offset, limit=limit)

        async def count():
            return await external_api.count_items()

        result = await paginate_async(fetch, count, params)
    """
    total = await count_total()
    items = await fetch_items(params.offset, params.limit)

    return PaginationResult(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )
