"""Fit Score v1: a pure port of `fit_factor_levels()` and `score_fit()` in reference/trustfit_reference.py.

Fit rates one Indian company against one SME's brief. Pass its result into `score_trust(..., fit=...)`
for the combined verdict: Fit can lower a Trust verdict, never raise it.
"""
from __future__ import annotations

from typing import Any

from trustfit_engine.fit_config import FitConfig
from trustfit_engine.models import Company, Sme
from trustfit_engine.rounding import r4, rhu

Level = tuple[int | None, bool]  # (level or None when unknown, verified)
_EPS = 1e-9


def attribute(company: Company, name: str) -> tuple[Any, bool]:
    """A profile attribute is {value, verified, source_url}; missing or empty -> (None, False)."""
    a = company.profile.get(name)
    if not a:
        return None, False
    return a["value"], bool(a.get("verified"))


def level_from_ratio(ratio: float, table: list[tuple[float, int]]) -> int:
    """The first [threshold, level] row whose threshold the ratio meets or beats."""
    for threshold, level in table:
        if ratio >= threshold - _EPS:
            return level
    return 0


def weighted_state_coverage(target: dict[str, list[str]], states: list[str], cfg: FitConfig) -> float:
    w = cfg.state_priority_weights
    primary, secondary = target.get("primary", []), target.get("secondary", [])
    total = w.primary * len(primary) + w.secondary * len(secondary)
    got = w.primary * len(set(primary) & set(states)) + w.secondary * len(set(secondary) & set(states))
    return got / total if total else 0.0


def blocking_conflict(sme: Sme, company: Company, cfg: FitConfig) -> dict[str, str] | bool | None:
    """The first blocking relation with one of the SME's competitors; False if none; None if unknown."""
    rels, _ = attribute(company, "brand_relationships")
    if rels is None:
        return None
    for r in rels:
        if r["brand"] in sme.competitors and r["relation"] in cfg.conflict.blocking_relations:
            return r
    return False


def _families(products: list[str], cfg: FitConfig) -> set[str]:
    return {f for f, members in cfg.vocabularies.product_families.items() if set(products) & set(members)}


def fit_factor_levels(sme: Sme, company: Company, cfg: FitConfig) -> dict[str, Level]:
    """{FTn: (level or None, verified)} for one company against one SME brief."""
    out: dict[str, Level] = {}
    voc = cfg.vocabularies

    sectors, v_s = attribute(company, "sectors")
    products, v_p = attribute(company, "products")
    if sectors is None and products is None:
        out["FT1"] = (None, False)
    else:
        sectors, products = sectors or [], products or []
        sector_match = sme.sector in sectors
        product_match = bool(set(sme.products) & set(products))
        family_match = bool(_families(sme.products, cfg) & _families(products, cfg))
        related = bool(set(voc.related_sectors.get(sme.sector, [])) & set(sectors))
        lvl = (100 if sector_match and product_match else
               75 if product_match or (sector_match and family_match) else
               50 if sector_match else 25 if related else 0)
        out["FT1"] = (lvl, v_s and v_p)

    states, v = attribute(company, "states")
    out["FT2"] = (None, False) if states is None else (
        level_from_ratio(weighted_state_coverage(sme.target_states, states, cfg), cfg.coverage_levels), v)

    channels, v = attribute(company, "channels")
    needed = sme.channels_needed
    out["FT3"] = (None, False) if channels is None or not needed else (
        level_from_ratio(len(set(needed) & set(channels)) / len(needed), cfg.coverage_levels), v)

    capacity, v = attribute(company, "capacity_units_per_month")
    out["FT4"] = (None, False) if capacity is None or not sme.volume_units_per_month else (
        level_from_ratio(capacity / sme.volume_units_per_month, cfg.capacity_levels), v)

    service, v = attribute(company, "service_states")
    out["FT5"] = (None, False) if service is None or sme.after_sales_need == "none" else (
        level_from_ratio(weighted_state_coverage(sme.target_states, service, cfg), cfg.coverage_levels), v)

    rels, v = attribute(company, "brand_relationships")
    if rels is None:
        out["FT6"] = (None, False)
    else:
        rel_types = {r["relation"] for r in rels if r["brand"] in set(sme.competitors)}
        lvl = (0 if rel_types & set(cfg.conflict.blocking_relations) else
               50 if rel_types & set(cfg.conflict.partial_relations) else 100)
        out["FT6"] = (lvl, v)
    return out


def factor_importance(sme: Sme, cfg: FitConfig) -> dict[str, str]:
    """Role defaults, overridden by the brief; FT3 and FT5 become irrelevant when the brief needs neither."""
    if sme.role_sought not in cfg.role_default_importance:
        raise ValueError(f"unknown role_sought {sme.role_sought!r}; expected one of {list(cfg.role_default_importance)}")
    importance = {**cfg.role_default_importance[sme.role_sought], **sme.factor_importance}
    for f, imp in importance.items():
        if f not in cfg.factors:
            raise ValueError(f"unknown fit factor {f!r}")
        if imp not in cfg.importance_multipliers:
            raise ValueError(f"{f}: unknown importance {imp!r}")
    if not sme.channels_needed:
        importance["FT3"] = "irrelevant"
    if sme.after_sales_need == "none":
        importance["FT5"] = "irrelevant"
    return importance


def factor_weights(importance: dict[str, str], cfg: FitConfig) -> dict[str, float]:
    """Effective weight = base weight x importance multiplier, rescaled to sum to 100."""
    eff = {f: spec.base_weight * cfg.importance_multipliers[importance[f]] for f, spec in cfg.factors.items()}
    total = sum(eff.values())
    if not total:
        raise ValueError("every fit factor is irrelevant; at least one must count")
    return {f: 100 * e / total for f, e in eff.items()}


def score_fit(sme: Sme, company: Company, cfg: FitConfig) -> dict[str, Any]:
    """Fit Score, fit confidence, category, factor breakdown and gaps for one company and one SME."""
    importance = factor_importance(sme, cfg)
    weights = factor_weights(importance, cfg)
    levels = fit_factor_levels(sme, company, cfg)

    known = [f for f in weights if weights[f] > 0 and levels[f][0] is not None]
    known_w = sum(weights[f] for f in known)
    score_raw = sum(weights[f] * levels[f][0] for f in known) / known_w if known_w else None
    confidence = sum(weights[f] for f in known if levels[f][1])

    musts = [f for f, imp in importance.items() if imp == "must"]
    must_zero = [f for f in musts if levels[f][0] == 0]
    must_weak = [f for f in musts if levels[f][0] is None or levels[f][0] < 50]
    conflict = levels["FT6"][0] == 0 and importance["FT6"] != "irrelevant"
    cats = cfg.categories
    if score_raw is None:
        category = "possible_fit"
    elif must_zero or conflict or score_raw < cats["possible_fit"].min_score:
        category = "not_a_fit"
    elif (score_raw >= cats["strong_fit"].min_score and not must_weak
          and confidence >= cats["strong_fit"].min_confidence):
        category = "strong_fit"
    else:
        category = "possible_fit"

    gaps = [f for f in weights if weights[f] > 0 and (levels[f][0] is None or levels[f][0] < 50)]
    return {
        "company_id": company.id, "sme_id": sme.id, "role": sme.role_sought,
        "score": int(rhu(score_raw)) if score_raw is not None else None, "score_raw": r4(score_raw),
        "confidence": r4(confidence), "category": category,
        "factors": {f: {"label": cfg.factors[f].label, "importance": importance[f],
                        "weight": r4(weights[f]), "level": levels[f][0], "verified": levels[f][1]}
                    for f in cfg.factors},
        "gaps": gaps, "competitor_conflict": conflict,
    }
