"""Trust Score v1: a pure port of `score_trust()` in reference/trustfit_reference.py.

No database, network or clock: the scoring date is the `as_of` argument. The arithmetic keeps the
reference's order of operations so results match reference/expected/*.json to 4 decimal places.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from trustfit_engine.config import TrustConfig
from trustfit_engine.models import Company, Evidence, WhatIf
from trustfit_engine.rounding import r4, rhu


def evidence_status(ev: Evidence | None, pid: str, cfg: TrustConfig, as_of: dt.date) -> str:
    """missing | unverified | stale | verified (D1 'excluded' is decided by the caller)."""
    if ev is None:
        return "missing"
    if not ev.verified:
        return "unverified"
    if ev.source_date is None or (as_of - ev.source_date).days > cfg.freshness.max_source_age_days:
        return "stale"
    recheck = cfg.parameters[pid].recheck_days
    if recheck and (ev.checked_at is None or (as_of - ev.checked_at).days > recheck):
        return "stale"
    return "verified"


def band_for(score: float, cfg: TrustConfig) -> str:
    for band in cfg.bands:
        if score >= band.min:
            return band.label
    return cfg.bands[-1].label


def outlook_for(company: Company, cfg: TrustConfig) -> str:
    if not company.trends:
        return "Not assessed"
    dirs = [t.direction for t in company.trends.values()]
    if dirs.count("improving") >= cfg.outlook.positive_if_improving_at_least:
        return "Positive"
    if dirs.count("worsening") >= cfg.outlook.watch_if_worsening_at_least:
        return "Watch"
    return "Stable"


def _check_inputs(company: Company, role: str, cfg: TrustConfig) -> None:
    if role not in cfg.roles:
        raise ValueError(f"unknown role {role!r}; expected one of {list(cfg.roles)}")
    known = {"knockout": cfg.overrides.knockouts, "cap": cfg.overrides.caps, "notch": cfg.overrides.notches}
    for f in company.flags:
        if f.type in known and f.code not in known[f.type]:
            raise ValueError(f"unknown {f.type} flag code {f.code!r}")
    for pid in company.evidence:
        if pid not in cfg.parameters:
            raise ValueError(f"unknown parameter {pid!r}")


def score_trust(company: Company, role: str, cfg: TrustConfig, as_of: dt.date,
                what_if: WhatIf | None = None, fit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Trust Score for one company in one role. `fit` (a Fit result with `category` and `score`)
    is optional; when given, it can only lower the verdict."""
    _check_inputs(company, role, cfg)
    evidence = dict(company.evidence)
    gates = dict(company.gates)
    is_what_if = what_if is not None and bool(what_if.evidence or what_if.gates)
    if is_what_if:
        for pid, level in what_if.evidence.items():
            evidence[pid] = Evidence(level=level, verified=True, source_url="what-if",
                                     source_date=as_of, checked_at=as_of)
        gates.update(what_if.gates)
    flags = company.flags
    fake_reviews = any(f.type == "fake_reviews" for f in flags)
    ov = cfg.overrides

    # 1. knock-outs
    knockouts = [{"code": f.code, "text": ov.knockouts[f.code].label} for f in flags if f.type == "knockout"]
    rows = []
    for pid, spec in cfg.parameters.items():
        ev = evidence.get(pid)
        status = evidence_status(ev, pid, cfg, as_of)
        if pid == "D1" and fake_reviews and status == "verified":
            status = "excluded"
        usable = status == "verified"
        if spec.knockout_at_zero and usable and ev.level == 0:
            knockouts.append({"code": f"{pid}_at_zero", "text": f"{pid} {spec.name} at 0%: {spec.rubric[0]}"})
        pts = cfg.parameter_points(role, pid)
        rows.append({
            "id": pid, "category": spec.category, "points": pts, "status": status,
            "level": ev.level if usable else None,
            "verified_points": pts if usable else 0.0,
            "earned_points": pts * ev.level / 100 if usable else 0.0,
        })

    base = {"company_id": company.id, "role": role, "as_of": as_of.isoformat(),
            "weight_set": cfg.version, "what_if": is_what_if}
    if knockouts:
        return {**base, "eligible": False, "status": "not_eligible", "score": None, "band": None,
                "confidence": None, "provisional": None, "verdict": "Red", "outlook": None,
                "reasons": [{"code": "knockout", "text": k["text"]} for k in knockouts],
                "knockouts": knockouts}

    # 2. categories and dimensions
    def stats(cats: list[str]) -> dict[str, float | None]:
        pts = sum(r["points"] for r in rows if r["category"] in cats)
        ver = sum(r["verified_points"] for r in rows if r["category"] in cats)
        earn = sum(r["earned_points"] for r in rows if r["category"] in cats)
        return {"points": r4(pts), "verified_points": r4(ver), "earned_points": r4(earn),
                "verified_pct": r4(100 * ver / pts) if pts else None,
                "score_pct": r4(100 * earn / ver) if ver else None}

    categories = {cat: {"label": spec.label, **stats([cat])} for cat, spec in cfg.categories.items()}
    dimensions = {d: {"label": spec.label, **stats(spec.categories)} for d, spec in cfg.dimensions.items()}

    verified = sum(r["verified_points"] for r in rows)
    earned = sum(r["earned_points"] for r in rows)
    confidence = verified  # points out of 100
    conf = cfg.confidence

    if confidence < conf.no_score_below:
        return {**base, "eligible": True, "status": "insufficient_data", "score": None, "band": None,
                "confidence": r4(confidence), "provisional": True, "verdict": "Amber",
                "outlook": outlook_for(company, cfg),
                "reasons": [{"code": "insufficient_data",
                             "text": f"Only {rhu(confidence, 1)} of 100 points verified; "
                                     f"no score below {conf.no_score_below}"}],
                "categories": categories, "dimensions": dimensions,
                "next_checks": next_checks(rows, dimensions, cfg, gates)}

    # 3. score, notches, weakest link, caps
    base_score = 100 * earned / verified
    notch_list = [{"code": f.code, "points": ov.notches[f.code].points} for f in flags if f.type == "notch"]
    limit = ov.notch_total_limit
    notches = max(-limit, min(limit, sum(n["points"] for n in notch_list)))
    weakest = min(d["score_pct"] for d in dimensions.values() if d["score_pct"] is not None)
    weakest_limit = weakest + ov.weakest_link_margin
    cap_list = [{"code": f.code, "max_score": ov.caps[f.code].max_score} for f in flags if f.type == "cap"]
    no_cap = 100
    cap = min([c["max_score"] for c in cap_list], default=no_cap)
    final_raw = min(base_score + notches, weakest_limit, cap)
    final = int(rhu(final_raw))
    binding = ("cap" if final_raw == cap and cap < no_cap else
               "weakest_link" if final_raw == weakest_limit else "score")

    # 4. confidence, gates, verdict (each triggered condition adds a reason)
    under = [d for d, v in dimensions.items() if v["verified_pct"] < conf.dimension_provisional_below]
    provisional = confidence < conf.provisional_below or bool(under)
    failed = sorted(g for g, s in gates.items() if s == "failed")
    pending = sorted(g for g in cfg.gates if gates.get(g, "pending") == "pending")
    vr = cfg.verdict

    reasons = []
    if failed:
        reasons.append({"code": "gate_failed", "text": f"Verification gate failed: {', '.join(failed)}"})
    if final < vr.red_below:
        reasons.append({"code": "score_below_red", "text": f"Final score {final} is below {vr.red_below}"})
    if fit is not None and (fit["category"] == "not_a_fit"
                            or (fit["score"] is not None and fit["score"] < vr.fit_red_below)):
        reasons.append({"code": "not_a_fit", "text": "Not a fit for this SME's brief"})
    red = bool(reasons)

    if confidence < conf.provisional_below:
        reasons.append({"code": "low_confidence",
                        "text": f"Only {rhu(confidence, 1)} of 100 points verified, "
                                f"under {conf.provisional_below}"})
    for d in under:
        dim = dimensions[d]
        reasons.append({"code": "dimension_under_verified",
                        "text": f"{dim['label']} is {rhu(dim['verified_pct'], 1)}% verified, "
                                f"under the {conf.dimension_provisional_below}% minimum"})
    if pending:
        reasons.append({"code": "gates_pending", "text": f"Verification gates pending: {', '.join(pending)}"})
    if fake_reviews:
        reasons.append({"code": "fake_reviews",
                        "text": "Fake or manipulated reviews found: D1 excluded, Amber at best"})
    if vr.red_below <= final < vr.green_from:
        reasons.append({"code": "score_adequate", "text": f"Final score {final} is under {vr.green_from}"})
    if fit is not None and fit["category"] == "possible_fit":
        reasons.append({"code": "possible_fit",
                        "text": "Possible fit: gaps to close against this SME's brief"})
    amber = bool(reasons)

    verdict = "Red" if red else ("Amber" if amber else "Green")
    return {
        **base, "eligible": True, "status": "scored", "score": final, "score_raw": r4(final_raw),
        "band": band_for(final, cfg), "confidence": r4(confidence), "provisional": provisional,
        "verdict": verdict, "outlook": outlook_for(company, cfg),
        "base_score": r4(base_score), "notches": notches, "notch_list": notch_list,
        "weakest_dimension": r4(weakest), "weakest_limit": r4(weakest_limit),
        "cap": cap if cap < no_cap else None, "cap_list": cap_list, "binding_limit": binding,
        "categories": categories, "dimensions": dimensions,
        "gates": {g: gates.get(g, "pending") for g in cfg.gates},
        "reasons": reasons,
        "parameters": {r["id"]: {"status": r["status"], "level": r["level"], "points": r4(r["points"])}
                       for r in rows},
        "next_checks": next_checks(rows, dimensions, cfg, gates),
    }


def next_checks(rows: list[dict[str, Any]], dimensions: dict[str, dict[str, Any]], cfg: TrustConfig,
                gates: Mapping[str, str]) -> list[dict[str, Any]]:
    """'What turns it Green': unverified parameters in under-verified dimensions first,
    then the rest, each group by points (largest first), then pending gates.
    `check` is where_to_check text: confidential, strip it for viewers."""
    minimum = cfg.confidence.dimension_provisional_below
    under = {d for d, v in dimensions.items()
             if v["verified_pct"] is not None and v["verified_pct"] < minimum}
    todo = [r for r in rows if r["status"] != "verified"]
    todo.sort(key=lambda r: (cfg.dimension_of(r["category"]) not in under, -r["points"], r["id"]))
    out = [{"type": "parameter", "id": r["id"], "points": r4(r["points"]), "status": r["status"],
            "check": cfg.parameters[r["id"]].where_to_check} for r in todo]
    out += [{"type": "gate", "id": g, "check": spec.check}
            for g, spec in cfg.gates.items() if gates.get(g, "pending") == "pending"]
    return out
