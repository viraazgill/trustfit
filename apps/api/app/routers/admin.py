"""Admin-only demo controls."""
from fastapi import APIRouter

from app.auth import AdminUser
from app.db import DbSession
from app.schemas import ResetOut
from app.seed import seed
from app.settings import scoring_date

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset-demo")
def reset_demo(db: DbSession, _: AdminUser) -> ResetOut:
    """Wipe companies, evidence, flags, SMEs and score runs, then reload the seed files (users are kept)."""
    as_of = scoring_date()
    return ResetOut(as_of=as_of, added=seed(db, as_of, wipe=True, keep_users=True))
