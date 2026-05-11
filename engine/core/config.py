from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "Aegis Legal AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SERVE_FRONTEND: bool = False

    # Security
    JWT_SECRET: str = "DEVELOPMENT_SECRET_KEY_REPLACE_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    AUTH_ENABLED: bool = False

    # AI Providers
    GROQ_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    
    # Data Stores
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "aegis_legal_docs"
    REDIS_URL: Optional[str] = None
    
    # CORS
    CORS_ALLOW_ORIGINS: List[str] = ["*"]

    # Scaling & Performance
    MAX_CONCURRENT_USERS: int = 100
    REQUEST_TIMEOUT_SECONDS: int = 60
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "../../.env"],
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
