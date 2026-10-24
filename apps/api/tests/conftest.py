"""API tests run against a real Postgres test database (TEST_DATABASE_URL), migrated with Alembic.

If Postgres is not reachable the database tests are skipped, unless REQUIRE_DB=1 (CI), which fails them.
"""
import datetime as dt
import math
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.main import app
from app.seed import seed
from app.settings import settings

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
AS_OF = dt.date(2026, 10, 24)  # the golden outputs' scoring date


CONNECT_TIMEOUT_S = 3
_unreachable: str | None = None  # remembered so a missing database costs one timeout, not one per test


def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT",
                          connect_args={"connect_timeout": CONNECT_TIMEOUT_S})
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def db_engine():
    global _unreachable
    url = settings.TEST_DATABASE_URL
    if _unreachable is None:
        try:
            _ensure_database(url)
        except OperationalError as exc:
            if os.environ.get("REQUIRE_DB") == "1":
                raise
            _unreachable = (f"Postgres not reachable at {make_url(url)}: start it with `make db` "
                            f"({exc.__class__.__name__})")
    if _unreachable:
        pytest.skip(_unreachable)
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine, monkeypatch):
    monkeypatch.setattr(settings, "SCORING_AS_OF", AS_OF)
    monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 4)  # fast hashes in tests
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret-" + "x" * 32)
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        seed(db, AS_OF, wipe=True)
    return factory


@pytest.fixture
def client(session_factory):
    def override():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _token(client, role: str) -> dict[str, str]:
    email = getattr(settings, f"SEED_{role.upper()}_EMAIL")
    password = getattr(settings, f"SEED_{role.upper()}_PASSWORD")
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def as_analyst(client):
    return _token(client, "analyst")


@pytest.fixture
def as_viewer(client):
    return _token(client, "viewer")


@pytest.fixture
def as_admin(client):
    return _token(client, "admin")


def assert_matches(actual, expected, path: str = "$") -> None:
    """Deep equality; numbers compared to 4 decimal places."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), f"{path}: keys differ"
        for k in expected:
            assert_matches(actual[k], expected[k], f"{path}.{k}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), f"{path}: lists differ"
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            assert_matches(a, e, f"{path}[{i}]")
    elif isinstance(expected, int | float) and not isinstance(expected, bool):
        assert math.isclose(actual, expected, abs_tol=5e-5), f"{path}: {actual!r} != {expected!r}"
    else:
        assert actual == expected, f"{path}: {actual!r} != {expected!r}"
