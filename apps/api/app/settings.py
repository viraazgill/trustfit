import datetime as dt
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://trustfit:trustfit@localhost:5432/trustfit"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_HOURS: int = 12
    CONFIG_DIR: Path = REPO_ROOT / "config"
    # Fixed scoring date for demos and tests; None means today.
    SCORING_AS_OF: dt.date | None = None
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
