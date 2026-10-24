"""The config loader validates trust_v1.yaml and fails loudly on bad numbers."""
import copy

import pytest
import yaml
from conftest import CONFIG_DIR
from pydantic import ValidationError

from trustfit_engine.config import TrustConfig, load_trust_config

RAW = yaml.safe_load((CONFIG_DIR / "trust_v1.yaml").read_text(encoding="utf-8"))


def test_real_config_loads(cfg):
    assert cfg.version == "v1"
    assert len(cfg.parameters) == 37
    assert list(cfg.categories) == list("ABCDEFGH")
    assert cfg.parameter_points("supplier", "A4") == 5.25
    assert cfg.parameter_points("distributor", "F4") == 5.0  # distributor override: 10 x 50%


def test_points_sum_to_100_for_every_role(cfg):
    for role in cfg.roles:
        assert sum(cfg.parameter_points(role, pid) for pid in cfg.parameters) == pytest.approx(100)


def broken(mutate) -> dict:
    raw = copy.deepcopy(RAW)
    mutate(raw)
    return raw


@pytest.mark.parametrize(("mutate", "message"), [
    (lambda r: r["category_weights"]["supplier"].update(A=16), "supplier.*sum to 100"),
    (lambda r: r["parameter_splits"]["default"].update(A1=11), "split.*A.*sum to 100"),
    (lambda r: r["parameter_splits"]["distributor"].update(F4=40), "distributor.*F.*sum to 100"),
    (lambda r: r["parameters"]["B2"]["rubric"].pop(25), "B2.*rubric"),
    (lambda r: r["parameters"]["B2"].update(category="Z"), "B2.*category"),
    (lambda r: r["parameter_splits"]["default"].pop("H2"), "H2"),
    (lambda r: r["category_weights"].pop("jv_partner"), "jv_partner"),
])
def test_invalid_config_fails_loudly(mutate, message):
    with pytest.raises(ValidationError, match=message):
        TrustConfig.model_validate(broken(mutate))


def test_missing_file_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_trust_config(tmp_path / "nope.yaml")
