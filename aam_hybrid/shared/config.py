"""
AAM Hybrid Configuration - Now using unified settings system

This module now uses the unified Pydantic settings system from app.config.settings
but maintains the same interface for backward compatibility with AAM services.

IMPORTANT: Hardcoded secrets have been REMOVED. All secrets must come from environment.

New code should import from app.config.settings directly.
"""

from pydantic_settings import BaseSettings
from typing import Optional

# Import unified settings from the main app config
from app.config.settings import settings as unified_settings


class Settings(BaseSettings):
    """
    AAM Hybrid Configuration - Backward-compatible wrapper

    Manages environment variables for Airbyte, Supabase, and Redis integration.
    All settings now pulled from unified configuration system.

    SECURITY: No hardcoded secrets. All sensitive values must be provided via environment.
    """

    # Airbyte configuration
    AIRBYTE_API_URL: str = unified_settings.airbyte.airbyte_api_url
    AIRBYTE_CLIENT_ID: Optional[str] = unified_settings.airbyte.airbyte_client_id
    AIRBYTE_CLIENT_SECRET: Optional[str] = unified_settings.airbyte.airbyte_client_secret
    AIRBYTE_WORKSPACE_ID: Optional[str] = unified_settings.airbyte.airbyte_workspace_id
    AIRBYTE_DESTINATION_ID: Optional[str] = unified_settings.airbyte.airbyte_destination_id
    AIRBYTE_USE_OSS: bool = unified_settings.airbyte.airbyte_use_oss

    # Database configuration - uses shared PostgreSQL database
    SUPABASE_DB_URL: str = unified_settings.database.supabase_db_url or unified_settings.database.database_url

    # Redis configuration
    REDIS_URL: str = unified_settings.redis.redis_url

    # Security - NO HARDCODED SECRETS - must come from environment
    SECRET_KEY: str = unified_settings.security.secret_key

    # Salesforce OAuth configuration
    SALESFORCE_CLIENT_ID: Optional[str] = unified_settings.salesforce.salesforce_client_id
    SALESFORCE_CLIENT_SECRET: Optional[str] = unified_settings.salesforce.salesforce_client_secret
    SALESFORCE_REFRESH_TOKEN: Optional[str] = unified_settings.salesforce.salesforce_refresh_token

    # AAM Service ports
    SERVICE_PORT_ORCHESTRATOR: int = unified_settings.aam_services.service_port_orchestrator
    SERVICE_PORT_AUTH_BROKER: int = unified_settings.aam_services.service_port_auth_broker
    SERVICE_PORT_DRIFT_REPAIR: int = unified_settings.aam_services.service_port_drift_repair
    SERVICE_PORT_SCHEMA_OBSERVER: int = unified_settings.aam_services.service_port_schema_observer
    SERVICE_PORT_RAG_ENGINE: int = unified_settings.aam_services.service_port_rag_engine

    # LLM configuration
    OPENAI_API_KEY: Optional[str] = unified_settings.llm.openai_api_key
    LLM_MODEL_NAME: str = unified_settings.llm.llm_model_name

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars from main app


# Create settings instance - all validation happens in unified_settings
# This will fail fast if SECRET_KEY or other required vars are missing
settings = Settings()


__all__ = ["Settings", "settings"]
