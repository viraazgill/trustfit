"""SME briefs and Fit. Viewers see their own SMEs and the fictional demo SMEs; responses are SME-safe."""
from fastapi import APIRouter
from sqlalchemy import select

from app import models
from app.auth import CurrentUser
from app.db import DbSession
from app.schemas import SmeIn, SmeOut, SmePatch, ViewerFit
from app.services.fit import can_read, create_sme, get_sme, run_fit, sme_out, update_sme
from app.services.scoring import get_company

router = APIRouter(prefix="/smes", tags=["smes"])


@router.get("")
def list_smes(db: DbSession, user: CurrentUser) -> list[SmeOut]:
    smes = db.scalars(select(models.Sme).order_by(models.Sme.fictional.desc(), models.Sme.name))
    return [sme_out(s, user) for s in smes if can_read(s, user)]


@router.post("", status_code=201)
def new_sme(body: SmeIn, db: DbSession, user: CurrentUser) -> SmeOut:
    return sme_out(create_sme(db, body, user), user)


@router.get("/{sme_id}")
def read_sme(sme_id: str, db: DbSession, user: CurrentUser) -> SmeOut:
    return sme_out(get_sme(db, sme_id, user), user)


@router.patch("/{sme_id}")
def edit_sme(sme_id: str, body: SmePatch, db: DbSession, user: CurrentUser) -> SmeOut:
    return sme_out(update_sme(db, get_sme(db, sme_id, user, write=True), body), user)


@router.get("/{sme_id}/fit/{company_id}")
def fit(sme_id: str, company_id: str, db: DbSession, user: CurrentUser) -> ViewerFit:
    """Fit Score for one business partner against this SME's brief, plus the combined verdict."""
    return run_fit(db, get_sme(db, sme_id, user), get_company(db, company_id), user)
