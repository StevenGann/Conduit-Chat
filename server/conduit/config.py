from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_path: str = "./conduit.db"
    secret_key: str = ""  # Required in production
    default_password: str = ""  # Required; assigned to new human users
    port: int = 8080
    serve_web_app: bool = False
    web_app_path: str = "./static"
    admin_username: str | None = None  # Force this user as admin
    origin: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
