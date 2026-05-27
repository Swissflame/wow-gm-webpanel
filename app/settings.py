from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "WoW GM Webpanel"
    app_secret_key: str = "dev-change-me"
    app_base_url: str = "http://localhost"
    app_lang: str = "de"
    panel_db_url: str = "sqlite:///./instance/wow_gm_webpanel.db"
    configured: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
