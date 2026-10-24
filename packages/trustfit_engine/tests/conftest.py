import datetime as dt
import json
import math
from pathlib import Path

import pytest

from trustfit_engine.config import TrustConfig, load_trust_config
from trustfit_engine.models import Company
from trustfit_engine.seed_io import load_companies

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "config"
SEED_DIR = REPO_ROOT / "seed"
EXPECTED_DIR = REPO_ROOT / "reference" / "expected"
AS_OF = dt.date(2026, 10, 24)  # the golden outputs' scoring date


@pytest.fixture(scope="session")
def cfg() -> TrustConfig:
    return load_trust_config(CONFIG_DIR / "trust_v1.yaml")


@pytest.fixture(scope="session")
def subros(cfg) -> Company:
    (company,) = load_companies(SEED_DIR / "subros.json", cfg, AS_OF)
    return company


def load_expected(name: str):
    return json.loads((EXPECTED_DIR / name).read_text(encoding="utf-8"))


def assert_matches(actual, expected, path: str = "$") -> None:
    """Deep equality; numbers compared to 4 decimal places."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected an object, got {actual!r}"
        assert set(actual) == set(expected), f"{path}: keys differ: {set(actual) ^ set(expected)}"
        for k in expected:
            assert_matches(actual[k], expected[k], f"{path}.{k}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), f"{path}: expected a list, got {actual!r}"
        assert len(actual) == len(expected), f"{path}: length {len(actual)} != {len(expected)}"
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            assert_matches(a, e, f"{path}[{i}]")
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        assert actual == expected, f"{path}: {actual!r} != {expected!r}"
    elif isinstance(expected, int | float):
        assert isinstance(actual, int | float) and not isinstance(actual, bool), f"{path}: {actual!r}"
        assert math.isclose(actual, expected, abs_tol=5e-5), f"{path}: {actual!r} != {expected!r}"
    else:  # pragma: no cover
        raise AssertionError(f"{path}: unexpected type {type(expected)}")
