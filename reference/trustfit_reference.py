#!/usr/bin/env python3
"""TrustFit reference implementation, v1.

Small, pure functions that define the expected behaviour of:
  1. the Trust Score   (config/trust_v1.yaml)
  2. the Fit Score     (config/fit_v1.yaml)
  3. the Gap Bridge    (config/gap_bridge_v1.yaml): readiness diagnostic, partner
     matching and the "India entry team"

The production engine (packages/trustfit_engine) must reproduce the outputs in
reference/expected/ exactly. When a rule changes, change the config and this file
together, regenerate the expected outputs, and review the diff.

Usage (needs PyYAML):
  python reference/trustfit_reference.py           # regenerate reference/expected/*.json
  python reference/trustfit_reference.py --check   # exit 1 if outputs differ from the files
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
SEED = ROOT / "seed"
EXPECTED = ROOT / "reference" / "expected"
AS_OF = dt.date(2026, 10, 24)  # fixed scoring date for the golden outputs

CATEGORY_ORDER = "ABCDEFGH"


# ---------------------------------------------------------------- helpers

def load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def load_json(name: str) -> dict:
    return json.loads((SEED / name).read_text(encoding="utf-8"))


def rhu(x: float, nd: int = 0) -> float:
    """Round half up (82.5 -> 83). Python's round() rounds half to even."""
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def r4(x):
    return None if x is None else rhu(x, 4)


_REL = re.compile(r"^today-(\d+)d$")


def resolve_date(value: str | None, as_of: dt.date) -> dt.date | None:
    """ISO date, or 'today-Nd' relative to the scoring date."""
    if value is None:
        return None
    m = _REL.match(value)
    if m:
        return as_of - dt.timedelta(days=int(m.group(1)))
    return dt.date.fromisoformat(value)


def level_from_ratio(ratio: float, table: list) -> int:
    for threshold, level in table:
        if ratio >= threshold - 1e-9:
            return level
    return 0


# ---------------------------------------------------------------- loading

def expand_company(raw: dict, defaults: dict | None, trust_cfg: dict) -> dict:
    """Normalise a seed company into {evidence: {pid: {...}}, ...}."""
    c = dict(raw)
    evidence: dict = {}
    if "trust_evidence" in raw:  # compact demo format
        pids_by_cat = {cat: [p for p, s in trust_cfg["parameters"].items() if s["category"] == cat]
                       for cat in CATEGORY_ORDER}
        for cat, levels in raw["trust_evidence"].items():
            for pid, level in zip(pids_by_cat[cat], levels):
                if level is None:
                    continue
                evidence[pid] = {
                    "level": level,
                    "verified": True,
                    "source_url": defaults["source_url"].format(company_id=raw["id"], parameter_id=pid),
                    "source_date": defaults["source_date"],
                    "checked_at": defaults["checked_at"],
                }
        c["trends"] = {k: {"direction": v} for k, v in raw.get("trends", {}).items()}
    else:  # full format (Subros)
        sources = raw.get("sources", {})
        for pid, ev in raw.get("evidence", {}).items():
            src = sources.get(ev.get("source"), {})
            evidence[pid] = {
                "level": ev["level"],
                "verified": ev["verified"],
                "source_url": src.get("url"),
                "source_date": ev.get("source_date", src.get("date")),
                "checked_at": ev.get("checked_at", raw.get("as_of")),
                "note": ev.get("note"),
            }
    c["evidence"] = evidence
    c.setdefault("flags", [])
    c.setdefault("gates", {})
    c.setdefault("trends", {})
    c.setdefault("profile", {})
    c.setdefault("capabilities", {})
    return c


# ---------------------------------------------------------------- trust

def parameter_points(cfg: dict, role: str, pid: str) -> float:
    spec = cfg["parameters"][pid]
    split = cfg["parameter_splits"].get(role, {}).get(pid, cfg["parameter_splits"]["default"][pid])
    return cfg["category_weights"][role][spec["category"]] * split / 100


def evidence_status(ev: dict | None, spec: dict, cfg: dict, as_of: dt.date) -> str:
    if not ev:
        return "missing"
    if not ev.get("verified"):
        return "unverified"
    src = resolve_date(ev.get("source_date"), as_of)
    if src is None or (as_of - src).days > cfg["freshness"]["max_source_age_days"]:
        return "stale"
    if spec.get("recheck_days"):
        chk = resolve_date(ev.get("checked_at"), as_of)
        if chk is None or (as_of - chk).days > spec["recheck_days"]:
            return "stale"
    return "verified"


def band_for(score: float, cfg: dict) -> str:
    for b in cfg["bands"]:
        if score >= b["min"]:
            return b["label"]
    return cfg["bands"][-1]["label"]


def outlook_for(trends: dict, cfg: dict) -> str:
    if not trends:
        return "Not assessed"
    dirs = [t["direction"] for t in trends.values()]
    o = cfg["outlook"]
    if dirs.count("improving") >= o["positive_if_improving_at_least"]:
        return "Positive"
    if dirs.count("worsening") >= o["watch_if_worsening_at_least"]:
        return "Watch"
    return "Stable"


def score_trust(company: dict, role: str, cfg: dict, as_of: dt.date,
                what_if: dict | None = None, fit: dict | None = None) -> dict:
    """Trust Score for one company in one role. `fit` (a score_fit result) is optional;
    when given, it can only lower the verdict."""
    evidence = dict(company["evidence"])
    gates = dict(company["gates"])
    if what_if:
        for pid, level in what_if.get("evidence", {}).items():
            evidence[pid] = {"level": level, "verified": True, "source_url": "what-if",
                             "source_date": as_of.isoformat(), "checked_at": as_of.isoformat()}
        gates.update(what_if.get("gates", {}))
    flags = company["flags"]
    fake_reviews = any(f["type"] == "fake_reviews" for f in flags)
    ov = cfg["overrides"]

    # 1. knock-outs
    knockouts = [{"code": f["code"], "text": ov["knockouts"][f["code"]]["label"]}
                 for f in flags if f["type"] == "knockout"]
    rows = []
    for pid, spec in cfg["parameters"].items():
        ev = evidence.get(pid)
        status = evidence_status(ev, spec, cfg, as_of)
        if pid == "D1" and fake_reviews and status == "verified":
            status = "excluded"
        if spec.get("knockout_at_zero") and status == "verified" and ev["level"] == 0:
            knockouts.append({"code": f"{pid}_at_zero",
                              "text": f"{pid} {spec['name']} at 0%: {spec['rubric'][0]}"})
        pts = parameter_points(cfg, role, pid)
        usable = status == "verified"
        rows.append({
            "id": pid, "category": spec["category"], "points": pts, "status": status,
            "level": ev["level"] if usable else None,
            "verified_points": pts if usable else 0.0,
            "earned_points": pts * ev["level"] / 100 if usable else 0.0,
        })

    base = {"company_id": company["id"], "role": role, "as_of": as_of.isoformat(),
            "weight_set": cfg["version"], "what_if": bool(what_if)}
    if knockouts:
        return {**base, "eligible": False, "status": "not_eligible", "score": None, "band": None,
                "confidence": None, "provisional": None, "verdict": "Red", "outlook": None,
                "reasons": [{"code": "knockout", "text": k["text"]} for k in knockouts],
                "knockouts": knockouts}

    # 2. categories and dimensions
    def stats(cats):
        pts = sum(r["points"] for r in rows if r["category"] in cats)
        ver = sum(r["verified_points"] for r in rows if r["category"] in cats)
        earn = sum(r["earned_points"] for r in rows if r["category"] in cats)
        return {"points": r4(pts), "verified_points": r4(ver), "earned_points": r4(earn),
                "verified_pct": r4(100 * ver / pts) if pts else None,
                "score_pct": r4(100 * earn / ver) if ver else None}

    categories = {cat: {"label": cfg["categories"][cat]["label"], **stats([cat])} for cat in CATEGORY_ORDER}
    dimensions = {d: {"label": spec["label"], **stats(spec["categories"])}
                  for d, spec in cfg["dimensions"].items()}

    verified = sum(r["verified_points"] for r in rows)
    earned = sum(r["earned_points"] for r in rows)
    confidence = verified  # points out of 100
    conf_cfg = cfg["confidence"]

    if confidence < conf_cfg["no_score_below"]:
        return {**base, "eligible": True, "status": "insufficient_data", "score": None, "band": None,
                "confidence": r4(confidence), "provisional": True, "verdict": "Amber",
                "outlook": outlook_for(company["trends"], cfg),
                "reasons": [{"code": "insufficient_data",
                             "text": f"Only {rhu(confidence, 1)} of 100 points verified; no score below {conf_cfg['no_score_below']}"}],
                "categories": categories, "dimensions": dimensions,
                "next_checks": next_checks(rows, dimensions, cfg, gates)}

    # 3. score, notches, weakest link, caps
    base_score = 100 * earned / verified
    notch_list = [{"code": f["code"], "points": ov["notches"][f["code"]]["points"]}
                  for f in flags if f["type"] == "notch"]
    limit = ov["notch_total_limit"]
    notches = max(-limit, min(limit, sum(n["points"] for n in notch_list)))
    dim_scores = [d["score_pct"] for d in dimensions.values() if d["score_pct"] is not None]
    weakest = min(dim_scores)
    weakest_limit = weakest + ov["weakest_link_margin"]
    cap_list = [{"code": f["code"], "max_score": ov["caps"][f["code"]]["max_score"]}
                for f in flags if f["type"] == "cap"]
    cap = min([c["max_score"] for c in cap_list], default=100)
    final_raw = min(base_score + notches, weakest_limit, cap)
    final = int(rhu(final_raw))
    binding = ("cap" if final_raw == cap and cap < 100 else
               "weakest_link" if final_raw == weakest_limit else "score")

    # 4. confidence, gates, verdict
    under = [d for d, v in dimensions.items() if v["verified_pct"] < conf_cfg["dimension_provisional_below"]]
    provisional = confidence < conf_cfg["provisional_below"] or bool(under)
    failed = sorted(g for g, s in gates.items() if s == "failed")
    pending = sorted(g for g in cfg["gates"] if gates.get(g, "pending") == "pending")

    reasons = []
    if failed:
        reasons.append({"code": "gate_failed", "text": f"Verification gate failed: {', '.join(failed)}"})
    if final < cfg["verdict"]["red_below"]:
        reasons.append({"code": "score_below_red", "text": f"Final score {final} is below {cfg['verdict']['red_below']}"})
    if fit is not None and (fit["category"] == "not_a_fit" or (fit["score"] is not None and fit["score"] < cfg["verdict"]["fit_red_below"])):
        reasons.append({"code": "not_a_fit", "text": "Not a fit for this SME's brief"})
    red = bool(reasons)

    if confidence < conf_cfg["provisional_below"]:
        reasons.append({"code": "low_confidence",
                        "text": f"Only {rhu(confidence, 1)} of 100 points verified, under {conf_cfg['provisional_below']}"})
    for d in under:
        reasons.append({"code": "dimension_under_verified",
                        "text": f"{dimensions[d]['label']} is {rhu(dimensions[d]['verified_pct'], 1)}% verified, under the {conf_cfg['dimension_provisional_below']}% minimum"})
    if pending:
        reasons.append({"code": "gates_pending", "text": f"Verification gates pending: {', '.join(pending)}"})
    if fake_reviews:
        reasons.append({"code": "fake_reviews", "text": "Fake or manipulated reviews found: D1 excluded, Amber at best"})
    if cfg["verdict"]["red_below"] <= final < cfg["verdict"]["green_from"]:
        reasons.append({"code": "score_adequate", "text": f"Final score {final} is under {cfg['verdict']['green_from']}"})
    if fit is not None and fit["category"] == "possible_fit":
        reasons.append({"code": "possible_fit", "text": "Possible fit: gaps to close against this SME's brief"})
    amber = len(reasons) > 0

    verdict = "Red" if red else ("Amber" if amber else "Green")
    return {
        **base, "eligible": True, "status": "scored", "score": final, "score_raw": r4(final_raw),
        "band": band_for(final, cfg), "confidence": r4(confidence), "provisional": provisional,
        "verdict": verdict, "outlook": outlook_for(company["trends"], cfg),
        "base_score": r4(base_score), "notches": notches, "notch_list": notch_list,
        "weakest_dimension": r4(weakest), "weakest_limit": r4(weakest_limit),
        "cap": cap if cap < 100 else None, "cap_list": cap_list, "binding_limit": binding,
        "categories": categories, "dimensions": dimensions,
        "gates": {g: gates.get(g, "pending") for g in cfg["gates"]},
        "reasons": reasons,
        "parameters": {r["id"]: {"status": r["status"], "level": r["level"], "points": r4(r["points"])} for r in rows},
        "next_checks": next_checks(rows, dimensions, cfg, gates),
    }


def next_checks(rows, dimensions, cfg, gates) -> list:
    """'What turns it Green': unverified parameters in under-verified dimensions first,
    then the rest, each group by points (largest first), then pending gates."""
    dim_of = {cat: d for d, s in cfg["dimensions"].items() for cat in s["categories"]}
    under = {d for d, v in dimensions.items()
             if v["verified_pct"] is not None and v["verified_pct"] < cfg["confidence"]["dimension_provisional_below"]}
    todo = [r for r in rows if r["status"] != "verified"]
    todo.sort(key=lambda r: (dim_of[r["category"]] not in under, -r["points"], r["id"]))
    out = [{"type": "parameter", "id": r["id"], "points": r4(r["points"]), "status": r["status"],
            "check": cfg["parameters"][r["id"]]["where_to_check"]} for r in todo]
    out += [{"type": "gate", "id": g, "check": cfg["gates"][g]["check"]}
            for g in cfg["gates"] if gates.get(g, "pending") == "pending"]
    return out


# ---------------------------------------------------------------- fit

def _attr(company: dict, name: str):
    a = company["profile"].get(name)
    if not a:
        return None, False
    return a["value"], bool(a.get("verified"))


def weighted_state_coverage(target: dict, states: list, fcfg: dict) -> float:
    w = fcfg["state_priority_weights"]
    total = w["primary"] * len(target.get("primary", [])) + w["secondary"] * len(target.get("secondary", []))
    got = (w["primary"] * len(set(target.get("primary", [])) & set(states)) +
           w["secondary"] * len(set(target.get("secondary", [])) & set(states)))
    return got / total if total else 0.0


def blocking_conflict(sme: dict, company: dict, fcfg: dict):
    rels, _ = _attr(company, "brand_relationships")
    if rels is None:
        return None
    for r in rels:
        if r["brand"] in sme["competitors"] and r["relation"] in fcfg["conflict"]["blocking_relations"]:
            return r
    return False


def fit_factor_levels(sme: dict, company: dict, fcfg: dict) -> dict:
    """Return {FTn: (level or None, verified)} for one company against one SME brief."""
    out = {}
    voc = fcfg["vocabularies"]
    sectors, v_s = _attr(company, "sectors")
    products, v_p = _attr(company, "products")
    if sectors is None and products is None:
        out["FT1"] = (None, False)
    else:
        sectors, products = sectors or [], products or []
        fam = lambda ps: {f for f, members in voc["product_families"].items() if set(ps) & set(members)}
        sector_match = sme["sector"] in sectors
        product_match = bool(set(sme["products"]) & set(products))
        family_match = bool(fam(sme["products"]) & fam(products))
        related = bool(set(voc["related_sectors"].get(sme["sector"], [])) & set(sectors))
        lvl = (100 if sector_match and product_match else
               75 if product_match or (sector_match and family_match) else
               50 if sector_match else 25 if related else 0)
        out["FT1"] = (lvl, v_s and v_p)

    states, v = _attr(company, "states")
    out["FT2"] = (None, False) if states is None else (
        level_from_ratio(weighted_state_coverage(sme["target_states"], states, fcfg), fcfg["coverage_levels"]), v)

    channels, v = _attr(company, "channels")
    needed = sme.get("channels_needed", [])
    out["FT3"] = (None, False) if channels is None or not needed else (
        level_from_ratio(len(set(needed) & set(channels)) / len(needed), fcfg["coverage_levels"]), v)

    cap, v = _attr(company, "capacity_units_per_month")
    out["FT4"] = (None, False) if cap is None else (
        level_from_ratio(cap / sme["volume_units_per_month"], fcfg["capacity_levels"]), v)

    svc, v = _attr(company, "service_states")
    out["FT5"] = (None, False) if svc is None or sme.get("after_sales_need") == "none" else (
        level_from_ratio(weighted_state_coverage(sme["target_states"], svc, fcfg), fcfg["coverage_levels"]), v)

    rels, v = _attr(company, "brand_relationships")
    if rels is None:
        out["FT6"] = (None, False)
    else:
        comp = set(sme["competitors"])
        rel_types = {r["relation"] for r in rels if r["brand"] in comp}
        lvl = (0 if rel_types & set(fcfg["conflict"]["blocking_relations"]) else
               50 if rel_types & set(fcfg["conflict"]["partial_relations"]) else 100)
        out["FT6"] = (lvl, v)
    return out


def score_fit(sme: dict, company: dict, fcfg: dict) -> dict:
    role = sme["role_sought"]
    importance = {**fcfg["role_default_importance"][role], **sme.get("factor_importance", {})}
    if not sme.get("channels_needed"):
        importance["FT3"] = "irrelevant"
    if sme.get("after_sales_need") == "none":
        importance["FT5"] = "irrelevant"
    eff = {f: spec["base_weight"] * fcfg["importance_multipliers"][importance[f]]
           for f, spec in fcfg["factors"].items()}
    total = sum(eff.values())
    weights = {f: 100 * e / total for f, e in eff.items()}
    levels = fit_factor_levels(sme, company, fcfg)

    known = [f for f in weights if weights[f] > 0 and levels[f][0] is not None]
    known_w = sum(weights[f] for f in known)
    score_raw = sum(weights[f] * levels[f][0] for f in known) / known_w if known_w else None
    confidence = sum(weights[f] for f in known if levels[f][1])

    musts = [f for f, imp in importance.items() if imp == "must"]
    must_zero = [f for f in musts if levels[f][0] == 0]
    must_weak = [f for f in musts if levels[f][0] is None or levels[f][0] < 50]
    conflict = levels["FT6"][0] == 0 and importance["FT6"] != "irrelevant"
    cats = fcfg["categories"]
    if score_raw is None:
        category = "possible_fit"
    elif must_zero or conflict or score_raw < cats["possible_fit"]["min_score"]:
        category = "not_a_fit"
    elif score_raw >= cats["strong_fit"]["min_score"] and not must_weak and confidence >= cats["strong_fit"]["min_confidence"]:
        category = "strong_fit"
    else:
        category = "possible_fit"

    gaps = [f for f in weights if weights[f] > 0 and (levels[f][0] is None or levels[f][0] < 50)]
    return {
        "company_id": company["id"], "sme_id": sme["id"], "role": role,
        "score": int(rhu(score_raw)) if score_raw is not None else None, "score_raw": r4(score_raw),
        "confidence": r4(confidence), "category": category,
        "factors": {f: {"label": fcfg["factors"][f]["label"], "importance": importance[f],
                        "weight": r4(weights[f]), "level": levels[f][0], "verified": levels[f][1]}
                    for f in fcfg["factors"]},
        "gaps": gaps, "competitor_conflict": conflict,
    }


# ---------------------------------------------------------------- gap bridge

def readiness(sme: dict, gcfg: dict) -> dict:
    role = sme["role_sought"]
    out = {}
    for dim, spec in gcfg["dimensions"].items():
        answers = [sme["readiness_answers"][q] for q in spec["questions"]]
        ready = 100 * sum(answers) / (4 * len(answers))
        severity = min(100.0, (100 - ready) * gcfg["relevance"][role][dim])
        label = next(s["label"] for s in gcfg["severity_labels"] if severity >= s["min"] - 1e-9)
        out[dim] = {"label": spec["label"], "jetro_ask": spec["jetro_ask"], "readiness": r4(ready),
                    "severity": r4(severity), "severity_label": label,
                    "covered_by_trustfit": dim in gcfg["covered_by_trustfit"]}
    return out


def capability_strengths(company: dict, sme: dict, trust: dict, fit_levels: dict,
                         fcfg: dict, gcfg: dict) -> dict:
    """{capability: strength 0..1} for one company against one SME."""
    s = {}
    u = gcfg["unverified_factor"]
    params = trust.get("parameters", {})
    for cap, spec in gcfg["capabilities"].items():
        if spec.get("applies_to") and spec["applies_to"] != company["type"]:
            continue
        if spec["source"] == "trust":
            lv = [params[p]["level"] for p in spec["parameters"] if params.get(p, {}).get("status") == "verified"]
            if lv:
                s[cap] = sum(lv) / len(lv) / 100
        elif spec["source"] == "fit":
            lvl, ver = fit_levels[spec["factor"]]
            if lvl is not None:
                s[cap] = lvl / 100 * (1 if ver else u)
        elif spec["source"] == "service_states":
            svc, ver = _attr(company, "service_states")
            if svc is not None:
                lvl = level_from_ratio(weighted_state_coverage(sme["target_states"], svc, fcfg),
                                       fcfg["coverage_levels"])
                s[cap] = lvl / 100 * (1 if ver else u)
        elif spec["source"] == "declared":
            tag = company["capabilities"].get(cap)
            if tag:
                s[cap] = tag["level"] / 100 * (1 if tag["verified"] else u)
    return {k: r4(v) for k, v in s.items() if v > 0}


def gap_cov(strengths_list: list, needs: dict) -> float:
    """Coverage of one gap by a team: each capability is covered by its strongest member."""
    return sum(w * max((s.get(cap, 0) for s in strengths_list), default=0) for cap, w in needs.items())


def team_coverage(strengths_list: list, severities: dict, gcfg: dict) -> float:
    total = sum(severities.values())
    got = sum(sev * gap_cov(strengths_list, gcfg["gap_needs"][g]) for g, sev in severities.items())
    return 100 * got / total if total else 0.0


def gap_bridge(sme: dict, companies: list, tcfg: dict, fcfg: dict, gcfg: dict, as_of: dt.date) -> dict:
    rd = readiness(sme, gcfg)
    severities = {g: v["severity"] for g, v in rd.items()
                  if not v["covered_by_trustfit"] and v["severity"] > 0}
    bcfg = gcfg["bridge"]
    role = sme["role_sought"]

    evaluated = []
    for c in companies:
        is_partner = c["type"] == "business_partner"
        trust_role = role if is_partner else tcfg["service_provider_trust_role"]
        fit = score_fit(sme, c, fcfg) if is_partner and role in c["roles_offered"] else None
        trust = score_trust(c, trust_role, tcfg, as_of)
        combined = score_trust(c, trust_role, tcfg, as_of, fit=fit) if fit else trust
        conflict = blocking_conflict(sme, c, fcfg)
        fl = fit_factor_levels(sme, c, fcfg)
        strengths = capability_strengths(c, sme, trust, fl, fcfg, gcfg)
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
        coverage = team_coverage([strengths], severities, gcfg)
        evaluated.append({
            "company_id": c["id"], "name": c["name"], "type": c["type"],
            "trust_role": trust_role, "trust_score": trust["score"], "trust_verdict": trust["verdict"],
            "provisional": trust.get("provisional"), "fit": fit["score"] if fit else None,
            "fit_category": fit["category"] if fit else None,
            "combined_verdict": combined["verdict"],
            "eligible": not reasons_out, "excluded_because": reasons_out,
            "strengths": strengths, "gap_coverage": r4(coverage),
            "per_gap": {g: r4(gap_cov([strengths], gcfg["gap_needs"][g])) for g in severities},
        })

    eligible = [e for e in evaluated if e["eligible"]]
    by_trust = lambda e: -(e["trust_score"] or 0)

    # primary partners: business partners offering the sought role
    primary = [e for e in eligible if e["fit"] is not None]
    w = bcfg["match_weights"]
    for e in primary:
        e["match"] = r4(w["fit"] * e["fit"] + w["gap_coverage"] * e["gap_coverage"])
    primary.sort(key=lambda e: (-e["match"], by_trust(e), e["name"]))

    # India entry team: best primary partner + greedy supporting service providers
    team, team_strengths = [], []
    if primary:
        team.append({"company_id": primary[0]["company_id"], "slot": "primary", "gain": r4(primary[0]["gap_coverage"])})
        team_strengths.append(primary[0]["strengths"])
    pool = [e for e in eligible if e["type"] == "service_provider"]
    current = team_coverage(team_strengths, severities, gcfg)
    supporters = lambda: sum(1 for t in team if t["slot"] == "support")
    while supporters() < bcfg["max_supporting_partners"] and current < bcfg["target_team_coverage"]:
        best, best_gain = None, 0.0
        for e in sorted(pool, key=lambda e: (by_trust(e), e["name"])):
            if any(t["company_id"] == e["company_id"] for t in team):
                continue
            gain = team_coverage(team_strengths + [e["strengths"]], severities, gcfg) - current
            if gain > best_gain + 1e-9:
                best, best_gain = e, gain
        if best is None or best_gain < bcfg["min_marginal_gain"]:
            break
        team.append({"company_id": best["company_id"], "slot": "support", "gain": r4(best_gain)})
        team_strengths.append(best["strengths"])
        current += best_gain

    # explanations: what each team member brings (capabilities where it is the team's
    # strongest member; ties go to the member added first)
    for i, t in enumerate(team):
        covers = []
        for g in severities:
            for cap, w in gcfg["gap_needs"][g].items():
                mine = team_strengths[i].get(cap, 0)
                if mine > 0 and all(mine > s.get(cap, 0) for s in team_strengths[:i]) \
                        and all(mine >= s.get(cap, 0) for s in team_strengths[i + 1:]):
                    covers.append({"gap": g, "capability": cap,
                                   "label": gcfg["capabilities"][cap]["label"], "strength": mine})
        t["covers"] = covers

    gap_status = {}
    for g in severities:
        cov = gap_cov(team_strengths, gcfg["gap_needs"][g])
        gap_status[g] = {"team_coverage": r4(cov),
                         "status": ("not covered" if cov < bcfg["not_covered_below"] else
                                    "partly covered" if cov < bcfg["partly_covered_below"] else "covered")}

    # per-gap shortlists
    per_gap = {}
    for g, v in rd.items():
        if g not in severities or v["severity_label"] not in bcfg["list_gaps_with_labels"]:
            continue
        ranked = [e for e in eligible if e["per_gap"][g] >= bcfg["per_gap_min_coverage"]]
        ranked.sort(key=lambda e: (-e["per_gap"][g], by_trust(e), e["name"]))
        per_gap[g] = [{"company_id": e["company_id"], "coverage": e["per_gap"][g]} for e in ranked[:bcfg["per_gap_top_n"]]]

    return {
        "sme_id": sme["id"], "as_of": as_of.isoformat(), "readiness": rd,
        "companies": evaluated,
        "primary_ranking": [{"company_id": e["company_id"], "match": e["match"], "fit": e["fit"],
                             "gap_coverage": e["gap_coverage"]} for e in primary],
        "team": team, "team_coverage": r4(current), "gap_status": gap_status, "per_gap": per_gap,
    }


# ---------------------------------------------------------------- main

TRUST_CFG = load_yaml("trust_v1.yaml")
FIT_CFG = load_yaml("fit_v1.yaml")
GAP_CFG = load_yaml("gap_bridge_v1.yaml")


def build_outputs() -> dict:
    subros = expand_company(load_json("subros.json"), None, TRUST_CFG)
    demo = load_json("demo_companies.json")
    companies = [expand_company(c, demo["evidence_defaults"], TRUST_CFG) for c in demo["companies"]]
    sorano = load_json("demo_sme_sorano.json")

    integrity_clean = {"evidence": {p: 100 for p in ["A1", "A3", "A4", "A5", "C1", "C2"]},
                       "gates": {"V1": "passed", "V2": "passed", "V3": "passed"}}
    denso_rival = {"id": "denso-rival-demo", "sector": "auto_components", "products": ["compressors"],
                   "role_sought": "supplier", "target_states": {"primary": ["haryana"], "secondary": []},
                   "channels_needed": [], "volume_units_per_month": 1000, "after_sales_need": "none",
                   "competitors": ["Denso"], "factor_importance": {}}
    return {
        "subros_supplier.json": score_trust(subros, "supplier", TRUST_CFG, AS_OF),
        "subros_supplier_whatif_integrity_clean.json": score_trust(subros, "supplier", TRUST_CFG, AS_OF, what_if=integrity_clean),
        "subros_by_role.json": {r: {k: v for k, v in score_trust(subros, r, TRUST_CFG, AS_OF).items()
                                    if k in ("score", "band", "confidence", "provisional", "verdict", "dimensions", "reasons")}
                                for r in TRUST_CFG["roles"]},
        "subros_fit_denso_rival.json": score_fit(denso_rival, subros, FIT_CFG),
        "demo_gap_bridge_sorano.json": gap_bridge(sorano, companies, TRUST_CFG, FIT_CFG, GAP_CFG, AS_OF),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare with reference/expected instead of writing")
    args = ap.parse_args()
    outputs = build_outputs()
    EXPECTED.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, data in outputs.items():
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        path = EXPECTED / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                print(f"DIFFERS: {name}")
                bad += 1
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
