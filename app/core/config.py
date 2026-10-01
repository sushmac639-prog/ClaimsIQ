from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ClaimIQ"
    app_env: str = "development"
    debug: bool = False
    database_url: str
    db_echo: bool = False
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
