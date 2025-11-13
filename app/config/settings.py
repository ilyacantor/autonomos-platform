"""
Unified Configuration System for AutonomOS Platform

This module consolidates all configuration from app/config.py and
aam_hybrid/shared/config.py into a single, validated Pydantic Settings system.

All secrets must be provided via environment variables. No hardcoded defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, PostgresDsn
from typing import Optional
import os


class DatabaseSettings(BaseSettings):
    """Database connection configuration"""

    database_url: str = Field(
        ...,
        description="PostgreSQL database connection string. Required.",
        validation_alias="DATABASE_URL"
    )

    postgres_url: Optional[str] = Field(
        None,
        description="Alternative PostgreSQL URL (legacy support)",
        validation_alias="POSTGRES_URL"
    )

    supabase_db_url: Optional[str] = Field(
        None,
        description="Supabase PostgreSQL connection string. Defaults to DATABASE_URL if not set.",
        validation_alias="SUPABASE_DB_URL"
    )

    supabase_schema: str = Field(
        default="public",
        description="Supabase database schema",
        validation_alias="SUPABASE_SCHEMA"
    )

    mongodb_uri: Optional[str] = Field(
        None,
        description="MongoDB connection URI for AAM connectors",
        validation_alias="MONGODB_URI"
    )

    mongodb_db: str = Field(
        default="autonomos",
        description="MongoDB database name",
        validation_alias="MONGODB_DB"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class RedisSettings(BaseSettings):
    """Redis cache and message broker configuration"""

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL (takes precedence over individual settings)",
        validation_alias="REDIS_URL"
    )

    redis_host: str = Field(
        default="localhost",
        description="Redis host (used if REDIS_URL not set)",
        validation_alias="REDIS_HOST"
    )

    redis_port: int = Field(
        default=6379,
        description="Redis port (used if REDIS_URL not set)",
        validation_alias="REDIS_PORT"
    )

    redis_db: int = Field(
        default=0,
        description="Redis database number (used if REDIS_URL not set)",
        validation_alias="REDIS_DB"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class SecuritySettings(BaseSettings):
    """Security and authentication configuration - NO HARDCODED SECRETS"""

    secret_key: str = Field(
        ...,
        min_length=32,
        description="Application secret key for JWT signing. REQUIRED. Minimum 32 characters.",
        validation_alias="SECRET_KEY"
    )

    jwt_secret_key: Optional[str] = Field(
        None,
        description="JWT-specific secret key. Defaults to SECRET_KEY if not provided.",
        validation_alias="JWT_SECRET_KEY"
    )

    jwt_secret: Optional[str] = Field(
        None,
        description="Legacy JWT secret (alias for jwt_secret_key)",
        validation_alias="JWT_SECRET"
    )

    jwt_issuer: str = Field(
        default="autonomos.dev",
        description="JWT token issuer",
        validation_alias="JWT_ISSUER"
    )

    jwt_audience: str = Field(
        default="aos.agents",
        description="JWT token audience",
        validation_alias="JWT_AUDIENCE"
    )

    jwt_expire_minutes: int = Field(
        default=30,
        description="JWT token expiration time in minutes",
        validation_alias="JWT_EXPIRE_MINUTES"
    )

    api_key: Optional[str] = Field(
        None,
        description="API key for external service authentication",
        validation_alias="API_KEY"
    )

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def default_jwt_secret(cls, v, info):
        """Use SECRET_KEY as default for jwt_secret_key if not provided"""
        if v is None and "secret_key" in info.data:
            return info.data["secret_key"]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class AirbyteSettings(BaseSettings):
    """Airbyte integration configuration for AAM connectors"""

    airbyte_api_url: str = Field(
        default="http://localhost:8000/api/public/v1",
        description="Airbyte API endpoint URL",
        validation_alias="AIRBYTE_API_URL"
    )

    airbyte_client_id: Optional[str] = Field(
        None,
        description="Airbyte OAuth client ID",
        validation_alias="AIRBYTE_CLIENT_ID"
    )

    airbyte_client_secret: Optional[str] = Field(
        None,
        description="Airbyte OAuth client secret",
        validation_alias="AIRBYTE_CLIENT_SECRET"
    )

    airbyte_workspace_id: Optional[str] = Field(
        None,
        description="Airbyte workspace ID",
        validation_alias="AIRBYTE_WORKSPACE_ID"
    )

    airbyte_destination_id: Optional[str] = Field(
        None,
        description="Airbyte destination ID",
        validation_alias="AIRBYTE_DESTINATION_ID"
    )

    airbyte_use_oss: bool = Field(
        default=False,
        description="Use Airbyte OSS (open source) instead of Cloud",
        validation_alias="AIRBYTE_USE_OSS"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class SalesforceSettings(BaseSettings):
    """Salesforce OAuth configuration for AAM connectors"""

    salesforce_client_id: Optional[str] = Field(
        None,
        description="Salesforce Connected App client ID",
        validation_alias="SALESFORCE_CLIENT_ID"
    )

    salesforce_client_secret: Optional[str] = Field(
        None,
        description="Salesforce Connected App client secret",
        validation_alias="SALESFORCE_CLIENT_SECRET"
    )

    salesforce_refresh_token: Optional[str] = Field(
        None,
        description="Salesforce OAuth refresh token",
        validation_alias="SALESFORCE_REFRESH_TOKEN"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class AAMServiceSettings(BaseSettings):
    """AAM (AutonomOS Architecture Manager) service port configuration"""

    service_port_orchestrator: int = Field(
        default=8001,
        description="Orchestrator service port",
        validation_alias="SERVICE_PORT_ORCHESTRATOR"
    )

    orchestrator_port: Optional[int] = Field(
        None,
        description="Legacy orchestrator port (alias)",
        validation_alias="ORCHESTRATOR_PORT"
    )

    orchestrator_url: str = Field(
        default="http://localhost:8001",
        description="Orchestrator service URL",
        validation_alias="ORCHESTRATOR_URL"
    )

    service_port_auth_broker: int = Field(
        default=8002,
        description="Auth Broker service port",
        validation_alias="SERVICE_PORT_AUTH_BROKER"
    )

    service_port_drift_repair: int = Field(
        default=8003,
        description="Drift Repair Agent service port",
        validation_alias="SERVICE_PORT_DRIFT_REPAIR"
    )

    drift_repair_port: Optional[int] = Field(
        None,
        description="Legacy drift repair port (alias)",
        validation_alias="DRIFT_REPAIR_PORT"
    )

    drift_repair_url: str = Field(
        default="http://localhost:8003",
        description="Drift Repair service URL",
        validation_alias="DRIFT_REPAIR_URL"
    )

    drift_repair_confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for auto-repair (0.0-1.0)",
        validation_alias="DRIFT_REPAIR_CONFIDENCE_THRESHOLD"
    )

    service_port_schema_observer: int = Field(
        default=8004,
        description="Schema Observer service port",
        validation_alias="SERVICE_PORT_SCHEMA_OBSERVER"
    )

    schema_observer_port: Optional[int] = Field(
        None,
        description="Legacy schema observer port (alias)",
        validation_alias="SCHEMA_OBSERVER_PORT"
    )

    schema_observer_url: str = Field(
        default="http://localhost:8004",
        description="Schema Observer service URL",
        validation_alias="SCHEMA_OBSERVER_URL"
    )

    service_port_rag_engine: int = Field(
        default=8005,
        description="RAG Engine service port",
        validation_alias="SERVICE_PORT_RAG_ENGINE"
    )

    rag_engine_port: Optional[int] = Field(
        None,
        description="Legacy RAG engine port (alias)",
        validation_alias="RAG_ENGINE_PORT"
    )

    rag_engine_url: str = Field(
        default="http://localhost:8005",
        description="RAG Engine service URL",
        validation_alias="RAG_ENGINE_URL"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class LLMSettings(BaseSettings):
    """Large Language Model configuration for RAG and drift repair"""

    openai_api_key: Optional[str] = Field(
        None,
        description="OpenAI API key for GPT models",
        validation_alias="OPENAI_API_KEY"
    )

    llm_model_name: str = Field(
        default="gpt-4o-mini",
        description="LLM model name to use",
        validation_alias="LLM_MODEL_NAME"
    )

    gemini_api_key: Optional[str] = Field(
        None,
        description="Google Gemini API key",
        validation_alias="GEMINI_API_KEY"
    )

    pinecone_api_key: Optional[str] = Field(
        None,
        description="Pinecone vector database API key",
        validation_alias="PINECONE_API_KEY"
    )

    pinecone_environment: Optional[str] = Field(
        None,
        description="Pinecone environment (e.g., us-west1-gcp)",
        validation_alias="PINECONE_ENVIRONMENT"
    )

    pinecone_index: Optional[str] = Field(
        None,
        description="Pinecone index name",
        validation_alias="PINECONE_INDEX"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class ExternalIntegrationSettings(BaseSettings):
    """External service integrations (Slack, CORS, etc.)"""

    slack_webhook_url: Optional[str] = Field(
        None,
        description="Slack webhook URL for notifications",
        validation_alias="SLACK_WEBHOOK_URL"
    )

    allowed_web_origin: str = Field(
        default="http://localhost:3000",
        description="CORS allowed web origin",
        validation_alias="ALLOWED_WEB_ORIGIN"
    )

    aod_base_url: str = Field(
        default="http://localhost:8000",
        description="AOS Discover (AOD) service base URL",
        validation_alias="AOD_BASE_URL"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class FeatureFlagSettings(BaseSettings):
    """Feature flags for progressive rollout"""

    feature_use_filesource: bool = Field(
        default=True,
        description="Enable file-based source connector for CSV ingestion",
        validation_alias="FEATURE_USE_FILESOURCE"
    )

    feature_drift_autofix: bool = Field(
        default=False,
        description="Enable automatic drift repair (>=0.85 confidence)",
        validation_alias="FEATURE_DRIFT_AUTOFIX"
    )

    monitor_polling: bool = Field(
        default=False,
        description="Enable AAM monitoring dashboard polling",
        validation_alias="MONITOR_POLLING"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class GatewaySettings(BaseSettings):
    """API Gateway configuration (rate limiting, idempotency)"""

    rate_limit_rpm: int = Field(
        default=60,
        description="Rate limit: requests per minute per tenant",
        validation_alias="RATE_LIMIT_RPM"
    )

    rate_limit_burst: int = Field(
        default=10,
        description="Rate limit: burst allowance",
        validation_alias="RATE_LIMIT_BURST"
    )

    idempotency_cache_minutes: int = Field(
        default=10,
        description="Idempotency key cache duration in minutes",
        validation_alias="IDEMPOTENCY_CACHE_MINUTES"
    )

    build_sha: str = Field(
        default="local-dev",
        description="Build SHA for health endpoint (auto-generated in CI/CD)",
        validation_alias="BUILD_SHA"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class MultiTenantSettings(BaseSettings):
    """Multi-tenant configuration"""

    tenant_id_demo: str = Field(
        default="demo-tenant",
        description="Demo tenant ID for testing",
        validation_alias="TENANT_ID_DEMO"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class DCLEngineSettings(BaseSettings):
    """DCL (Data Control Layer) Engine configuration"""

    dcl_registry_path: str = Field(
        default="./app/dcl_engine/registry.duckdb",
        description="DuckDB registry database path",
        validation_alias="DCL_REGISTRY_PATH"
    )

    dcl_dev_mode: bool = Field(
        default=False,
        description="Enable DCL development mode",
        validation_alias="DCL_DEV_MODE"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class LoggingSettings(BaseSettings):
    """Logging and monitoring configuration"""

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        validation_alias="LOG_LEVEL"
    )

    log_format: str = Field(
        default="json",
        description="Log format (json or text)",
        validation_alias="LOG_FORMAT"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class EventStreamSettings(BaseSettings):
    """Server-Sent Events (SSE) configuration for live flow visualization"""

    event_stream_enabled: bool = Field(
        default=True,
        description="Enable Server-Sent Events (SSE) for live flow visualization",
        validation_alias="EVENT_STREAM_ENABLED"
    )

    event_stream_heartbeat_ms: int = Field(
        default=15000,
        description="Heartbeat interval for SSE connections in milliseconds",
        validation_alias="EVENT_STREAM_HEARTBEAT_MS"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class DevelopmentSettings(BaseSettings):
    """Development and debugging configuration"""

    environment: str = Field(
        default="development",
        description="Environment identifier (development, preview, production)",
        validation_alias="ENVIRONMENT"
    )

    port: int = Field(
        default=8000,
        description="Application port (set by Render in preview/production)",
        validation_alias="PORT"
    )

    debug: bool = Field(
        default=False,
        description="Enable debug mode (DO NOT use in production)",
        validation_alias="DEBUG"
    )

    dev_debug: bool = Field(
        default=False,
        description="Enable development debug mode",
        validation_alias="DEV_DEBUG"
    )

    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
        validation_alias="VERBOSE"
    )

    disable_auto_migrations: bool = Field(
        default=False,
        description="Disable automatic database migrations on startup",
        validation_alias="DISABLE_AUTO_MIGRATIONS"
    )

    required_sources: Optional[str] = Field(
        None,
        description="Comma-separated list of required data sources",
        validation_alias="REQUIRED_SOURCES"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class Settings(BaseSettings):
    """
    Unified AutonomOS Platform Configuration

    Consolidates all configuration from app/config.py and aam_hybrid/shared/config.py
    into a single, validated Pydantic Settings system.

    All secrets (SECRET_KEY, API keys, etc.) must be provided via environment variables.
    No hardcoded defaults for sensitive data.

    Usage:
        from app.config.settings import settings

        # Access settings
        db_url = settings.database.database_url
        redis_url = settings.redis.redis_url
        secret_key = settings.security.secret_key
    """

    # Configuration groups
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    airbyte: AirbyteSettings = Field(default_factory=AirbyteSettings)
    salesforce: SalesforceSettings = Field(default_factory=SalesforceSettings)
    aam_services: AAMServiceSettings = Field(default_factory=AAMServiceSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    external: ExternalIntegrationSettings = Field(default_factory=ExternalIntegrationSettings)
    features: FeatureFlagSettings = Field(default_factory=FeatureFlagSettings)
    gateway: GatewaySettings = Field(default_factory=GatewaySettings)
    multi_tenant: MultiTenantSettings = Field(default_factory=MultiTenantSettings)
    dcl_engine: DCLEngineSettings = Field(default_factory=DCLEngineSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    event_stream: EventStreamSettings = Field(default_factory=EventStreamSettings)
    development: DevelopmentSettings = Field(default_factory=DevelopmentSettings)

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def __init__(self, **kwargs):
        """Initialize settings and validate required fields"""
        super().__init__(**kwargs)

        # Ensure database URL is set
        if not self.database.database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required but not set. "
                "Please ensure your PostgreSQL database is configured."
            )

        # Ensure secret key is set and meets minimum length
        if not self.security.secret_key or len(self.security.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY environment variable is required and must be at least 32 characters. "
                "Please add a secure random string to your environment. "
                "This key is used for JWT token signing and encryption."
            )

        # Auto-populate supabase_db_url from database_url if not set
        if not self.database.supabase_db_url:
            self.database.supabase_db_url = self.database.database_url


# Global settings instance
# This will fail fast on import if required environment variables are missing
settings = Settings()


__all__ = ["Settings", "settings"]
