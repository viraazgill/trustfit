"""Readiness and the Gap Bridge for one SME. Every number is computed by trustfit_engine; this module adds
names, labels and one-line reasons for the SME-facing pages."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.errors import ApiError
from app.schemas import ReadinessOut, ViewerBridge
from app.services.fit import _hash, config_versions, fit_config, to_engine_sme
from app.services.scoring import to_engine, trust_config
from app.settings import scoring_date, settings
from trustfit_engine import models as engine
from trustfit_engine.bridge import check_answers, gap_bridge, readiness
from trustfit_engine.bridge_config import BridgeConfig, load_bridge_config
from trustfit_engine.fit import attribute
from trustfit_engine.rounding import rhu

FIT_FACTOR_ATTRIBUTES = {"FT1": ("sectors", "products"), "FT2": ("states",)}


@lru_cache
def bridge_config() -> BridgeConfig:
    return load_bridge_config(settings.CONFIG_DIR / "gap_bridge_v1.yaml")


def save_answers(db: Session, sme: models.Sme, answers: dict[str, int]) -> models.Sme:
    try:
        check_answers(engine.Sme(id=sme.id, sector=sme.sector, role_sought=sme.role_sought,
                                 readiness_answers=answers), bridge_config())
    except ValueError as exc:
        raise ApiError(422, str(exc), field="answers") from exc
    sme.readiness_answers = answers
    db.commit()
    return sme


def readiness_out(sme: models.Sme) -> ReadinessOut:
    answered = bool(sme.readiness_answers)
    dims = readiness(to_engine_sme(sme), bridge_config()) if answered else {}
    return ReadinessOut(sme_id=sme.id, answered=answered, answers=sme.readiness_answers, dimensions=dims)


def capability_verified(company: engine.Company, capability: str, cfg: BridgeConfig) -> bool:
    """Whether a capability strength rests on verified data (Trust-derived strengths always do)."""
    spec = cfg.capabilities[capability]
    if spec.source == "trust":
        return True
    if spec.source == "fit":
        return all(attribute(company, a)[1] for a in FIT_FACTOR_ATTRIBUTES.get(spec.factor, ()))
    if spec.source == "service_states":
        return attribute(company, "service_states")[1]
    tag = company.capabilities.get(capability) or {}
    return bool(tag.get("verified"))


def _strength_text(label: str, strength: float, verified: bool) -> str:
    return f"{label} {int(rhu(100 * strength))}%, {'verified' if verified else 'not yet verified'}"


def run_bridge(db: Session, sme: models.Sme, user: models.User) -> ViewerBridge:
    """The full Gap Bridge for one SME, over every company in the database. Saved as a `bridge` run."""
    if not sme.readiness_answers:
        raise ApiError(409, "Answer the readiness check first", field="readiness_answers")
    tcfg, fcfg, gcfg, as_of = trust_config(), fit_config(), bridge_config(), scoring_date()
    rows = list(db.scalars(select(models.Company).order_by(models.Company.id)))
    companies = [to_engine(c) for c in rows]
    es = to_engine_sme(sme)
    try:
        result: dict[str, Any] = gap_bridge(es, companies, tcfg, fcfg, gcfg, as_of)
    except ValueError as exc:
        raise ApiError(422, str(exc)) from exc
    versions = config_versions(trust=tcfg.version, fit=fcfg.version, gap_bridge=gcfg.version)
    db.add(models.ScoreRun(
        kind="bridge", sme_id=sme.id, role=sme.role_sought, config_version=versions, as_of=as_of,
        inputs_hash=_hash({"sme": es.model_dump(mode="json"), "as_of": as_of.isoformat(),
                           "companies": [c.model_dump(mode="json") for c in companies]}),
        is_what_if=False, result=result, created_by=user.id))
    db.commit()

    by_id = {c.id: c for c in companies}
    fictional = {c.id: c.fictional for c in rows}
    for c in result["companies"]:
        c["fictional"] = fictional[c["company_id"]]
    for member in result["team"]:
        for cover in member["covers"]:
            cover["verified"] = capability_verified(by_id[member["company_id"]], cover["capability"], gcfg)
    strengths = {c["company_id"]: c["strengths"] for c in result["companies"]}
    for gap, entries in result["per_gap"].items():
        needs = gcfg.gap_needs[gap]
        for entry in entries:
            s = strengths[entry["company_id"]]
            cap = max(needs, key=lambda k: needs[k] * s.get(k, 0))  # ties: first listed need
            verified = capability_verified(by_id[entry["company_id"]], cap, gcfg)
            entry["reason"] = _strength_text(gcfg.capabilities[cap].label, s[cap], verified)
    return ViewerBridge(**result, config_version=versions, disclaimer=tcfg.disclaimer)
