import pytest

API = "/api/v1"

ANALYST_ROUTES = [
    ("get", "/config/rubrics", None),
    ("post", "/companies", {"id": "x-demo", "name": "X (Demo)"}),
    ("patch", "/companies/subros", {"hq_state": "delhi"}),
    ("get", "/companies/subros/evidence", None),
    ("put", "/companies/subros/evidence/A1", {"level": 100, "verified": False}),
    ("get", "/companies/subros/evidence/A1/history", None),
    ("get", "/companies/subros/flags", None),
    ("post", "/companies/subros/flags", {"type": "cap", "code": "going_concern_uncertainty"}),
    ("delete", "/companies/subros/flags/1", None),
    ("put", "/companies/subros/gates", {"V1": "passed"}),
    ("get", "/companies/subros/trends", None),
    ("put", "/companies/subros/trends", {"revenue_growth": {"direction": "stable"}}),
    ("post", "/companies/subros/trust-score", {"role": "supplier"}),
]
VIEWER_ROUTES = ["/companies", "/companies/subros", "/companies/subros/trust-report?role=supplier"]


def call(client, method, path, body, headers=None):
    kwargs = {"headers": headers or {}}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(API + path, **kwargs)


@pytest.mark.parametrize(("method", "path", "body"), ANALYST_ROUTES)
def test_viewer_gets_403_on_analyst_routes(client, as_viewer, method, path, body):
    res = call(client, method, path, body, as_viewer)
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(("method", "path", "body"), ANALYST_ROUTES)
def test_anonymous_gets_401(client, method, path, body):
    assert call(client, method, path, body).status_code == 401


@pytest.mark.parametrize("path", VIEWER_ROUTES)
def test_every_role_can_read_viewer_routes(client, as_viewer, as_analyst, as_admin, path):
    for headers in (as_viewer, as_analyst, as_admin):
        assert client.get(API + path, headers=headers).status_code == 200


def test_admin_can_use_analyst_routes(client, as_admin):
    assert client.get(f"{API}/config/rubrics", headers=as_admin).status_code == 200


def test_wrong_password_is_401(client):
    res = client.post(f"{API}/auth/login", json={"email": "viewer@trustfit.local", "password": "nope"})
    assert res.status_code == 401
    assert res.json() == {"error": {"code": "unauthorized", "message": "Wrong email or password",
                                    "field": None}}


def test_bad_token_is_401(client):
    res = client.get(f"{API}/companies", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


def test_me(client, as_analyst):
    assert client.get(f"{API}/auth/me", headers=as_analyst).json()["role"] == "analyst"


def test_openapi_lists_every_route(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    for p in ["/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/config/public", "/api/v1/config/rubrics",
              "/api/v1/companies", "/api/v1/companies/{company_id}",
              "/api/v1/companies/{company_id}/evidence",
              "/api/v1/companies/{company_id}/evidence/{parameter_id}",
              "/api/v1/companies/{company_id}/evidence/{parameter_id}/history",
              "/api/v1/companies/{company_id}/flags", "/api/v1/companies/{company_id}/flags/{flag_id}",
              "/api/v1/companies/{company_id}/gates", "/api/v1/companies/{company_id}/trends",
              "/api/v1/companies/{company_id}/trust-score", "/api/v1/companies/{company_id}/trust-report"]:
        assert p in paths, p


def test_admin_resets_the_demo_data_and_stays_signed_in(client, as_admin, as_analyst, as_viewer):
    created = client.post("/api/v1/smes", headers=as_viewer, json={
        "name": "Temp (Demo)", "sector": "machinery", "role_sought": "supplier", "volume_units_per_month": 10,
        "target_states": {"primary": ["goa"], "secondary": []}}).json()
    assert client.post("/api/v1/admin/reset-demo", headers=as_analyst).status_code == 403
    res = client.post("/api/v1/admin/reset-demo", headers=as_admin)
    assert res.status_code == 200, res.text
    assert res.json()["added"] == {"users": 0, "companies": 10, "smes": 1}
    assert client.get(f"/api/v1/smes/{created['id']}", headers=as_admin).status_code == 404
    assert client.get("/api/v1/auth/me", headers=as_admin).status_code == 200  # the token still works


def test_public_config_reports_the_scoring_date(client):
    body = client.get("/api/v1/config/public").json()
    assert (body["scoring_date"], body["fixed_scoring_date"]) == ("2026-10-24", True)
