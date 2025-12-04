import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Priority: SUPABASE_DB_URL or SUPABASE_DATABASE_URL (custom) > DATABASE_URL (Replit-managed)
    # Use SUPABASE_DB_URL in production to override Replit's auto-generated Neon DATABASE_URL
    DATABASE_URL: str = os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    ALLOWED_WEB_ORIGIN: str = os.getenv("ALLOWED_WEB_ORIGIN", "http://localhost:3000")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    EVENT_STREAM_ENABLED: bool = os.getenv("EVENT_STREAM_ENABLED", "true").lower() == "true"
    EVENT_STREAM_HEARTBEAT_MS: int = int(os.getenv("EVENT_STREAM_HEARTBEAT_MS", "15000"))
    
    # AOS Discover service (AOD) configuration
    AOD_BASE_URL: str = os.getenv("AOD_BASE_URL", "http://localhost:8000")
    
    def __init__(self):
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL environment variable is required but not set. "
                "Please ensure your PostgreSQL database is configured."
            )
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable is required but not set. "
                "Please add a secure random string (32+ characters) to Replit Secrets. "
                "This key is used for JWT token signing."
            )
        if not self.JWT_SECRET_KEY:
            self.JWT_SECRET_KEY = self.SECRET_KEY

settings = Settings()
