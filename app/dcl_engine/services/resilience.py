"""
Resilience Infrastructure - Phase 3

Centralized async-aware resilience patterns for DCL Intelligence services.
Provides circuit breakers, retry logic, timeout enforcement, and graceful fallbacks.

Design Principles:
- Async-first: All decorators support async functions
- Differentiated thresholds: LLM, RAG, Redis, DB have different failure tolerances
- Graceful degradation: Fallback to heuristics when external services unavailable
- Observability: Structured errors, metrics, and logging integration

Dependencies:
- Python circuitbreaker library (for circuit breaker pattern)
- tenacity library (for retry with exponential backoff)
- asyncio (for timeout enforcement)
"""

import asyncio
import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, ParamSpec, Coroutine, Awaitable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class DependencyType(Enum):
    """External dependency types with differentiated resilience thresholds"""
    LLM = "llm"
    RAG = "rag"
    REDIS = "redis"
    DATABASE = "database"
    HTTP = "http"


@dataclass
class ResilienceConfig:
    """Resilience configuration for a specific dependency type"""
    failure_threshold: int
    recovery_timeout: int
    timeout_seconds: float
    retry_enabled: bool
    max_retries: int
    backoff_multiplier: float
    backoff_min: float
    backoff_max: float


LLM_CONFIG = ResilienceConfig(
    failure_threshold=3,
    recovery_timeout=60,
    timeout_seconds=30.0,
    retry_enabled=True,
    max_retries=3,
    backoff_multiplier=1.0,
    backoff_min=1.0,
    backoff_max=10.0
)

RAG_CONFIG = ResilienceConfig(
    failure_threshold=5,
    recovery_timeout=60,
    timeout_seconds=15.0,
    retry_enabled=True,
    max_retries=3,
    backoff_multiplier=1.0,
    backoff_min=0.5,
    backoff_max=5.0
)

REDIS_CONFIG = ResilienceConfig(
    failure_threshold=5,
    recovery_timeout=30,
    timeout_seconds=5.0,
    retry_enabled=True,
    max_retries=2,
    backoff_multiplier=0.5,
    backoff_min=0.1,
    backoff_max=2.0
)

DATABASE_CONFIG = ResilienceConfig(
    failure_threshold=10,
    recovery_timeout=60,
    timeout_seconds=10.0,
    retry_enabled=False,
    max_retries=0,
    backoff_multiplier=0.0,
    backoff_min=0.0,
    backoff_max=0.0
)

HTTP_CONFIG = ResilienceConfig(
    failure_threshold=5,
    recovery_timeout=60,
    timeout_seconds=20.0,
    retry_enabled=True,
    max_retries=3,
    backoff_multiplier=1.0,
    backoff_min=1.0,
    backoff_max=15.0
)


DEPENDENCY_CONFIGS = {
    DependencyType.LLM: LLM_CONFIG,
    DependencyType.RAG: RAG_CONFIG,
    DependencyType.REDIS: REDIS_CONFIG,
    DependencyType.DATABASE: DATABASE_CONFIG,
    DependencyType.HTTP: HTTP_CONFIG
}


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open (too many failures)"""
    def __init__(self, dependency: str, failures: int, recovery_timeout: int):
        self.dependency = dependency
        self.failures = failures
        self.recovery_timeout = recovery_timeout
        super().__init__(
            f"Circuit breaker OPEN for {dependency} "
            f"({failures} failures, recovery in {recovery_timeout}s)"
        )


class TimeoutError(Exception):
    """Raised when operation exceeds configured timeout"""
    def __init__(self, operation: str, timeout_seconds: float):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Operation '{operation}' exceeded timeout of {timeout_seconds}s"
        )


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    def __init__(self, operation: str, attempts: int, last_error: Exception):
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Operation '{operation}' failed after {attempts} retries: {last_error}"
        )


class SimpleCircuitBreaker:
    """
    Lightweight async circuit breaker implementation.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int,
        recovery_timeout: int
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
    
    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker {self.name}: Entering HALF_OPEN state")
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError(
                    dependency=self.name,
                    failures=self.failure_count,
                    recovery_timeout=self.recovery_timeout
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Reset circuit breaker on successful call"""
        if self.state == "HALF_OPEN":
            logger.info(f"Circuit breaker {self.name}: Service recovered, entering CLOSED state")
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None
    
    def _on_failure(self):
        """Increment failure count and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker {self.name}: OPEN after {self.failure_count} failures "
                f"(threshold: {self.failure_threshold})"
            )
            self.state = "OPEN"
    
    def get_state(self) -> dict:
        """Get current circuit breaker state for health checks"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None
        }


_circuit_breakers: dict[str, SimpleCircuitBreaker] = {}


def get_circuit_breaker(dependency: DependencyType) -> SimpleCircuitBreaker:
    """Get or create circuit breaker for dependency"""
    name = dependency.value
    
    if name not in _circuit_breakers:
        config = DEPENDENCY_CONFIGS[dependency]
        _circuit_breakers[name] = SimpleCircuitBreaker(
            name=name,
            failure_threshold=config.failure_threshold,
            recovery_timeout=config.recovery_timeout
        )
    
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict[str, dict]:
    """Get state of all circuit breakers (for health checks)"""
    return {
        name: breaker.get_state()
        for name, breaker in _circuit_breakers.items()
    }


async def with_retry(
    func: Callable[..., Awaitable[T]],
    config: ResilienceConfig,
    operation_name: str,
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Execute function with retry logic (exponential backoff with jitter).
    
    Only retries idempotent operations (LLM, RAG, HTTP).
    Database writes are NOT retried to prevent duplicate work.
    """
    if not config.retry_enabled:
        return await func(*args, **kwargs)
    
    last_error: Optional[Exception] = None
    
    for attempt in range(1, config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 1:
                logger.info(
                    f"Operation '{operation_name}' succeeded on attempt {attempt}"
                )
            return result
        
        except CircuitBreakerOpenError:
            raise
        
        except Exception as e:
            last_error = e
            
            if attempt < config.max_retries:
                backoff = min(
                    config.backoff_max,
                    config.backoff_min * (config.backoff_multiplier ** (attempt - 1))
                )
                jitter = backoff * 0.1
                wait_time = backoff + (jitter * (0.5 - asyncio.get_event_loop().time() % 1))
                
                logger.warning(
                    f"Operation '{operation_name}' failed on attempt {attempt}/{config.max_retries}, "
                    f"retrying in {wait_time:.2f}s: {str(e)}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Operation '{operation_name}' failed after {config.max_retries} retries: {str(e)}"
                )
    
    if last_error is None:
        last_error = Exception("Unknown error")
    
    raise RetryExhaustedError(
        operation=operation_name,
        attempts=config.max_retries,
        last_error=last_error
    )


async def with_timeout(
    func: Callable[..., Awaitable[T]],
    timeout_seconds: float,
    operation_name: str,
    *args: Any,
    **kwargs: Any
) -> T:
    """Execute function with timeout enforcement using asyncio.wait_for"""
    try:
        coro = func(*args, **kwargs)
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(
            operation=operation_name,
            timeout_seconds=timeout_seconds
        )


def with_resilience(
    dependency: DependencyType,
    operation_name: Optional[str] = None,
    fallback_name: Optional[str] = None
):
    """
    Decorator that applies full resilience pattern:
    1. Circuit breaker
    2. Timeout enforcement
    3. Retry logic (if enabled)
    4. Graceful fallback (if provided via name-based invocation)
    
    Usage:
        class MyService:
            @with_resilience(
                DependencyType.LLM, 
                operation_name="generate_proposal",
                fallback_name="_heuristic_fallback"
            )
            async def propose_mapping(self, ...):
                # Clean business logic only
                ...
            
            async def _heuristic_fallback(self, ...):
                # Fallback implementation (signature matches primary method excluding 'self')
                ...
    
    Args:
        dependency: Type of external dependency (LLM, RAG, Redis, etc.)
        operation_name: Human-readable operation name for logging
        fallback_name: Optional name of fallback method (string) on the instance.
                       The decorator will invoke it using getattr(instance, fallback_name).
                       Fallback signature must match the original method (excluding 'self').
    """
    config = DEPENDENCY_CONFIGS[dependency]
    circuit_breaker = get_circuit_breaker(dependency)
    
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            op_name = operation_name or func.__name__
            
            async def resilient_operation():
                """Full resilience chain: timeout → retry → circuit breaker"""
                async def timed_operation():
                    return await with_timeout(
                        func,
                        config.timeout_seconds,
                        op_name,
                        *args,
                        **kwargs
                    )
                
                return await with_retry(
                    timed_operation,
                    config=config,
                    operation_name=op_name
                )
            
            try:
                return await circuit_breaker.call(resilient_operation)
            
            except (CircuitBreakerOpenError, TimeoutError, RetryExhaustedError) as e:
                # Name-based fallback invocation for instance methods
                if fallback_name and args:
                    instance = args[0]
                    
                    if hasattr(instance, fallback_name):
                        # Get the BOUND method from the instance
                        fallback_func = getattr(instance, fallback_name)
                        
                        logger.warning(
                            f"Failure in {func.__name__} ({dependency.value}). "
                            f"Invoking fallback '{fallback_name}': {type(e).__name__}"
                        )
                        
                        try:
                            # Call the bound fallback method with remaining args (strip 'self')
                            # The bound method already includes 'self'
                            result = fallback_func(*args[1:], **kwargs)
                            if asyncio.iscoroutine(result):
                                return await result
                            return result
                        
                        except Exception as fallback_e:
                            logger.error(
                                f"Fallback method '{fallback_name}' itself failed: {fallback_e}"
                            )
                            raise e from fallback_e
                
                # No suitable fallback found or fallback not configured
                if fallback_name:
                    logger.error(
                        f"Failure in {func.__name__} ({dependency.value}). "
                        f"Fallback '{fallback_name}' not found on instance. Error: {e}"
                    )
                raise
        
        return wrapper
    
    return decorator


class BulkheadSemaphore:
    """
    Bulkhead isolation using async semaphores.
    Prevents one dependency from exhausting resources for others.
    """
    
    def __init__(self, name: str, max_concurrent: int):
        self.name = name
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0
    
    async def acquire(self):
        """Acquire semaphore slot"""
        await self.semaphore.acquire()
        self.active_count += 1
    
    def release(self):
        """Release semaphore slot"""
        self.semaphore.release()
        self.active_count = max(0, self.active_count - 1)
    
    def get_state(self) -> dict:
        """Get current bulkhead state"""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active_count": self.active_count,
            "available_slots": self.max_concurrent - self.active_count
        }


_bulkheads: dict[str, BulkheadSemaphore] = {
    "llm": BulkheadSemaphore("llm", max_concurrent=10),
    "database": BulkheadSemaphore("database", max_concurrent=50),
    "rag": BulkheadSemaphore("rag", max_concurrent=20),
}


def get_bulkhead(name: str) -> BulkheadSemaphore:
    """Get bulkhead semaphore by name"""
    return _bulkheads.get(name, _bulkheads["llm"])


def get_all_bulkheads() -> dict[str, dict]:
    """Get state of all bulkheads (for health checks)"""
    return {
        name: bulkhead.get_state()
        for name, bulkhead in _bulkheads.items()
    }


def with_bulkhead(bulkhead_name: str):
    """
    Decorator that applies bulkhead isolation.
    
    Usage:
        @with_bulkhead("llm")
        async def call_llm(...):
            ...
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            bulkhead = get_bulkhead(bulkhead_name)
            
            try:
                await bulkhead.acquire()
                return await func(*args, **kwargs)
            finally:
                bulkhead.release()
        
        return wrapper
    
    return decorator
