"""Rule tests from docs/02-trust-score-spec.md ("Rule tests the engine must also pass")."""
import datetime as dt

import pytest
from conftest import AS_OF

from trustfit_engine.config import NotchSpec
from trustfit_engine.models import Company, Evidence, Flag
from trustfit_engine.trust import score_trust

ALL_GATES_PASSED = {"V1": "passed", "V2": "passed", "V3": "passed"}


def make_company(cfg, level=100, levels=None, flags=(), gates=None, trends=None, skip=(), **evidence_kw):
    """Every parameter verified at `level` (fresh), with per-parameter overrides in `levels`."""
    levels = levels or {}
    fresh = AS_OF - dt.timedelta(days=5)
    evidence = {}
    for pid in cfg.parameters:
        if pid in skip:
            continue
        kw = {"verified": True, "source_url": "https://example.com", "source_date": fresh,
              "checked_at": fresh, **evidence_kw.get(pid, {})}
        evidence[pid] = Evidence(level=levels.get(pid, level), **kw)
    return Company(id="test", name="Test (Demo)", fictional=True, evidence=evidence,
                   flags=[Flag(**f) for f in flags],
                   gates=ALL_GATES_PASSED if gates is None else gates,
                   trends=trends or {})


def category_levels(cfg, **by_category):
    return {pid: by_category[spec.category] for pid, spec in cfg.parameters.items()
            if spec.category in by_category}


def test_clean_company_is_green(cfg):
    r = score_trust(make_company(cfg), "supplier", cfg, AS_OF)
    assert (r["score"], r["verdict"], r["confidence"], r["reasons"]) == (100, "Green", 100.0, [])


# ---- knock-outs

def test_knockout_flag_makes_not_eligible(cfg):
    c = make_company(cfg, flags=[{"type": "knockout", "code": "sanctions_match"}])
    r = score_trust(c, "supplier", cfg, AS_OF)
    assert (r["eligible"], r["status"], r["score"], r["verdict"]) == (False, "not_eligible", None, "Red")
    assert r["reasons"][0]["code"] == "knockout"


def test_a3_verified_at_zero_is_a_knockout(cfg):
    r = score_trust(make_company(cfg, levels={"A3": 0}), "supplier", cfg, AS_OF)
    assert (r["eligible"], r["score"], r["verdict"]) == (False, None, "Red")
    assert [k["code"] for k in r["knockouts"]] == ["A3_at_zero"]


def test_unverified_zero_on_knockout_parameter_is_not_a_knockout(cfg):
    c = make_company(cfg, levels={"A3": 0}, A3={"verified": False})
    r = score_trust(c, "supplier", cfg, AS_OF)
    assert r["eligible"] is True and r["parameters"]["A3"]["status"] == "unverified"


# ---- confidence

def test_confidence_below_40_gives_no_score(cfg):
    only_b = [pid for pid, s in cfg.parameters.items() if s.category != "B"]
    r = score_trust(make_company(cfg, skip=only_b), "supplier", cfg, AS_OF)
    assert (r["status"], r["score"], r["verdict"]) == ("insufficient_data", None, "Amber")
    assert r["confidence"] == 20.0
    assert r["next_checks"]


def test_missing_is_not_zero(cfg):
    r = score_trust(make_company(cfg, skip=["B6", "D1"]), "supplier", cfg, AS_OF)
    assert r["base_score"] == 100.0
    assert r["confidence"] == 100 - 2.0 - 2.5  # B6 = 20 x 10%, D1 = 10 x 25%


# ---- limits

def test_cap_50_binds_and_makes_red(cfg):
    c = make_company(cfg, level=75, levels=category_levels(cfg, A=100),
                     flags=[{"type": "cap", "code": "adverse_audit_opinion"}])
    r = score_trust(c, "supplier", cfg, AS_OF)
    assert r["base_score"] == 78.75
    assert (r["score"], r["cap"], r["binding_limit"], r["verdict"]) == (50, 50, "cap", "Red")
    assert "score_below_red" in [x["code"] for x in r["reasons"]]


def test_lowest_cap_wins(cfg):
    c = make_company(cfg, flags=[{"type": "cap", "code": "asset_attachment_24m"},
                                 {"type": "cap", "code": "going_concern_uncertainty"}])
    r = score_trust(c, "supplier", cfg, AS_OF)
    assert (r["score"], r["cap"]) == (60, 60)


def test_notches_are_clamped_to_plus_minus_8(cfg):
    test_cfg = cfg.model_copy(deep=True)
    test_cfg.overrides.notches["test_plus_5"] = NotchSpec(label="test", points=5, check="test")
    flags = [{"type": "notch", "code": "strategic_shareholder_10"},
             {"type": "notch", "code": "strategic_shareholder_10"},
             {"type": "notch", "code": "test_plus_5"}]  # +3 +3 +5 = +11
    r = score_trust(make_company(test_cfg, level=75, flags=flags), "supplier", test_cfg, AS_OF)
    assert sum(n["points"] for n in r["notch_list"]) == 11
    assert r["notches"] == 8
    assert r["score_raw"] == 83.0


def test_negative_notches_are_clamped(cfg):
    flags = [{"type": "notch", "code": "promoter_group_default"}] * 2  # -10
    r = score_trust(make_company(cfg, level=75, flags=flags), "supplier", cfg, AS_OF)
    assert r["notches"] == -8 and r["score"] == 67


def test_weakest_link_limits_the_score(cfg):
    # Integrity = (15 x 50 + 15 x 75) / 30 = 62.5; base = 88.75; limit 77.5 -> 78 (round half up)
    c = make_company(cfg, levels=category_levels(cfg, A=50, C=75))
    r = score_trust(c, "supplier", cfg, AS_OF)
    assert (r["base_score"], r["weakest_dimension"], r["weakest_limit"]) == (88.75, 62.5, 77.5)
    assert (r["score"], r["binding_limit"]) == (78, "weakest_link")


# ---- freshness

def test_a3_checked_31_days_ago_is_stale(cfg):
    fresh = score_trust(make_company(cfg, A3={"checked_at": AS_OF - dt.timedelta(days=30)}),
                        "supplier", cfg, AS_OF)
    stale = score_trust(make_company(cfg, A3={"checked_at": AS_OF - dt.timedelta(days=31)}),
                        "supplier", cfg, AS_OF)
    assert fresh["parameters"]["A3"]["status"] == "verified"
    assert stale["parameters"]["A3"]["status"] == "stale"
    assert stale["parameters"]["A3"]["level"] is None
    assert stale["confidence"] == fresh["confidence"] - 3.75  # supplier A3 = 15 x 25%


def test_source_older_than_730_days_is_stale(cfg):
    c = make_company(cfg, B2={"source_date": AS_OF - dt.timedelta(days=731)})
    assert score_trust(c, "supplier", cfg, AS_OF)["parameters"]["B2"]["status"] == "stale"
    c = make_company(cfg, B2={"source_date": AS_OF - dt.timedelta(days=730)})
    assert score_trust(c, "supplier", cfg, AS_OF)["parameters"]["B2"]["status"] == "verified"


def test_unverified_evidence_stays_out_of_the_score(cfg):
    c = make_company(cfg, levels={"B2": 0}, B2={"verified": False})
    r = score_trust(c, "supplier", cfg, AS_OF)
    assert r["base_score"] == 100.0 and r["confidence"] == 97.0


# ---- fake reviews and gates

def test_fake_reviews_excludes_d1_and_caps_at_amber(cfg):
    r = score_trust(make_company(cfg, flags=[{"type": "fake_reviews", "code": "review_pattern"}]),
                    "supplier", cfg, AS_OF)
    assert r["parameters"]["D1"]["status"] == "excluded"
    assert r["verdict"] == "Amber"
    assert "fake_reviews" in [x["code"] for x in r["reasons"]]


def test_failed_gate_is_red(cfg):
    r = score_trust(make_company(cfg, gates={**ALL_GATES_PASSED, "V2": "failed"}), "supplier", cfg, AS_OF)
    assert r["verdict"] == "Red"
    assert r["reasons"][0]["code"] == "gate_failed"


def test_pending_gate_is_amber_at_best(cfg):
    r = score_trust(make_company(cfg, gates={"V1": "passed", "V2": "passed"}), "supplier", cfg, AS_OF)
    assert r["verdict"] == "Amber"
    assert r["gates"]["V3"] == "pending"
    assert r["next_checks"][-1] == {"type": "gate", "id": "V3", "check": cfg.gates["V3"].check}


def test_score_between_55_and_70_is_amber(cfg):
    r = score_trust(make_company(cfg, level=75, levels={"B2": 0, "B4": 0, "F5": 0}), "supplier", cfg, AS_OF)
    assert 55 <= r["score"] < 70 and r["verdict"] == "Amber"


# ---- fit can only lower the verdict

@pytest.mark.parametrize(("fit", "verdict"), [
    ({"category": "strong_fit", "score": 90}, "Green"),
    ({"category": "possible_fit", "score": 65}, "Amber"),
    ({"category": "not_a_fit", "score": 80}, "Red"),
    ({"category": "possible_fit", "score": 45}, "Red"),
])
def test_fit_can_only_lower_the_verdict(cfg, fit, verdict):
    assert score_trust(make_company(cfg), "supplier", cfg, AS_OF, fit=fit)["verdict"] == verdict


# ---- outlook

@pytest.mark.parametrize(("directions", "outlook"), [
    ([], "Not assessed"),
    (["improving"] * 3 + ["stable"] * 2, "Positive"),
    (["worsening"] * 3 + ["improving"] * 2, "Watch"),
    (["improving", "improving", "worsening", "worsening", "stable"], "Stable"),
])
def test_outlook(cfg, directions, outlook):
    trends = {sig: {"direction": d} for sig, d in zip(cfg.outlook.signals, directions, strict=False)}
    r = score_trust(make_company(cfg, trends=trends), "supplier", cfg, AS_OF)
    assert r["outlook"] == outlook and r["verdict"] == "Green"  # outlook never changes the verdict


# ---- next checks and input validation

def test_next_checks_put_under_verified_dimensions_first(cfg):
    integrity = [pid for pid, s in cfg.parameters.items() if s.category in ("A", "C")]
    r = score_trust(make_company(cfg, skip=integrity[:-1] + ["B7"]), "supplier", cfg, AS_OF)
    ids = [x["id"] for x in r["next_checks"] if x["type"] == "parameter"]
    assert ids[-1] == "B7"
    assert set(ids[:-1]) == set(integrity[:-1])
    pts = [x["points"] for x in r["next_checks"][:-1]]
    assert pts == sorted(pts, reverse=True)


def test_unknown_flag_code_is_rejected(cfg):
    with pytest.raises(ValueError, match="no_such_cap"):
        score_trust(make_company(cfg, flags=[{"type": "cap", "code": "no_such_cap"}]), "supplier", cfg, AS_OF)


def test_unknown_role_is_rejected(cfg):
    with pytest.raises(ValueError, match="role"):
        score_trust(make_company(cfg), "landlord", cfg, AS_OF)
