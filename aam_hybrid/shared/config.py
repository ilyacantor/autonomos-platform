from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    AAM Hybrid Configuration
    Manages environment variables for Airbyte, Supabase, and Redis integration
    """
    
    AIRBYTE_API_URL: str = "http://localhost:8000/api/public/v1"
    AIRBYTE_CLIENT_ID: Optional[str] = None
    AIRBYTE_CLIENT_SECRET: Optional[str] = None
    AIRBYTE_WORKSPACE_ID: Optional[str] = None
    AIRBYTE_DESTINATION_ID: Optional[str] = None
    
    # Use the shared PostgreSQL database from Replit
    SUPABASE_DB_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/aam_registry")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    SALESFORCE_CLIENT_ID: Optional[str] = None
    SALESFORCE_CLIENT_SECRET: Optional[str] = None
    SALESFORCE_REFRESH_TOKEN: Optional[str] = None
    
    SERVICE_PORT_ORCHESTRATOR: int = 8001
    SERVICE_PORT_AUTH_BROKER: int = 8002
    SERVICE_PORT_DRIFT_REPAIR: int = 8003
    SERVICE_PORT_SCHEMA_OBSERVER: int = 8004
    SERVICE_PORT_RAG_ENGINE: int = 8005
    
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars from main app


settings = Settings()
