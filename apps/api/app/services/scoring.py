"""Bridge between the database and the pure engine. Every score is computed by trustfit_engine."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.errors import ApiError
from app.schemas import LatestScore, ViewerCategory, ViewerPending, ViewerReason, ViewerTrustReport
from app.settings import scoring_date, settings
from trustfit_engine import models as engine
from trustfit_engine.config import TrustConfig, load_trust_config
from trustfit_engine.rounding import r4
from trustfit_engine.trust import evidence_status, score_trust


@lru_cache
def trust_config() -> TrustConfig:
    return load_trust_config(settings.CONFIG_DIR / "trust_v1.yaml")


def get_company(db: Session, company_id: str) -> models.Company:
    company = db.get(models.Company, company_id)
    if company is None:
        raise ApiError(404, f"No company {company_id!r}")
    return company


def check_role(role: str) -> str:
    if role not in trust_config().roles:
        roles = ", ".join(trust_config().roles)
        raise ApiError(422, f"Unknown role {role!r}; use one of {roles}", field="role")
    return role


def to_engine(company: models.Company) -> engine.Company:
    return engine.Company(
        id=company.id, name=company.name, fictional=company.fictional, type=company.type,
        roles_offered=list(company.roles_offered),
        evidence={e.parameter_id: engine.Evidence(level=e.level, verified=e.verified, source_url=e.source_url,
                                                  source_date=e.source_date, checked_at=e.checked_at,
                                                  note=e.note)
                  for e in company.evidence},
        flags=[engine.Flag(type=f.type, code=f.code, note=f.note, source_url=f.source_url)
               for f in company.flags],
        gates=dict(company.gates), trends=dict(company.trends),
        profile=dict(company.profile), capabilities=dict(company.capabilities),
    )


def inputs_hash(company: engine.Company, role: str, what_if: engine.WhatIf | None, as_of: dt.date,
                version: str) -> str:
    payload = {"company": company.model_dump(mode="json"), "role": role, "as_of": as_of.isoformat(),
               "what_if": what_if.model_dump(mode="json") if what_if else None, "config": version}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def run_trust(db: Session, company: models.Company, role: str, what_if: engine.WhatIf | None,
              user: models.User | None) -> models.ScoreRun:
    """Score with the engine and save the run (what-if runs are flagged and never shown to viewers)."""
    cfg, as_of = trust_config(), scoring_date()
    ec = to_engine(company)
    try:
        result = score_trust(ec, check_role(role), cfg, as_of, what_if=what_if)
    except ValueError as exc:
        raise ApiError(422, str(exc)) from exc
    run = models.ScoreRun(kind="trust", company_id=company.id, role=role, config_version=cfg.version,
                          as_of=as_of, inputs_hash=inputs_hash(ec, role, what_if, as_of, cfg.version),
                          is_what_if=result["what_if"], result=result,
                          created_by=user.id if user else None)
    db.add(run)
    db.commit()
    return run


def default_role(company: models.Company) -> str:
    """The role a company is shown in by default: its first role offered, else the first configured role
    (service providers are scored with service_provider_trust_role)."""
    cfg = trust_config()
    if company.type == "service_provider":
        return cfg.service_provider_trust_role
    return company.roles_offered[0] if company.roles_offered else next(iter(cfg.roles))


def latest_scores(db: Session, companies: list[models.Company] | None = None) -> dict[str, LatestScore]:
    """Latest real (never what-if) trust run per company. Companies without a saved run (for example
    right after a reseed) are scored live in their default role, without saving a run."""
    runs = db.scalars(select(models.ScoreRun)
                      .where(models.ScoreRun.kind == "trust", models.ScoreRun.is_what_if.is_(False))
                      .order_by(models.ScoreRun.created_at.desc(), models.ScoreRun.id.desc()))
    out: dict[str, LatestScore] = {}
    for run in runs:
        if run.company_id not in out:
            r = run.result
            out[run.company_id] = LatestScore(role=run.role, score=r["score"], verdict=r["verdict"],
                                              confidence=r["confidence"], as_of=run.as_of)
    cfg, as_of = trust_config(), scoring_date()
    for company in companies or []:
        if company.id not in out:
            role = default_role(company)
            r = score_trust(to_engine(company), role, cfg, as_of)
            out[company.id] = LatestScore(role=role, score=r["score"], verdict=r["verdict"],
                                          confidence=r["confidence"], as_of=as_of)
    return out


def evidence_rows(company: models.Company) -> list[dict[str, Any]]:
    """All parameters, in config order, with their freshness status as of the scoring date."""
    cfg, as_of = trust_config(), scoring_date()
    stored = {e.parameter_id: e for e in company.evidence}
    rows = []
    for pid, spec in cfg.parameters.items():
        e = stored.get(pid)
        ev = engine.Evidence(level=e.level, verified=e.verified, source_date=e.source_date,
                             checked_at=e.checked_at) if e else None
        row = {"parameter_id": pid, "category": spec.category, "name": spec.name,
               "status": evidence_status(ev, pid, cfg, as_of)}
        if e:
            row |= {"level": e.level, "verified": e.verified, "source_url": e.source_url,
                    "source_date": e.source_date, "checked_at": e.checked_at, "note": e.note,
                    "updated_at": e.updated_at}
        rows.append(row)
    return rows


def viewer_reasons(result: dict[str, Any], cfg: TrustConfig) -> list[ViewerReason]:
    """Knock-outs at a 0% parameter quote rubric text in the engine result; viewers get the category."""
    if result["status"] != "not_eligible":
        return [ViewerReason(**r) for r in result["reasons"]]
    out = []
    for k in result["knockouts"]:
        pid = k["code"].removesuffix("_at_zero")
        if pid in cfg.parameters:
            cat = cfg.categories[cfg.parameters[pid].category].label
            text = f"Knock-out: a required {cat.lower()} check failed"
            out.append(ViewerReason(code="knockout", text=text))
        else:
            out.append(ViewerReason(code="knockout", text=k["text"]))
    return out


def viewer_report(company: models.Company, role: str) -> ViewerTrustReport:
    """SME-safe Trust report, computed from current data (what-if runs never reach it)."""
    cfg = trust_config()
    result = score_trust(to_engine(company), check_role(role), cfg, scoring_date())

    def safe(stats: dict[str, dict[str, Any]]) -> dict[str, ViewerCategory]:
        return {k: ViewerCategory(label=v["label"], weight=v["points"], verified_pct=v["verified_pct"],
                                  score_pct=v["score_pct"]) for k, v in stats.items()}

    return ViewerTrustReport(
        company_id=company.id, company_name=company.name, fictional=company.fictional, role=role,
        as_of=result["as_of"], weight_set=result["weight_set"], eligible=result["eligible"],
        status=result["status"], score=result["score"], band=result["band"],
        confidence=result["confidence"], provisional=result["provisional"], verdict=result["verdict"],
        outlook=result["outlook"], categories=safe(result.get("categories", {})),
        dimensions=safe(result.get("dimensions", {})), gates=result.get("gates", {}),
        reasons=viewer_reasons(result, cfg), pending=viewer_pending(result, cfg), disclaimer=cfg.disclaimer,
    )


def viewer_pending(result: dict[str, Any], cfg: TrustConfig) -> list[ViewerPending]:
    """The engine's next checks rolled up to categories (order kept: under-verified dimensions first,
    then by points), followed by pending gates. No parameter names, rubric or check instructions."""
    lines: dict[str, ViewerPending] = {}
    under = {d for d, v in result.get("dimensions", {}).items()
             if v["verified_pct"] is not None and v["verified_pct"] < cfg.confidence.dimension_provisional_below}
    gates = []
    for check in result.get("next_checks", []):
        if check["type"] == "gate":
            gates.append(ViewerPending(type="gate", id=check["id"], label=cfg.gates[check["id"]].label, count=1,
                                       points=None, priority=False))
            continue
        cat = cfg.parameters[check["id"]].category
        line = lines.get(cat)
        if line is None:
            line = lines[cat] = ViewerPending(type="category", id=cat, label=cfg.categories[cat].label, count=0,
                                              points=0.0, priority=cfg.dimension_of(cat) in under)
        line.count += 1
        line.points = r4(line.points + check["points"])
    return [*lines.values(), *gates]
