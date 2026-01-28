"""
API Utility Functions

Common utilities for reducing boilerplate in API endpoints:
- get_or_404: Raise HTTPException if resource not found
- handle_api_errors: Decorator for standardized error handling
"""

import functools
import logging
from typing import Any, Callable, Optional, TypeVar, Union

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_or_404(
    query_result: Optional[T],
    resource_name: str,
    resource_id: Any,
    detail: Optional[str] = None,
) -> T:
    """
    Return query result or raise 404 HTTPException if None.

    Args:
        query_result: The result from a database query (may be None)
        resource_name: Human-readable name of the resource (e.g., "Agent", "Run")
        resource_id: The ID that was queried for
        detail: Optional custom error message (overrides default)

    Returns:
        The query_result if not None

    Raises:
        HTTPException: 404 error if query_result is None

    Example:
        agent = get_or_404(
            db.query(models.Agent).filter(...).first(),
            "Agent",
            agent_id
        )
    """
    if query_result is None:
        error_detail = detail or f"{resource_name} {resource_id} not found"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail,
        )
    return query_result


def handle_api_errors(operation_name: str) -> Callable:
    """
    Decorator for standardized API error handling.

    Catches common exceptions and converts them to appropriate HTTPExceptions:
    - ValueError -> 400 Bad Request
    - PermissionError -> 403 Forbidden
    - LookupError (KeyError, IndexError) -> 404 Not Found
    - Other exceptions -> 500 Internal Server Error (logged)

    Args:
        operation_name: Description of the operation for error messages

    Example:
        @router.post("/agents/{agent_id}/delegate")
        @handle_api_errors("delegate task")
        async def create_delegation(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise FastAPI exceptions as-is
                raise
            except ValueError as e:
                logger.warning(f"Bad request during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except PermissionError as e:
                logger.warning(f"Permission denied during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(e) or "Permission denied",
                )
            except LookupError as e:
                logger.warning(f"Resource not found during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e) or "Resource not found",
                )
            except Exception as e:
                logger.exception(f"Unexpected error during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to {operation_name}: internal error",
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # Re-raise FastAPI exceptions as-is
                raise
            except ValueError as e:
                logger.warning(f"Bad request during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except PermissionError as e:
                logger.warning(f"Permission denied during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(e) or "Permission denied",
                )
            except LookupError as e:
                logger.warning(f"Resource not found during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e) or "Resource not found",
                )
            except Exception as e:
                logger.exception(f"Unexpected error during {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to {operation_name}: internal error",
                )

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
