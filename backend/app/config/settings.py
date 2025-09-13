from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server Configuration
    SERVER_HOST: str = "localhost"
    SERVER_PORT: int = 8000
    RELOAD: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./hive_small_file_db.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Default Hive/HDFS settings
    DEFAULT_HIVE_HOST: str = "localhost"
    DEFAULT_HIVE_PORT: int = 10000
    DEFAULT_HDFS_URL: str = "hdfs://localhost:9000"
    
    # Small file threshold (in bytes)
    SMALL_FILE_THRESHOLD: int = 128 * 1024 * 1024  # 128MB
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"

    # Schema management (dev convenience only)
    AUTO_CREATE_SCHEMA: bool = True

    # Demo mode: use simulated merge engine to validate flow without real Hive/HDFS
    DEMO_MODE: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
