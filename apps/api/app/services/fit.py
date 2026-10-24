"""SME briefs and Fit: database rows to engine models and back. Every score is computed by trustfit_engine."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from functools import lru_cache
from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.auth import ROLE_RANK
from app.errors import ApiError
from app.schemas import SmeIn, SmeOut, SmePatch, TrustSummary, ViewerFit
from app.services.scoring import to_engine, trust_config, viewer_reasons
from app.settings import scoring_date, settings
from trustfit_engine import models as engine
from trustfit_engine.fit import blocking_conflict, score_fit
from trustfit_engine.fit_config import FitConfig, load_fit_config
from trustfit_engine.trust import score_trust

SME_FIELDS = ("name", "country", "city", "employees", "description", "sector", "products", "role_sought",
              "target_states", "channels_needed", "volume_units_per_month", "after_sales_need",
              "competitors", "factor_importance")


@lru_cache
def fit_config() -> FitConfig:
    return load_fit_config(settings.CONFIG_DIR / "fit_v1.yaml")


# ---------------------------------------------------------------- access

def is_staff(user: models.User) -> bool:
    return ROLE_RANK[user.role] >= ROLE_RANK["analyst"]


def can_read(sme: models.Sme, user: models.User) -> bool:
    """Staff see every SME; a viewer sees their own briefs and the fictional demo SMEs."""
    return is_staff(user) or sme.fictional or sme.owner_id == user.id


def can_write(sme: models.Sme, user: models.User) -> bool:
    return is_staff(user) or sme.owner_id == user.id


def get_sme(db: Session, sme_id: str, user: models.User, write: bool = False) -> models.Sme:
    sme = db.get(models.Sme, sme_id)
    if sme is None or not can_read(sme, user):
        raise ApiError(404, f"No SME {sme_id!r}")
    if write and not can_write(sme, user):
        raise ApiError(403, "Only the SME's owner or an analyst can change this brief")
    return sme


def sme_out(sme: models.Sme, user: models.User) -> SmeOut:
    return SmeOut(
        id=sme.id, name=sme.name, fictional=sme.fictional, country=sme.country, city=sme.city,
        employees=sme.employees, description=sme.description, sector=sme.sector,
        products=list(sme.products), role_sought=sme.role_sought, target_states=sme.target_states,
        channels_needed=list(sme.channels_needed),
        volume_units_per_month=sme.volume_units_per_month, after_sales_need=sme.after_sales_need,
        competitors=list(sme.competitors), factor_importance=sme.factor_importance,
        readiness_answers=sme.readiness_answers, mine=can_write(sme, user),
    )


# ---------------------------------------------------------------- briefs

def check_brief(values: dict[str, Any]) -> None:
    """Vocabulary checks against config/fit_v1.yaml (Pydantic already checked the shapes)."""
    cfg = fit_config()
    voc = cfg.vocabularies
    if "sector" in values and values["sector"] not in voc.sectors:
        raise ApiError(422, f"Unknown sector {values['sector']!r}", field="sector")
    if "target_states" in values:
        ts = values["target_states"]
        unknown = sorted((set(ts.get("primary", [])) | set(ts.get("secondary", []))) - set(voc.states))
        if unknown:
            raise ApiError(422, f"Unknown state(s): {', '.join(unknown)}", field="target_states")
        if set(ts.get("primary", [])) & set(ts.get("secondary", [])):
            raise ApiError(422, "A state can't be both primary and secondary", field="target_states")
        if not ts.get("primary"):
            raise ApiError(422, "Pick at least one primary target state", field="target_states")
    if "channels_needed" in values:
        unknown = sorted(set(values["channels_needed"]) - set(voc.channels))
        if unknown:
            raise ApiError(422, f"Unknown channel(s): {', '.join(unknown)}", field="channels_needed")
    if "factor_importance" in values:
        unknown = sorted(set(values["factor_importance"]) - set(cfg.factors))
        if unknown:
            raise ApiError(422, f"Unknown fit factor(s): {', '.join(unknown)}", field="factor_importance")


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "sme"
    return f"{base}-{secrets.token_hex(3)}"


def create_sme(db: Session, body: SmeIn, user: models.User) -> models.Sme:
    values = body.model_dump()
    check_brief(values)
    sme = models.Sme(id=_slug(body.name), fictional=False, owner_id=user.id, readiness_answers={}, **values)
    db.add(sme)
    db.commit()
    return sme


def update_sme(db: Session, sme: models.Sme, body: SmePatch) -> models.Sme:
    values = body.model_dump(exclude_unset=True)
    check_brief(values)
    for key, value in values.items():
        setattr(sme, key, value)
    db.commit()
    return sme


def to_engine_sme(sme: models.Sme) -> engine.Sme:
    return engine.Sme(id=sme.id, sector=sme.sector, products=list(sme.products), role_sought=sme.role_sought,
                      target_states=dict(sme.target_states), channels_needed=list(sme.channels_needed),
                      volume_units_per_month=sme.volume_units_per_month,
                      after_sales_need=sme.after_sales_need or "none", competitors=list(sme.competitors),
                      factor_importance=dict(sme.factor_importance),
                      readiness_answers=dict(sme.readiness_answers))


# ---------------------------------------------------------------- fit

def config_versions(**versions: str) -> str:
    """Every config a run used, e.g. 'trust:v1 fit:v1' (stored in score_runs.config_version)."""
    return " ".join(f"{name}:{v}" for name, v in versions.items())


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def run_fit(db: Session, sme: models.Sme, company: models.Company, user: models.User) -> ViewerFit:
    """Fit for one SME and one business partner, with the combined verdict. Saved as a `fit` run."""
    if company.type != "business_partner" or sme.role_sought not in company.roles_offered:
        raise ApiError(422, f"{company.name} is not a business partner offering the {sme.role_sought} role; "
                            "Fit applies only to those", field="company_id")
    tcfg, fcfg, as_of = trust_config(), fit_config(), scoring_date()
    ec, es = to_engine(company), to_engine_sme(sme)
    try:
        fit = score_fit(es, ec, fcfg)
    except ValueError as exc:
        raise ApiError(422, str(exc)) from exc
    trust = score_trust(ec, sme.role_sought, tcfg, as_of)
    combined = score_trust(ec, sme.role_sought, tcfg, as_of, fit=fit)
    conflict = blocking_conflict(es, ec, fcfg) if fit["competitor_conflict"] else None
    category = fcfg.categories[fit["category"]]

    db.add(models.ScoreRun(
        kind="fit", company_id=company.id, sme_id=sme.id, role=sme.role_sought,
        config_version=config_versions(trust=tcfg.version, fit=fcfg.version), as_of=as_of,
        inputs_hash=_hash({"company": ec.model_dump(mode="json"), "sme": es.model_dump(mode="json"),
                           "as_of": as_of.isoformat()}),
        is_what_if=False, result={"fit": fit, "combined_verdict": combined["verdict"]}, created_by=user.id))
    db.commit()

    return ViewerFit(
        company_id=company.id, company_name=company.name, fictional=company.fictional, sme_id=sme.id,
        role=sme.role_sought, score=fit["score"], score_raw=fit["score_raw"], confidence=fit["confidence"],
        category=fit["category"], category_label=category.label, action=category.action,
        factors=fit["factors"], gaps=fit["gaps"], competitor_conflict=fit["competitor_conflict"],
        conflict=conflict or None,
        trust=TrustSummary(role=sme.role_sought, **{k: trust[k] for k in (
            "eligible", "status", "score", "band", "confidence", "provisional", "verdict")}),
        combined_verdict=combined["verdict"], reasons=viewer_reasons(combined, tcfg),
        disclaimer=tcfg.disclaimer,
    )
