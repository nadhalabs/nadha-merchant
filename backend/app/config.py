from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "sqlite:///./nadha.db"
    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 10080
    cors_origins: str = "http://localhost:5173,capacitor://localhost,http://localhost,https://localhost"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def production_safety(self):
        if self.environment.lower()=="production":
            if self.secret_key=="development-only-change-me" or len(self.secret_key)<32:raise ValueError("Production requires a strong SECRET_KEY")
            if self.database_url.startswith("sqlite"):raise ValueError("Production requires the configured PostgreSQL database")
            if any(origin.startswith("http://") for origin in self.cors_origin_list):raise ValueError("Production CORS origins must use HTTPS or capacitor://")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
