"""
Legacy configuration module for backward compatibility

This module now uses the unified Pydantic settings system from app.config.settings
but maintains the same interface for backward compatibility with existing code.

DEPRECATED: New code should import from app.config.settings directly.
"""

from dotenv import load_dotenv
from app.config.settings import settings as unified_settings

load_dotenv()


class Settings:
    """
    Backward-compatible Settings class wrapper around unified Pydantic settings.

    This class provides the same interface as the old config.py to avoid breaking
    existing imports and usage patterns.

    New code should use: from app.config.settings import settings
    """

    def __init__(self):
        # All validation happens in unified_settings initialization
        # These properties will be accessed via __getattribute__ below
        pass

    def __getattribute__(self, name: str):
        """
        Dynamically map old attribute names to unified settings.

        This ensures backward compatibility while using the new settings internally.
        """
        # Handle special methods normally
        if name.startswith('__'):
            return object.__getattribute__(self, name)

        # Map old attribute names to new unified settings structure
        mappings = {
            # Database
            'DATABASE_URL': lambda: unified_settings.database.database_url,

            # Redis
            'REDIS_HOST': lambda: unified_settings.redis.redis_host,
            'REDIS_PORT': lambda: unified_settings.redis.redis_port,
            'REDIS_DB': lambda: unified_settings.redis.redis_db,
            'REDIS_URL': lambda: unified_settings.redis.redis_url,

            # Security
            'SECRET_KEY': lambda: unified_settings.security.secret_key,
            'JWT_SECRET_KEY': lambda: unified_settings.security.jwt_secret_key,
            'JWT_EXPIRE_MINUTES': lambda: unified_settings.security.jwt_expire_minutes,

            # External integrations
            'SLACK_WEBHOOK_URL': lambda: unified_settings.external.slack_webhook_url or "",
            'ALLOWED_WEB_ORIGIN': lambda: unified_settings.external.allowed_web_origin,
            'AOD_BASE_URL': lambda: unified_settings.external.aod_base_url,

            # Event streaming
            'EVENT_STREAM_ENABLED': lambda: unified_settings.event_stream.event_stream_enabled,
            'EVENT_STREAM_HEARTBEAT_MS': lambda: unified_settings.event_stream.event_stream_heartbeat_ms,
        }

        if name in mappings:
            return mappings[name]()

        # If not in mappings, raise AttributeError
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# Create settings instance - validation happens in unified_settings initialization
settings = Settings()


__all__ = ["Settings", "settings"]
