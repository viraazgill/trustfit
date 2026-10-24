"""PDF report routes. The printer itself (Playwright) is exercised by the web end-to-end test; here it is
replaced so the tests check routing, access and the page each PDF prints."""
import pytest

from app.routers import reports

API = "/api/v1"


@pytest.fixture
def printed(monkeypatch):
    calls = []

    def fake_render(path, user, lang="en"):
        calls.append((path, user.role, lang))
        return b"%PDF-1.7 fake"

    monkeypatch.setattr(reports, "render_pdf", fake_render)
    return calls


def test_trust_report_pdf_prints_the_report_page(client, as_viewer, printed):
    res = client.get(f"{API}/companies/subros/report.pdf?role=jv_partner&lang=ja", headers=as_viewer)
    assert res.status_code == 200 and res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    assert 'filename="trustfit-subros-jv_partner.pdf"' in res.headers["content-disposition"]
    assert printed == [("/report/company/subros?role=jv_partner", "viewer", "ja")]


def test_trust_report_pdf_defaults_to_the_company_role(client, as_viewer, printed):
    client.get(f"{API}/companies/certipath/report.pdf", headers=as_viewer)
    assert printed[0][0] == "/report/company/certipath?role=distributor"


def test_sme_report_pdf(client, as_viewer, printed):
    res = client.get(f"{API}/smes/sorano/report.pdf", headers=as_viewer)
    assert res.status_code == 200 and printed == [("/sme/sorano/report", "viewer", "en")]


def test_pdfs_need_sign_in_and_valid_inputs(client, as_viewer, printed):
    assert client.get(f"{API}/smes/sorano/report.pdf").status_code == 401
    pdf = f"{API}/companies/subros/report.pdf"
    assert client.get(f"{pdf}?role=landlord", headers=as_viewer).status_code == 422
    assert client.get(f"{pdf}?lang=fr", headers=as_viewer).status_code == 422
    assert client.get(f"{API}/smes/nobody/report.pdf", headers=as_viewer).status_code == 404
    assert printed == []
