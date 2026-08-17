from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GhostNet AI"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database and Caching
    DATABASE_URL: str = "postgresql+asyncpg://ghostnet:ghostnet_secure_pass@localhost:5432/ghostnet_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    POSTGIS_SRID: int = 4326

    # Operational Modes
    SMS_GATEWAY_MODE: str = "mock"  # "mock" | "real"
    MESH_MODE: str = "simulated"    # "simulated" | "real"
    DEMO_DISTRICT: str = "Purulia, West Bengal"
    DEBUG: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://10.0.2.2:8000",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
