"""The engine must reproduce reference/expected/*.json (numbers to 4 decimal places)."""
from conftest import AS_OF, assert_matches, load_expected

from trustfit_engine.models import TrustResult, WhatIf
from trustfit_engine.trust import score_trust

BY_ROLE_KEYS = ("score", "band", "confidence", "provisional", "verdict", "dimensions", "reasons")


def test_subros_supplier(subros, cfg):
    result = score_trust(subros, "supplier", cfg, AS_OF)
    assert_matches(result, load_expected("subros_supplier.json"))
    TrustResult.model_validate(result)


def test_subros_supplier_headline(subros, cfg):
    result = score_trust(subros, "supplier", cfg, AS_OF)
    assert (result["score"], result["band"], result["verdict"], result["outlook"]) == (
        87, "Very strong", "Amber", "Watch")


def test_subros_whatif_integrity_clean(subros, cfg):
    what_if = WhatIf(evidence={p: 100 for p in ["A1", "A3", "A4", "A5", "C1", "C2"]},
                     gates={"V1": "passed", "V2": "passed", "V3": "passed"})
    result = score_trust(subros, "supplier", cfg, AS_OF, what_if=what_if)
    assert_matches(result, load_expected("subros_supplier_whatif_integrity_clean.json"))


def test_subros_by_role(subros, cfg):
    actual = {role: {k: v for k, v in score_trust(subros, role, cfg, AS_OF).items() if k in BY_ROLE_KEYS}
              for role in cfg.roles}
    assert_matches(actual, load_expected("subros_by_role.json"))


def test_scoring_does_not_mutate_inputs(subros, cfg):
    before = subros.model_dump()
    score_trust(subros, "supplier", cfg, AS_OF, what_if=WhatIf(evidence={"A1": 100}, gates={"V1": "passed"}))
    assert subros.model_dump() == before
