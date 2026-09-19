from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="WORKBOARD_", extra="ignore")

    database_url: str = "postgresql+psycopg://workboard:workboard@localhost:5432/workboard"
    jwt_secret: SecretStr
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
