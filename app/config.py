import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    ALLOWED_WEB_ORIGIN: str = os.getenv("ALLOWED_WEB_ORIGIN", "http://localhost:3000")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    
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
