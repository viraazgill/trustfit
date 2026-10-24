"""Gap Bridge: the Sorano golden output (docs/04-gap-bridge-spec.md), the greedy team's stop rules and
every exclusion reason."""
import datetime as dt

import pytest
import yaml
from conftest import AS_OF, CONFIG_DIR, assert_matches, load_expected

from trustfit_engine.bridge import gap_bridge, readiness
from trustfit_engine.bridge_config import BridgeConfig, load_bridge_config
from trustfit_engine.models import Company, Evidence, Flag, Sme

ALL_GATES_PASSED = {"V1": "passed", "V2": "passed", "V3": "passed"}


@pytest.fixture(scope="session")
def gcfg() -> BridgeConfig:
    return load_bridge_config(CONFIG_DIR / "gap_bridge_v1.yaml")


def run(sme, companies, cfg, fit_cfg, gcfg):
    return gap_bridge(sme, companies, cfg, fit_cfg, gcfg, AS_OF)


# ---- golden

def test_sorano_matches_the_golden_output(sorano, demo_companies, cfg, fit_cfg, gcfg):
    result = run(sorano, demo_companies, cfg, fit_cfg, gcfg)
    assert_matches(result, load_expected("demo_gap_bridge_sorano.json"))


def test_sorano_headline_numbers(sorano, demo_companies, cfg, fit_cfg, gcfg):
    result = run(sorano, demo_companies, cfg, fit_cfg, gcfg)
    assert [t["company_id"] for t in result["team"]] == [
        "deccan-instrumentation", "certipath", "nihon-india-bridge", "swift-cargo"]
    assert round(result["team_coverage"]) == 82
    excluded = {c["company_id"]: c["excluded_because"] for c in result["companies"] if not c["eligible"]}
    assert excluded == {"western-flow": ["competitor conflict: represents Flowtek (Demo)"],
                        "konkan-trade": ["knock-out"]}
    assert result["gap_status"]["R3"]["status"] == "not covered"


def test_sorano_readiness(sorano, gcfg):
    rd = readiness(sorano, gcfg)
    assert {d: (v["readiness"], v["severity"], v["severity_label"]) for d, v in rd.items()} == {
        "R1": (41.6667, 70.0, "critical"), "R2": (12.5, 87.5, "critical"), "R3": (66.6667, 26.6667, "minor"),
        "R4": (25.0, 90.0, "critical"), "R5": (50.0, 50.0, "significant"), "R6": (25.0, 90.0, "critical")}
    assert [d for d, v in rd.items() if v["covered_by_trustfit"]] == ["R2"]


# ---- synthetic companies for the rules

def sme(**kw) -> Sme:
    answers = {q: 0 for q in ("R1.1", "R1.2", "R1.3", "R2.1", "R2.2", "R3.1", "R3.2", "R3.3", "R4.1", "R4.2",
                              "R4.3", "R5.1", "R5.2", "R6.1", "R6.2", "R6.3")}
    base = dict(id="sme", sector="industrial_instruments", products=["flow_meters"],
                role_sought="distributor", target_states={"primary": ["maharashtra"], "secondary": []},
                channels_needed=["industrial_b2b"],
                volume_units_per_month=100, after_sales_need="full", competitors=["Rival (Demo)"],
                readiness_answers=answers)
    return Sme(**{**base, **kw})


def company(cfg, cid, type="service_provider", caps=None, profile=None, levels=None, only=None, flags=(),
            gates=None) -> Company:
    """Fresh verified evidence at 100 (G2/G4 at 0 so service providers don't pick up language strengths),
    with per-parameter overrides; `only` keeps just those parameters."""
    fresh = AS_OF - dt.timedelta(days=5)
    levels = {"G2": 0, "G4": 0, **(levels or {})}
    evidence = {pid: Evidence(level=levels.get(pid, 100), verified=True, source_url="https://example.com",
                              source_date=fresh, checked_at=fresh)
                for pid in cfg.parameters if only is None or pid in only}
    return Company(id=cid, name=f"{cid} (Demo)", fictional=True, type=type,
                   roles_offered=["distributor"] if type == "business_partner" else [],
                   evidence=evidence, flags=[Flag(**f) for f in flags],
                   gates=ALL_GATES_PASSED if gates is None else gates,
                   capabilities={k: {"level": v, "verified": True} for k, v in (caps or {}).items()},
                   profile={k: {"value": v, "verified": True} for k, v in (profile or {}).items()})


GOOD_PARTNER = dict(sectors=["industrial_instruments"], products=["flow_meters"], states=["maharashtra"],
                    channels=["industrial_b2b"], capacity_units_per_month=500, service_states=["maharashtra"],
                    brand_relationships=[])


def team_ids(result):
    return [t["company_id"] for t in result["team"]]


# ---- greedy stop rules

def test_at_most_three_supporting_partners(cfg, fit_cfg, gcfg):
    providers = [company(cfg, f"p{i}", caps={cap: 100}) for i, cap in enumerate(
        ["market_research", "certification_support", "warehousing_logistics", "customs_clearance"], start=1)]
    result = run(sme(), providers, cfg, fit_cfg, gcfg)
    assert len(result["team"]) == gcfg.bridge.max_supporting_partners == 3
    assert result["team_coverage"] < gcfg.bridge.target_team_coverage
    assert all(t["slot"] == "support" and t["gain"] >= gcfg.bridge.min_marginal_gain for t in result["team"])
    assert team_ids(result)[0] == "p2"  # the largest gain goes first


def test_a_gain_under_the_minimum_is_not_added(cfg, fit_cfg, gcfg):
    # business_interpretation covers 0.2 of R5: 100 x 0.2 / 480 x 100 = 4.17 points, under 5
    result = run(sme(), [company(cfg, "small", caps={"business_interpretation": 100})], cfg, fit_cfg, gcfg)
    assert result["team"] == [] and result["team_coverage"] == 0


def test_the_team_stops_once_it_reaches_the_target(cfg, fit_cfg, gcfg):
    providers = [company(cfg, "p1", caps={"market_research": 100}),
                 company(cfg, "p2", caps={"certification_support": 100})]
    rules = gcfg.bridge.model_copy(update={"target_team_coverage": 5.0})
    low_target = gcfg.model_copy(update={"bridge": rules})
    assert team_ids(run(sme(), providers, cfg, fit_cfg, low_target)) == ["p2"]


def test_the_top_primary_partner_leads_the_team(cfg, fit_cfg, gcfg):
    partner = company(cfg, "partner", type="business_partner", profile=GOOD_PARTNER)
    result = run(sme(), [partner, company(cfg, "p1", caps={"market_research": 100})], cfg, fit_cfg, gcfg)
    assert result["team"][0]["slot"] == "primary" and result["team"][0]["company_id"] == "partner"
    assert result["primary_ranking"][0]["company_id"] == "partner"


def test_ties_go_to_higher_trust_then_name(cfg, fit_cfg, gcfg):
    weaker = company(cfg, "a-weaker", caps={"certification_support": 100}, levels={"B1": 25, "B2": 25})
    stronger = company(cfg, "b-stronger", caps={"certification_support": 100})
    assert team_ids(run(sme(), [weaker, stronger], cfg, fit_cfg, gcfg))[0] == "b-stronger"


# ---- exclusion reasons

def excluded(cfg, fit_cfg, gcfg, c):
    entry = run(sme(), [c], cfg, fit_cfg, gcfg)["companies"][0]
    assert entry["eligible"] is False
    return entry["excluded_because"]


def test_knockout_is_excluded(cfg, fit_cfg, gcfg):
    c = company(cfg, "ko", flags=[{"type": "knockout", "code": "sanctions_match"}])
    assert excluded(cfg, fit_cfg, gcfg, c) == ["knock-out"]


def test_insufficient_data_is_excluded(cfg, fit_cfg, gcfg):
    c = company(cfg, "thin", only={"A1", "A2", "B1"})
    assert excluded(cfg, fit_cfg, gcfg, c) == ["insufficient verified data"]


def test_trust_red_is_excluded(cfg, fit_cfg, gcfg):
    c = company(cfg, "failed-gate", gates={"V1": "failed", "V2": "passed", "V3": "passed"})
    assert excluded(cfg, fit_cfg, gcfg, c) == ["Trust verdict Red"]


def test_competitor_conflict_is_excluded(cfg, fit_cfg, gcfg):
    rival = {**GOOD_PARTNER, "brand_relationships": [{"brand": "Rival (Demo)", "relation": "exclusive"}]}
    c = company(cfg, "rival-rep", type="business_partner", profile=rival)
    assert excluded(cfg, fit_cfg, gcfg, c) == ["competitor conflict: exclusive Rival (Demo)"]


def test_not_a_fit_is_excluded(cfg, fit_cfg, gcfg):
    c = company(cfg, "far-away", type="business_partner", profile={**GOOD_PARTNER, "states": ["kerala"]})
    assert excluded(cfg, fit_cfg, gcfg, c) == ["not a fit"]


def test_per_gap_lists_only_eligible_companies_above_the_minimum(sorano, demo_companies, cfg, fit_cfg, gcfg):
    result = run(sorano, demo_companies, cfg, fit_cfg, gcfg)
    eligible = {c["company_id"] for c in result["companies"] if c["eligible"]}
    minimum = gcfg.bridge.per_gap_min_coverage
    for rows in result["per_gap"].values():
        assert len(rows) <= gcfg.bridge.per_gap_top_n
        assert all(r["company_id"] in eligible and r["coverage"] >= minimum for r in rows)
    assert "R3" not in result["per_gap"]  # minor gaps get no shortlist


# ---- inputs and config

FULL_ANSWERS = sme().readiness_answers


@pytest.mark.parametrize(("answers", "message"), [
    ({"R1.1": 2}, "missing"),                         # most questions unanswered
    ({**FULL_ANSWERS, "R1.1": 5}, "must be one of"),  # off the 0-4 scale
    ({**FULL_ANSWERS, "R9.9": 1}, "unknown"),         # not a question
])
def test_invalid_readiness_answers_are_rejected(gcfg, answers, message):
    with pytest.raises(ValueError, match=message):
        readiness(sme(readiness_answers=answers), gcfg)


def _raw():
    return yaml.safe_load((CONFIG_DIR / "gap_bridge_v1.yaml").read_text(encoding="utf-8"))


def test_real_bridge_config_loads(gcfg):
    assert gcfg.version == "v1" and len(gcfg.questions) == 16 and gcfg.max_answer == 4


@pytest.mark.parametrize(("mutate", "message"), [
    (lambda c: c["gap_needs"]["R1"].__setitem__("market_research", 0.5), "must sum to 1"),
    (lambda c: c["gap_needs"]["R4"].__setitem__("telepathy", 0.0), "unknown capability"),
    (lambda c: c["relevance"]["supplier"].pop("R3"), "relevance.supplier"),
    (lambda c: c["severity_labels"].reverse(), "severity_labels"),
    (lambda c: c["gap_needs"].pop("R6"), "missing"),
    (lambda c: c["bridge"]["list_gaps_with_labels"].append("catastrophic"), "unknown severity label"),
])
def test_invalid_bridge_config_fails_loudly(mutate, message):
    raw = _raw()
    mutate(raw)
    with pytest.raises(ValueError, match=message):
        BridgeConfig.model_validate(raw)
