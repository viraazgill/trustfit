"""SME briefs and Fit through the API (docs/03-fit-score-spec.md golden numbers for Sorano)."""
import pytest
from sqlalchemy import select

from app import models
from app.auth import create_token, hash_password

API = "/api/v1"
BRIEF = {
    "name": "Kaze Pumps (Demo)", "city": "Nagoya", "employees": 40, "sector": "industrial_instruments",
    "products": ["flow_meters"], "role_sought": "distributor",
    "target_states": {"primary": ["maharashtra"], "secondary": ["gujarat"]},
    "channels_needed": ["industrial_b2b"], "volume_units_per_month": 200, "after_sales_need": "basic",
    "competitors": ["Flowtek (Demo)"], "factor_importance": {"FT4": "must"},
}


def fit(client, headers, company, sme="sorano"):
    res = client.get(f"{API}/smes/{sme}/fit/{company}", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def other_viewer(session_factory) -> dict[str, str]:
    with session_factory() as db:
        user = models.User(email="other@trustfit.local", role="viewer", password_hash=hash_password("x" * 12))
        db.add(user)
        db.commit()
        return {"Authorization": f"Bearer {create_token(user)}"}


def test_sorano_vs_deccan_is_a_strong_fit_and_green(client, as_viewer):
    body = fit(client, as_viewer, "deccan-instrumentation")
    assert (body["score"], body["category"], body["action"]) == (90, "strong_fit", "Shortlist")
    assert (body["trust"]["score"], body["trust"]["verdict"]) == (85, "Green")
    assert body["combined_verdict"] == "Green"
    levels = [body["factors"][f]["level"] for f in ("FT1", "FT2", "FT3", "FT4", "FT5", "FT6")]
    assert levels == [100, 75, 100, 75, 75, 100]
    assert body["disclaimer"] == "TrustFit Score is not a credit rating or investment advice."


def test_western_flow_is_trusted_but_not_a_fit(client, as_viewer):
    body = fit(client, as_viewer, "western-flow")
    assert (body["score"], body["category"], body["action"]) == (54, "not_a_fit", "Skip, even if trusted")
    assert body["conflict"] == {"brand": "Flowtek (Demo)", "relation": "represents"}
    assert (body["trust"]["verdict"], body["combined_verdict"]) == ("Green", "Red")
    assert any(r["code"] == "not_a_fit" for r in body["reasons"])


def test_knocked_out_company_stays_red(client, as_viewer):
    body = fit(client, as_viewer, "konkan-trade")
    assert (body["score"], body["category"]) == (57, "possible_fit")
    assert (body["trust"]["eligible"], body["combined_verdict"]) == (False, "Red")


def test_fit_runs_are_saved(client, as_viewer, session_factory):
    fit(client, as_viewer, "sabarmati-process")
    with session_factory() as db:
        run = db.scalars(select(models.ScoreRun).where(models.ScoreRun.kind == "fit")).one()
        assert (run.sme_id, run.company_id, run.result["fit"]["score"]) == ("sorano", "sabarmati-process", 51)


def test_fit_needs_a_business_partner_offering_the_role(client, as_viewer):
    for company in ("certipath", "subros"):  # a service provider; a supplier, not a distributor
        assert client.get(f"{API}/smes/sorano/fit/{company}", headers=as_viewer).status_code == 422


def test_viewer_creates_and_edits_their_own_brief(client, as_viewer):
    res = client.post(f"{API}/smes", json=BRIEF, headers=as_viewer)
    assert res.status_code == 201, res.text
    sme = res.json()
    assert sme["mine"] is True and sme["fictional"] is False and sme["id"].startswith("kaze-pumps-demo-")
    res = client.patch(f"{API}/smes/{sme['id']}", json={"volume_units_per_month": 500}, headers=as_viewer)
    assert res.json()["volume_units_per_month"] == 500
    listed = {s["id"]: s["mine"] for s in client.get(f"{API}/smes", headers=as_viewer).json()}
    assert listed == {"sorano": False, sme["id"]: True}
    body = fit(client, as_viewer, "deccan-instrumentation", sme=sme["id"])
    assert body["factors"]["FT4"]["importance"] == "must"


def test_viewers_cannot_see_each_others_briefs(client, as_viewer, session_factory):
    sme = client.post(f"{API}/smes", json=BRIEF, headers=as_viewer).json()
    other = other_viewer(session_factory)
    assert client.get(f"{API}/smes/{sme['id']}", headers=other).status_code == 404
    assert [s["id"] for s in client.get(f"{API}/smes", headers=other).json()] == ["sorano"]


def test_demo_sme_is_read_only_for_viewers_but_not_analysts(client, as_viewer, as_analyst):
    assert client.patch(f"{API}/smes/sorano", json={"city": "Kobe"}, headers=as_viewer).status_code == 403
    assert client.patch(f"{API}/smes/sorano", json={"city": "Osaka"}, headers=as_analyst).status_code == 200


@pytest.mark.parametrize(("patch", "field"), [
    ({"sector": "spaceships"}, "sector"),
    ({"target_states": {"primary": ["atlantis"], "secondary": []}}, "target_states"),
    ({"target_states": {"primary": [], "secondary": ["goa"]}}, "target_states"),
    ({"target_states": {"primary": ["goa"], "secondary": ["goa"]}}, "target_states"),
    ({"channels_needed": ["carrier_pigeon"]}, "channels_needed"),
    ({"factor_importance": {"FT1": "crucial"}}, "factor_importance.FT1"),
    ({"factor_importance": {"FT9": "must"}}, "factor_importance"),
    ({"volume_units_per_month": 0}, "volume_units_per_month"),
])
def test_invalid_briefs_are_rejected(client, as_viewer, patch, field):
    res = client.post(f"{API}/smes", json={**BRIEF, **patch}, headers=as_viewer)
    assert res.status_code == 422, res.text
    assert res.json()["error"]["field"] == field


def test_public_fit_config(client):
    body = client.get(f"{API}/config/fit").json()
    assert body["role_default_importance"]["distributor"]["FT2"] == "must"
    assert body["categories"]["not_a_fit"]["action"] == "Skip, even if trusted"
    assert "maharashtra" in body["states"] and body["after_sales_needs"] == ["none", "basic", "full"]


def test_smes_need_sign_in(client):
    assert client.get(f"{API}/smes").status_code == 401
