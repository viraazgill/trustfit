"""Fit Score: golden outputs (docs/03-fit-score-spec.md) and the factor rules."""
import pytest
import yaml
from conftest import AS_OF, CONFIG_DIR, assert_matches, load_expected

from trustfit_engine.fit import (
    factor_importance,
    factor_weights,
    fit_factor_levels,
    level_from_ratio,
    score_fit,
)
from trustfit_engine.fit_config import FitConfig
from trustfit_engine.models import Company, Sme
from trustfit_engine.trust import score_trust

# The SME the reference uses for subros_fit_denso_rival.json
DENSO_RIVAL = Sme(id="denso-rival-demo", sector="auto_components", products=["compressors"],
                  role_sought="supplier", target_states={"primary": ["haryana"], "secondary": []},
                  channels_needed=[], volume_units_per_month=1000, after_sales_need="none",
                  competitors=["Denso"])
VERDICT_ORDER = {"Green": 0, "Amber": 1, "Red": 2}


def brief(**kw) -> Sme:
    base = dict(id="sme", sector="industrial_instruments", products=["flow_meters"],
                role_sought="distributor",
                target_states={"primary": ["maharashtra", "gujarat"], "secondary": ["karnataka"]},
                channels_needed=["industrial_b2b", "epc_projects"], volume_units_per_month=100,
                after_sales_need="full", competitors=["Rival (Demo)"])
    return Sme(**{**base, **kw})


def company(**attrs) -> Company:
    """Profile attributes given as values, verified unless passed as (value, False)."""
    profile = {}
    for k, v in attrs.items():
        value, verified = v if isinstance(v, tuple) else (v, True)
        profile[k] = {"value": value, "verified": verified}
    return Company(id="c", name="C (Demo)", fictional=True, roles_offered=["distributor"], profile=profile)


STRONG = dict(sectors=["industrial_instruments"], products=["flow_meters"],
              states=["maharashtra", "gujarat", "karnataka"], channels=["industrial_b2b", "epc_projects"],
              capacity_units_per_month=200, service_states=["maharashtra", "gujarat", "karnataka"],
              brand_relationships=[])


# ---- golden numbers

def test_subros_against_a_denso_rival(subros, fit_cfg):
    result = score_fit(DENSO_RIVAL, subros, fit_cfg)
    assert_matches(result, load_expected("subros_fit_denso_rival.json"))
    assert (result["score"], result["category"]) == (71, "not_a_fit")


def test_sorano_fit_per_company(sorano, demo_companies, fit_cfg):
    expected = {c["company_id"]: c for c in load_expected("demo_gap_bridge_sorano.json")["companies"]}
    partners = [c for c in demo_companies
                if c.type == "business_partner" and sorano.role_sought in c.roles_offered]
    assert {c.id for c in partners} == {"deccan-instrumentation", "western-flow", "sabarmati-process",
                                        "konkan-trade"}
    for c in partners:
        result = score_fit(sorano, c, fit_cfg)
        want = (expected[c.id]["fit"], expected[c.id]["fit_category"])
        assert (result["score"], result["category"]) == want, c.id


def test_sorano_headline_results(sorano, demo_companies, fit_cfg):
    by_id = {c.id: c for c in demo_companies}
    assert score_fit(sorano, by_id["deccan-instrumentation"], fit_cfg)["score"] == 90
    western = score_fit(sorano, by_id["western-flow"], fit_cfg)
    assert (western["score"], western["category"], western["competitor_conflict"]) == (54, "not_a_fit", True)
    sabarmati = score_fit(sorano, by_id["sabarmati-process"], fit_cfg)
    assert (sabarmati["score"], sabarmati["category"]) == (51, "possible_fit")
    assert (sabarmati["factors"]["FT3"]["importance"], sabarmati["factors"]["FT3"]["level"]) == ("must", 25)


def test_combined_verdicts_match_reference_and_never_rise(sorano, demo_companies, cfg, fit_cfg):
    expected = {c["company_id"]: c for c in load_expected("demo_gap_bridge_sorano.json")["companies"]}
    for c in demo_companies:
        if c.type != "business_partner":
            continue
        fit = score_fit(sorano, c, fit_cfg)
        trust = score_trust(c, sorano.role_sought, cfg, AS_OF)
        combined = score_trust(c, sorano.role_sought, cfg, AS_OF, fit=fit)
        assert combined["verdict"] == expected[c.id]["combined_verdict"], c.id
        assert VERDICT_ORDER[combined["verdict"]] >= VERDICT_ORDER[trust["verdict"]], c.id


def test_distributor_effective_weights(sorano, fit_cfg):
    weights = factor_weights(factor_importance(sorano, fit_cfg), fit_cfg)
    assert {f: round(w, 2) for f, w in weights.items()} == {
        "FT1": 17.54, "FT2": 28.07, "FT3": 28.07, "FT4": 5.26, "FT5": 7.02, "FT6": 14.04}
    assert sum(weights.values()) == pytest.approx(100)


# ---- threshold edges

@pytest.mark.parametrize(("ratio", "level"), [
    (1.0, 100), (0.9, 100), (0.8999, 75), (0.7, 75), (0.5, 50), (0.4999, 25), (0.25, 25), (0.2499, 0),
    (0.0, 0)])
def test_coverage_levels_at_their_edges(fit_cfg, ratio, level):
    assert level_from_ratio(ratio, fit_cfg.coverage_levels) == level


@pytest.mark.parametrize(("capacity", "level"),
                         [(150, 100), (149, 75), (120, 75), (100, 50), (99, 25), (70, 25), (69, 0)])
def test_capacity_levels_at_their_edges(fit_cfg, capacity, level):
    c = company(capacity_units_per_month=capacity)
    levels = fit_factor_levels(brief(volume_units_per_month=100), c, fit_cfg)
    assert levels["FT4"] == (level, True)


def test_weighted_state_coverage_counts_primary_twice(fit_cfg):
    # primary maharashtra + gujarat (2 x 2) + secondary karnataka (1) = 5
    both_primaries = company(states=["maharashtra", "gujarat"])  # 4 / 5 = 0.8
    assert fit_factor_levels(brief(), both_primaries, fit_cfg)["FT2"] == (75, True)
    secondary_only = company(states=["karnataka"])  # 1 / 5 = 0.2
    assert fit_factor_levels(brief(), secondary_only, fit_cfg)["FT2"] == (0, True)


@pytest.mark.parametrize(("attrs", "level"), [
    (dict(sectors=["industrial_instruments"], products=["flow_meters"]), 100),
    (dict(sectors=["machinery"], products=["flow_meters"]), 75),                     # a shared product
    (dict(sectors=["industrial_instruments"], products=["pressure_gauges"]), 75),   # same sector + family
    (dict(sectors=["industrial_instruments"], products=["process_valves"]), 50),    # same sector only
    (dict(sectors=["water_treatment"], products=["dosing_pumps"]), 25),             # a related sector
    (dict(sectors=["food_processing"], products=[]), 0),
])
def test_ft1_sector_and_product_levels(fit_cfg, attrs, level):
    assert fit_factor_levels(brief(), company(**attrs), fit_cfg)["FT1"][0] == level


@pytest.mark.parametrize(("relation", "level"), [("represents", 0), ("owner", 0), ("shareholder_10", 0),
                                                  ("exclusive", 0), ("supplies", 50)])
def test_ft6_competitor_relations(fit_cfg, relation, level):
    rival = company(brand_relationships=[{"brand": "Rival (Demo)", "relation": relation}])
    assert fit_factor_levels(brief(), rival, fit_cfg)["FT6"] == (level, True)
    other = company(brand_relationships=[{"brand": "Someone else", "relation": relation}])
    assert fit_factor_levels(brief(), other, fit_cfg)["FT6"] == (100, True)


# ---- importance and categories

def test_strong_fit(fit_cfg):
    result = score_fit(brief(), company(**STRONG), fit_cfg)
    assert (result["score"], result["category"], result["gaps"]) == (100, "strong_fit", [])
    assert result["confidence"] == pytest.approx(100)


def test_ft3_is_irrelevant_without_channels(fit_cfg):
    result = score_fit(brief(channels_needed=[]), company(**{**STRONG, "channels": []}), fit_cfg)
    assert (result["factors"]["FT3"]["importance"], result["factors"]["FT3"]["weight"]) == ("irrelevant", 0)
    assert result["category"] == "strong_fit"


def test_ft5_is_irrelevant_without_after_sales_need(fit_cfg):
    result = score_fit(brief(after_sales_need="none"), company(**STRONG), fit_cfg)
    ft5 = result["factors"]["FT5"]
    assert (ft5["importance"], ft5["weight"], ft5["level"]) == ("irrelevant", 0, None)
    assert result["category"] == "strong_fit"


def test_an_unknown_must_have_blocks_strong_fit(fit_cfg):
    attrs = {k: v for k, v in STRONG.items() if k != "channels"}  # FT3 is a distributor must-have
    result = score_fit(brief(), company(**attrs), fit_cfg)
    assert (result["score"], result["category"]) == (100, "possible_fit") and "FT3" in result["gaps"]


def test_a_must_have_at_zero_is_not_a_fit(fit_cfg):
    result = score_fit(brief(), company(**{**STRONG, "states": ["kerala"]}), fit_cfg)  # FT2 must-have -> 0
    assert (result["factors"]["FT2"]["level"], result["category"]) == (0, "not_a_fit")


def test_low_fit_confidence_blocks_strong_fit(fit_cfg):
    unverified = {k: (v, False) for k, v in STRONG.items()}
    result = score_fit(brief(), company(**unverified), fit_cfg)
    assert (result["score"], result["confidence"], result["category"]) == (100, 0, "possible_fit")


def test_competitor_conflict_ignored_when_ft6_is_irrelevant(fit_cfg):
    c = company(**{**STRONG, "brand_relationships": [{"brand": "Rival (Demo)", "relation": "represents"}]})
    assert score_fit(brief(), c, fit_cfg)["category"] == "not_a_fit"
    result = score_fit(brief(factor_importance={"FT6": "irrelevant"}), c, fit_cfg)
    assert (result["category"], result["competitor_conflict"]) == ("strong_fit", False)


def test_brief_overrides_role_defaults(fit_cfg):
    importance = factor_importance(brief(factor_importance={"FT4": "must"}), fit_cfg)
    assert (importance["FT4"], importance["FT2"]) == ("must", "must")


def test_no_known_factor_gives_no_score(fit_cfg):
    result = score_fit(brief(), company(), fit_cfg)
    assert (result["score"], result["category"], result["confidence"]) == (None, "possible_fit", 0.0)


def test_strong_fit_never_raises_a_trust_verdict(subros, cfg):
    trust = score_trust(subros, "supplier", cfg, AS_OF)
    combined = score_trust(subros, "supplier", cfg, AS_OF, fit={"category": "strong_fit", "score": 100})
    assert combined["verdict"] == trust["verdict"] == "Amber"


@pytest.mark.parametrize("bad", [{"factor_importance": {"FT9": "must"}},
                                 {"factor_importance": {"FT1": "maybe"}},
                                 {"role_sought": "landlord"}])
def test_invalid_brief_is_rejected(fit_cfg, bad):
    with pytest.raises(ValueError):
        score_fit(brief(**bad), company(**STRONG), fit_cfg)


# ---- config validation

def _raw():
    return yaml.safe_load((CONFIG_DIR / "fit_v1.yaml").read_text(encoding="utf-8"))


def test_real_fit_config_loads(fit_cfg):
    assert fit_cfg.version == "v1" and sum(f.base_weight for f in fit_cfg.factors.values()) == 100


@pytest.mark.parametrize(("mutate", "message"), [
    (lambda c: c["role_default_importance"]["supplier"].pop("FT1"), "role_default_importance.supplier"),
    (lambda c: c["coverage_levels"].reverse(), "highest to lowest"),
    (lambda c: c["capacity_levels"][0].__setitem__(1, 90), "not one of"),
    (lambda c: c["categories"].pop("strong_fit"), "categories must be"),
    (lambda c: c["conflict"]["partial_relations"].append("owner"), "both blocking and partial"),
    (lambda c: c["vocabularies"]["related_sectors"].__setitem__("space", ["machinery"]), "unknown sector"),
])
def test_invalid_fit_config_fails_loudly(mutate, message):
    raw = _raw()
    mutate(raw)
    with pytest.raises(ValueError, match=message):
        FitConfig.model_validate(raw)
