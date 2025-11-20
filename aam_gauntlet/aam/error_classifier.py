"""Error classification for AAM responses."""
from enum import Enum
from typing import Optional, Dict, Any


class ErrorClass(Enum):
    """Classification of API errors."""
    AUTH_EXPIRED = "auth_expired"
    INVALID_CREDS = "invalid_creds"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ErrorClassifier:
    """Classify errors from API responses."""
    
    @staticmethod
    def classify_error(
        status_code: Optional[int],
        response_data: Optional[Dict[str, Any]],
        exception: Optional[Exception] = None
    ) -> ErrorClass:
        """
        Classify an error based on status code, response data, and exception.
        """
        # Handle exceptions first
        if exception:
            exc_str = str(exception).lower()
            if "timeout" in exc_str:
                return ErrorClass.TIMEOUT
            elif any(net_err in exc_str for net_err in ["connection", "network", "dns"]):
                return ErrorClass.NETWORK_ERROR
            elif "auth" in exc_str or "token" in exc_str:
                return ErrorClass.AUTH_EXPIRED
        
        # Handle status codes
        if status_code:
            if status_code == 401:
                # Check response for more specific auth errors
                if response_data:
                    error_msg = str(response_data.get("error", "")).lower()
                    if "expired" in error_msg:
                        return ErrorClass.AUTH_EXPIRED
                    else:
                        return ErrorClass.INVALID_CREDS
                return ErrorClass.INVALID_CREDS
            
            elif status_code == 429:
                return ErrorClass.RATE_LIMIT
            
            elif status_code == 403:
                return ErrorClass.INVALID_CREDS
            
            elif 400 <= status_code < 500:
                return ErrorClass.CLIENT_ERROR
            
            elif 500 <= status_code < 600:
                return ErrorClass.SERVER_ERROR
        
        return ErrorClass.UNKNOWN
    
    @staticmethod
    def is_retryable(error_class: ErrorClass) -> bool:
        """Determine if an error is retryable."""
        retryable_errors = {
            ErrorClass.RATE_LIMIT,
            ErrorClass.NETWORK_ERROR,
            ErrorClass.SERVER_ERROR,
            ErrorClass.TIMEOUT,
            ErrorClass.AUTH_EXPIRED  # Can retry after token refresh
        }
        return error_class in retryable_errors
    
    @staticmethod
    def get_retry_delay(error_class: ErrorClass, attempt: int) -> float:
        """Calculate retry delay based on error class and attempt number."""
        base_delays = {
            ErrorClass.RATE_LIMIT: 5.0,
            ErrorClass.NETWORK_ERROR: 2.0,
            ErrorClass.SERVER_ERROR: 3.0,
            ErrorClass.TIMEOUT: 1.0,
            ErrorClass.AUTH_EXPIRED: 0.5,  # Quick retry after refresh
        }
        
        base_delay = base_delays.get(error_class, 1.0)
        
        # Exponential backoff with jitter
        import random
        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
        
        # Cap at 60 seconds
        return min(delay, 60.0)