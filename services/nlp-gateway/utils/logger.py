import logging
import sys
from typing import Optional
from contextvars import ContextVar

trace_id_context: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


class TraceIdFilter(logging.Filter):
    """
    Logging filter that injects trace_id into log records.
    """
    def filter(self, record):
        trace_id = trace_id_context.get()
        record.trace_id = trace_id if trace_id else "no-trace-id"
        return True


def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger with trace_id support.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(trace_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        trace_filter = TraceIdFilter()
        handler.addFilter(trace_filter)
        
        logger.addHandler(handler)
        logger.propagate = False
    
    return logger


def set_trace_id(trace_id: str) -> None:
    """
    Set the trace_id for the current context.
    
    Args:
        trace_id: Trace ID to set
    """
    trace_id_context.set(trace_id)


def get_trace_id() -> Optional[str]:
    """
    Get the trace_id from the current context.
    
    Returns:
        Current trace ID or None
    """
    return trace_id_context.get()
