from fastapi import APIRouter, Depends

from app.auth import AnalystUser, viewer
from app.db import DbSession
from app.schemas import TrustRunOut, TrustScoreIn, ViewerTrustReport
from app.services.scoring import default_role, get_company, run_trust, viewer_report

router = APIRouter(prefix="/companies/{company_id}", tags=["trust"])


@router.post("/trust-score")
def trust_score(company_id: str, body: TrustScoreIn, db: DbSession,
                user: AnalystUser) -> TrustRunOut:
    """Full engine result (analyst view). Saved as a score run; what-if runs are flagged."""
    run = run_trust(db, get_company(db, company_id), body.role, body.what_if, user)
    return TrustRunOut(run_id=run.id, is_what_if=run.is_what_if, result=run.result)


@router.get("/trust-report", dependencies=[Depends(viewer)])
def trust_report(company_id: str, db: DbSession, role: str | None = None) -> ViewerTrustReport:
    """SME-safe report: categories, weights, scores and reasons only. Defaults to the first role offered."""
    company = get_company(db, company_id)
    return viewer_report(company, role or default_role(company))
