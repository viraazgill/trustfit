import datetime as dt
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Empty values (e.g. SCORING_AS_OF= in .env.example) mean "use the default".
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore", env_ignore_empty=True)

    DATABASE_URL: str = "postgresql+psycopg://trustfit:trustfit@localhost:5432/trustfit"
    TEST_DATABASE_URL: str = "postgresql+psycopg://trustfit:trustfit@localhost:5432/trustfit_test"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_HOURS: int = 12
    BCRYPT_ROUNDS: int = 12
    CONFIG_DIR: Path = REPO_ROOT / "config"
    SEED_DIR: Path = REPO_ROOT / "seed"
    # Fixed scoring date for demos and tests; None means today.
    SCORING_AS_OF: dt.date | None = None
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    # The web app the PDF printer opens (it prints the same report pages the SME sees)
    WEB_URL: str = "http://localhost:3000"

    # Users created by `python -m app.seed`
    SEED_ADMIN_EMAIL: str = "admin@trustfit.local"
    SEED_ADMIN_PASSWORD: str = "change-me-admin"
    SEED_ANALYST_EMAIL: str = "analyst@trustfit.local"
    SEED_ANALYST_PASSWORD: str = "change-me-analyst"
    SEED_VIEWER_EMAIL: str = "viewer@trustfit.local"
    SEED_VIEWER_PASSWORD: str = "change-me-viewer"


settings = Settings()


def scoring_date() -> dt.date:
    """The API's scoring date: SCORING_AS_OF when set, else today. The engine never reads the clock."""
    return settings.SCORING_AS_OF or dt.date.today()
