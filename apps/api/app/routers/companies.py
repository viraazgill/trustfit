"""Companies, gates, trends and flags."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select

from app import models
from app.auth import analyst, viewer
from app.db import DbSession
from app.errors import ApiError
from app.schemas import (
    CompanyCreate,
    CompanyPatch,
    FlagIn,
    FlagOut,
    TrendIn,
    ViewerCompany,
    ViewerCompanyListItem,
)
from app.services.scoring import get_company, latest_scores, trust_config
from trustfit_engine.models import GateStatus

router = APIRouter(prefix="/companies", tags=["companies"])


def viewer_company(c: models.Company) -> ViewerCompany:
    return ViewerCompany(
        id=c.id, name=c.name, fictional=c.fictional, type=c.type, roles_offered=list(c.roles_offered),
        cin=c.cin, nse_code=c.nse_code, bse_code=c.bse_code, msme_category=c.msme_category,
        hq_state=c.hq_state, description=c.description, profile=c.profile, capabilities=c.capabilities,
        gates=c.gates, trends={k: v["direction"] for k, v in c.trends.items()},
    )


@router.get("", dependencies=[Depends(viewer)])
def list_companies(db: DbSession) -> list[ViewerCompanyListItem]:
    latest = latest_scores(db)
    return [ViewerCompanyListItem(id=c.id, name=c.name, fictional=c.fictional, type=c.type,
                                  roles_offered=list(c.roles_offered), hq_state=c.hq_state,
                                  latest=latest.get(c.id))
            for c in db.scalars(select(models.Company).order_by(models.Company.name))]


@router.post("", status_code=201, dependencies=[Depends(analyst)])
def create_company(body: CompanyCreate, db: DbSession) -> ViewerCompany:
    if db.get(models.Company, body.id):
        raise ApiError(409, f"Company {body.id!r} already exists", field="id")
    company = models.Company(**body.model_dump())
    db.add(company)
    db.commit()
    return viewer_company(company)


@router.get("/{company_id}", dependencies=[Depends(viewer)])
def read_company(company_id: str, db: DbSession) -> ViewerCompany:
    return viewer_company(get_company(db, company_id))


@router.patch("/{company_id}", dependencies=[Depends(analyst)])
def update_company(company_id: str, body: CompanyPatch, db: DbSession) -> ViewerCompany:
    company = get_company(db, company_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    db.commit()
    return viewer_company(company)


@router.put("/{company_id}/gates", dependencies=[Depends(analyst)])
def set_gates(company_id: str, body: dict[str, GateStatus], db: DbSession) -> ViewerCompany:
    company = get_company(db, company_id)
    unknown = set(body) - set(trust_config().gates)
    if unknown:
        raise ApiError(422, f"Unknown gate(s): {', '.join(sorted(unknown))}", field="gates")
    company.gates = {**company.gates, **body}
    db.commit()
    return viewer_company(company)


@router.get("/{company_id}/trends", dependencies=[Depends(analyst)])
def read_trends(company_id: str, db: DbSession) -> dict[str, TrendIn]:
    return get_company(db, company_id).trends


@router.put("/{company_id}/trends", dependencies=[Depends(analyst)])
def set_trends(company_id: str, body: dict[str, TrendIn], db: DbSession) -> dict[str, TrendIn]:
    company = get_company(db, company_id)
    unknown = set(body) - set(trust_config().outlook.signals)
    if unknown:
        raise ApiError(422, f"Unknown trend signal(s): {', '.join(sorted(unknown))}", field="trends")
    company.trends = {**company.trends, **{k: v.model_dump() for k, v in body.items()}}
    db.commit()
    return company.trends


@router.get("/{company_id}/flags", dependencies=[Depends(analyst)])
def list_flags(company_id: str, db: DbSession) -> list[FlagOut]:
    return [FlagOut.model_validate(f) for f in get_company(db, company_id).flags]


@router.post("/{company_id}/flags", status_code=201, dependencies=[Depends(analyst)])
def add_flag(company_id: str, body: FlagIn, db: DbSession) -> FlagOut:
    company = get_company(db, company_id)
    ov = trust_config().overrides
    known = {"knockout": ov.knockouts, "cap": ov.caps, "notch": ov.notches}.get(body.type)
    if known is not None and body.code not in known:
        raise ApiError(422, f"Unknown {body.type} code {body.code!r}; use one of {', '.join(known)}",
                       field="code")
    flag = models.Flag(company_id=company.id, **body.model_dump())
    db.add(flag)
    db.commit()
    return FlagOut.model_validate(flag)


@router.delete("/{company_id}/flags/{flag_id}", status_code=204, dependencies=[Depends(analyst)])
def delete_flag(company_id: str, flag_id: int, db: DbSession) -> Response:
    flag = db.get(models.Flag, flag_id)
    if flag is None or flag.company_id != company_id:
        raise ApiError(404, f"No flag {flag_id} on {company_id!r}")
    db.delete(flag)
    db.commit()
    return Response(status_code=204)
