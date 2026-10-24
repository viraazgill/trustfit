"""Evidence (analyst only). Every write appends to evidence_history."""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app import models
from app.auth import AnalystUser, analyst
from app.db import DbSession
from app.errors import ApiError
from app.schemas import EvidenceHistoryRow, EvidenceIn, EvidenceRow
from app.services.scoring import evidence_rows, get_company, trust_config

router = APIRouter(prefix="/companies/{company_id}/evidence", tags=["evidence"])


def _check_parameter(parameter_id: str) -> None:
    if parameter_id not in trust_config().parameters:
        raise ApiError(404, f"No parameter {parameter_id!r}")


@router.get("", dependencies=[Depends(analyst)])
def list_evidence(company_id: str, db: DbSession) -> list[EvidenceRow]:
    return [EvidenceRow(**row) for row in evidence_rows(get_company(db, company_id))]


@router.put("/{parameter_id}")
def put_evidence(company_id: str, parameter_id: str, body: EvidenceIn, db: DbSession,
                 user: AnalystUser) -> EvidenceRow:
    company = get_company(db, company_id)
    _check_parameter(parameter_id)
    levels = trust_config().scale_levels
    if body.level not in levels:
        raise ApiError(422, f"Level must be one of {levels}", field="level")
    row = db.get(models.Evidence, (company_id, parameter_id))
    if row is None:
        row = models.Evidence(company_id=company_id, parameter_id=parameter_id)
        db.add(row)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_by = user.id
    db.add(models.EvidenceHistory(company_id=company_id, parameter_id=parameter_id, changed_by=user.id,
                                  **body.model_dump()))
    db.commit()
    db.refresh(company)
    return EvidenceRow(**next(r for r in evidence_rows(company) if r["parameter_id"] == parameter_id))


@router.get("/{parameter_id}/history", dependencies=[Depends(analyst)])
def evidence_history(company_id: str, parameter_id: str, db: DbSession) -> list[EvidenceHistoryRow]:
    get_company(db, company_id)
    _check_parameter(parameter_id)
    rows = db.scalars(select(models.EvidenceHistory)
                      .where(models.EvidenceHistory.company_id == company_id,
                             models.EvidenceHistory.parameter_id == parameter_id)
                      .order_by(models.EvidenceHistory.id.desc()))
    return [EvidenceHistoryRow.model_validate(r) for r in rows]
