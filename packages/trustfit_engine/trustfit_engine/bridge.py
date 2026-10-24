"""Gap Bridge v1: a pure port of `readiness()`, `capability_strengths()` and `gap_bridge()` in
reference/trustfit_reference.py.

The SME's readiness answers become gaps with severities; every Indian company gets capability strengths
against this SME; trusted, eligible companies are ranked and a greedy "India entry team" covers the most
gap severity. The arithmetic keeps the reference's order of operations so results match the golden file.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from trustfit_engine.bridge_config import BridgeConfig
from trustfit_engine.config import TrustConfig
from trustfit_engine.fit import (
    Level,
    attribute,
    blocking_conflict,
    fit_factor_levels,
    level_from_ratio,
    score_fit,
    weighted_state_coverage,
)
from trustfit_engine.fit_config import FitConfig
from trustfit_engine.models import Company, Sme
from trustfit_engine.rounding import r4
from trustfit_engine.trust import score_trust

_EPS = 1e-9
Strengths = dict[str, float]


# ---------------------------------------------------------------- readiness

def check_answers(sme: Sme, cfg: BridgeConfig) -> None:
    missing = sorted(set(cfg.questions) - set(sme.readiness_answers))
    if missing:
        raise ValueError(f"readiness answers missing for {', '.join(missing)}")
    for q, a in sme.readiness_answers.items():
        if q not in cfg.questions:
            raise ValueError(f"unknown readiness question {q!r}")
        if a not in cfg.answer_scale:
            raise ValueError(f"{q}: answer {a!r} must be one of {sorted(cfg.answer_scale)}")


def readiness(sme: Sme, cfg: BridgeConfig) -> dict[str, dict[str, Any]]:
    """Per dimension: readiness = mean(answers) / max x 100; severity = (100 - readiness) x relevance,
    capped at 100, with its label."""
    check_answers(sme, cfg)
    if sme.role_sought not in cfg.relevance:
        raise ValueError(f"no readiness relevance for role {sme.role_sought!r}")
    out = {}
    for dim, spec in cfg.dimensions.items():
        answers = [sme.readiness_answers[q] for q in spec.questions]
        ready = 100 * sum(answers) / (cfg.max_answer * len(answers))
        severity = min(100.0, (100 - ready) * cfg.relevance[sme.role_sought][dim])
        label = next(s.label for s in cfg.severity_labels if severity >= s.min - _EPS)
        out[dim] = {"label": spec.label, "jetro_ask": spec.jetro_ask, "readiness": r4(ready),
                    "severity": r4(severity), "severity_label": label,
                    "covered_by_trustfit": dim in cfg.covered_by_trustfit}
    return out


# ---------------------------------------------------------------- capabilities and coverage

def capability_strengths(company: Company, sme: Sme, trust: dict[str, Any], fit_levels: dict[str, Level],
                         fcfg: FitConfig, cfg: BridgeConfig) -> Strengths:
    """{capability: strength 0..1} for one company against one SME (strengths of 0 left out)."""
    s: dict[str, float] = {}
    u = cfg.unverified_factor
    params = trust.get("parameters", {})
    for cap, spec in cfg.capabilities.items():
        if spec.applies_to and spec.applies_to != company.type:
            continue
        if spec.source == "trust":
            lv = [params[p]["level"] for p in spec.parameters
                  if params.get(p, {}).get("status") == "verified"]
            if lv:
                s[cap] = sum(lv) / len(lv) / 100
        elif spec.source == "fit":
            lvl, ver = fit_levels[spec.factor]
            if lvl is not None:
                s[cap] = lvl / 100 * (1 if ver else u)
        elif spec.source == "service_states":
            svc, ver = attribute(company, "service_states")
            if svc is not None:
                coverage = weighted_state_coverage(sme.target_states, svc, fcfg)
                lvl = level_from_ratio(coverage, fcfg.coverage_levels)
                s[cap] = lvl / 100 * (1 if ver else u)
        elif spec.source == "declared":
            tag = company.capabilities.get(cap)
            if tag:
                s[cap] = tag["level"] / 100 * (1 if tag["verified"] else u)
    return {k: r4(v) for k, v in s.items() if v > 0}


def gap_cov(strengths_list: list[Strengths], needs: dict[str, float]) -> float:
    """Coverage of one gap by a team: each capability is covered by its strongest member."""
    return sum(w * max((s.get(cap, 0) for s in strengths_list), default=0) for cap, w in needs.items())


def team_coverage(strengths_list: list[Strengths], severities: dict[str, float], cfg: BridgeConfig) -> float:
    """Severity-weighted gap coverage of a team, in percent."""
    total = sum(severities.values())
    got = sum(sev * gap_cov(strengths_list, cfg.gap_needs[g]) for g, sev in severities.items())
    return 100 * got / total if total else 0.0


# ---------------------------------------------------------------- the bridge

def _evaluate(c: Company, sme: Sme, severities: dict[str, float], tcfg: TrustConfig, fcfg: FitConfig,
              cfg: BridgeConfig, as_of: dt.date) -> dict[str, Any]:
    """Trust, Fit, eligibility and capability strengths for one company against this SME."""
    is_partner = c.type == "business_partner"
    trust_role = sme.role_sought if is_partner else tcfg.service_provider_trust_role
    fit = score_fit(sme, c, fcfg) if is_partner and sme.role_sought in c.roles_offered else None
    trust = score_trust(c, trust_role, tcfg, as_of)
    combined = score_trust(c, trust_role, tcfg, as_of, fit=fit) if fit else trust
    conflict = blocking_conflict(sme, c, fcfg)
    strengths = capability_strengths(c, sme, trust, fit_factor_levels(sme, c, fcfg), fcfg, cfg)

    reasons_out = []
    if not trust["eligible"]:
        reasons_out.append("knock-out")
    elif trust["status"] == "insufficient_data":
        reasons_out.append("insufficient verified data")
    elif trust["verdict"] == "Red":
        reasons_out.append("Trust verdict Red")
    if conflict:
        reasons_out.append(f"competitor conflict: {conflict['relation']} {conflict['brand']}")
    if fit and fit["category"] == "not_a_fit" and not conflict:
        reasons_out.append("not a fit")
    return {
        "company_id": c.id, "name": c.name, "type": c.type,
        "trust_role": trust_role, "trust_score": trust["score"], "trust_verdict": trust["verdict"],
        "provisional": trust.get("provisional"), "fit": fit["score"] if fit else None,
        "fit_category": fit["category"] if fit else None,
        "combined_verdict": combined["verdict"],
        "eligible": not reasons_out, "excluded_because": reasons_out,
        "strengths": strengths, "gap_coverage": r4(team_coverage([strengths], severities, cfg)),
        "per_gap": {g: r4(gap_cov([strengths], cfg.gap_needs[g])) for g in severities},
    }


def _greedy_team(primary: list[dict[str, Any]], pool: list[dict[str, Any]], severities: dict[str, float],
                 cfg: BridgeConfig) -> tuple[list[dict[str, Any]], list[Strengths], float]:
    """Top primary partner, then up to max_supporting_partners service providers, each the largest gain
    in team coverage (ties: higher Trust, then name); stop under min_marginal_gain or at the target."""
    rules = cfg.bridge
    by_trust = lambda e: -(e["trust_score"] or 0)  # noqa: E731 - mirrors the reference
    team: list[dict[str, Any]] = []
    team_strengths: list[Strengths] = []
    if primary:
        lead = primary[0]
        team.append({"company_id": lead["company_id"], "slot": "primary", "gain": r4(lead["gap_coverage"])})
        team_strengths.append(primary[0]["strengths"])
    current = team_coverage(team_strengths, severities, cfg)
    supporters = lambda: sum(1 for t in team if t["slot"] == "support")  # noqa: E731
    while supporters() < rules.max_supporting_partners and current < rules.target_team_coverage:
        best, best_gain = None, 0.0
        for e in sorted(pool, key=lambda e: (by_trust(e), e["name"])):
            if any(t["company_id"] == e["company_id"] for t in team):
                continue
            gain = team_coverage(team_strengths + [e["strengths"]], severities, cfg) - current
            if gain > best_gain + _EPS:
                best, best_gain = e, gain
        if best is None or best_gain < rules.min_marginal_gain:
            break
        team.append({"company_id": best["company_id"], "slot": "support", "gain": r4(best_gain)})
        team_strengths.append(best["strengths"])
        current += best_gain
    return team, team_strengths, current


def _what_each_brings(team: list[dict[str, Any]], team_strengths: list[Strengths],
                      severities: dict[str, float], cfg: BridgeConfig) -> None:
    """Capabilities where a member is the team's strongest (ties go to the member added first)."""
    for i, t in enumerate(team):
        covers = []
        for g in severities:
            for cap in cfg.gap_needs[g]:
                mine = team_strengths[i].get(cap, 0)
                if mine > 0 and all(mine > s.get(cap, 0) for s in team_strengths[:i]) \
                        and all(mine >= s.get(cap, 0) for s in team_strengths[i + 1:]):
                    covers.append({"gap": g, "capability": cap, "label": cfg.capabilities[cap].label,
                                   "strength": mine})
        t["covers"] = covers


def gap_bridge(sme: Sme, companies: list[Company], tcfg: TrustConfig, fcfg: FitConfig, cfg: BridgeConfig,
               as_of: dt.date) -> dict[str, Any]:
    """Readiness, every company's eligibility and strengths, the primary ranking, the India entry team,
    gap status and per-gap shortlists for one SME."""
    rd = readiness(sme, cfg)
    severities = {g: v["severity"] for g, v in rd.items()
                  if not v["covered_by_trustfit"] and v["severity"] > 0}
    rules = cfg.bridge

    evaluated = [_evaluate(c, sme, severities, tcfg, fcfg, cfg, as_of) for c in companies]
    eligible = [e for e in evaluated if e["eligible"]]
    by_trust = lambda e: -(e["trust_score"] or 0)  # noqa: E731

    # primary partners: business partners offering the sought role (they have a Fit result)
    primary = [e for e in eligible if e["fit"] is not None]
    w = rules.match_weights
    for e in primary:
        e["match"] = r4(w.fit * e["fit"] + w.gap_coverage * e["gap_coverage"])
    primary.sort(key=lambda e: (-e["match"], by_trust(e), e["name"]))

    pool = [e for e in eligible if e["type"] == "service_provider"]
    team, team_strengths, current = _greedy_team(primary, pool, severities, cfg)
    _what_each_brings(team, team_strengths, severities, cfg)

    gap_status = {}
    for g in severities:
        cov = gap_cov(team_strengths, cfg.gap_needs[g])
        gap_status[g] = {"team_coverage": r4(cov),
                         "status": ("not covered" if cov < rules.not_covered_below else
                                    "partly covered" if cov < rules.partly_covered_below else "covered")}

    per_gap = {}
    for g, v in rd.items():
        if g not in severities or v["severity_label"] not in rules.list_gaps_with_labels:
            continue
        ranked = [e for e in eligible if e["per_gap"][g] >= rules.per_gap_min_coverage]
        ranked.sort(key=lambda e: (-e["per_gap"][g], by_trust(e), e["name"]))
        per_gap[g] = [{"company_id": e["company_id"], "coverage": e["per_gap"][g]}
                      for e in ranked[:rules.per_gap_top_n]]

    return {
        "sme_id": sme.id, "as_of": as_of.isoformat(), "readiness": rd,
        "companies": evaluated,
        "primary_ranking": [{"company_id": e["company_id"], "match": e["match"], "fit": e["fit"],
                             "gap_coverage": e["gap_coverage"]} for e in primary],
        "team": team, "team_coverage": r4(current), "gap_status": gap_status, "per_gap": per_gap,
    }
