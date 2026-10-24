"""PDF reports (viewer+). Each prints the matching web page, so the PDF is what the SME sees on screen."""
from typing import Literal

from fastapi import APIRouter, Response

from app.auth import CurrentUser
from app.db import DbSession
from app.services.fit import get_sme
from app.services.pdf import render_pdf
from app.services.scoring import check_role, default_role, get_company

router = APIRouter(tags=["reports"])
Lang = Literal["en", "ja"]


def _pdf(data: bytes, filename: str) -> Response:
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/companies/{company_id}/report.pdf", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def trust_report_pdf(company_id: str, db: DbSession, user: CurrentUser, role: str | None = None,
                     lang: Lang = "en") -> Response:
    """One-page SME-safe Trust report for one role."""
    company = get_company(db, company_id)
    role = check_role(role or default_role(company))
    data = render_pdf(f"/report/company/{company.id}?role={role}", user, lang)
    return _pdf(data, f"trustfit-{company.id}-{role}.pdf")


@router.get("/smes/{sme_id}/report.pdf", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def sme_report_pdf(sme_id: str, db: DbSession, user: CurrentUser, lang: Lang = "en") -> Response:
    """One-page SME report: readiness, gaps, matches and the India entry team."""
    sme = get_sme(db, sme_id, user)
    return _pdf(render_pdf(f"/sme/{sme.id}/report", user, lang), f"trustfit-{sme.id}.pdf")
