import uuid
import time
from contextvars import ContextVar

_trace_id_context: ContextVar[str] = ContextVar('trace_id', default=None)


def generate_trace_id(prefix: str = "nlp") -> str:
    """
    Generate a unique trace ID for request tracking.
    
    Format: {prefix}_{timestamp}_{uuid_short}
    Example: nlp_1699478400_a1b2c3d4
    
    Args:
        prefix: Prefix for the trace ID (default: "nlp")
        
    Returns:
        Unique trace ID string
    """
    timestamp = int(time.time())
    short_uuid = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{short_uuid}"


def set_trace_id(trace_id: str) -> None:
    """
    Set the trace ID for the current request context.
    
    Args:
        trace_id: Trace ID to set
    """
    _trace_id_context.set(trace_id)


def get_trace_id() -> str:
    """
    Get the trace ID for the current request context.
    
    Returns:
        Current trace ID or "no-trace-id" if not set
    """
    return _trace_id_context.get() or "no-trace-id"
