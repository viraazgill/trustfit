import json

import pytest
from conftest import REPO_ROOT, assert_matches
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import models
from app.services.scoring import trust_config

API = "/api/v1"
INTEGRITY_CLEAN = {"evidence": {p: 100 for p in ["A1", "A3", "A4", "A5", "C1", "C2"]},
                   "gates": {"V1": "passed", "V2": "passed", "V3": "passed"}}


def expected(name: str):
    return json.loads((REPO_ROOT / "reference" / "expected" / name).read_text(encoding="utf-8"))


def score(client, headers, company="subros", **body):
    res = client.post(f"{API}/companies/{company}/trust-score", json={"role": "supplier", **body},
                      headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


# ---- seed and schema

def test_seed_loads_everything(session_factory):
    with session_factory() as db:
        companies = db.scalars(select(models.Company)).all()
        assert len(companies) == 10
        assert all(c.name.endswith("(Demo)") for c in companies if c.fictional)
        assert [c.id for c in companies if not c.fictional] == ["subros"]
        assert len(db.scalars(select(models.User)).all()) == 3
        assert db.get(models.Sme, "sorano").fictional is True


def test_seed_without_reset_is_idempotent(session_factory):
    from conftest import AS_OF

    from app.seed import seed
    with session_factory() as db:
        assert seed(db, AS_OF) == {"users": 0, "companies": 0, "smes": 0}


def test_evidence_levels_match_config():
    assert list(models.EVIDENCE_LEVELS) == trust_config().scale_levels


@pytest.mark.parametrize("fields", [
    {"level": 30, "verified": False},
    {"level": 50, "verified": True, "source_url": None, "source_date": None},
])
def test_database_constraints(session_factory, fields):
    with session_factory() as db:
        db.add(models.Evidence(company_id="subros", parameter_id="A1", **fields))
        with pytest.raises(IntegrityError):
            db.commit()


# ---- scoring

def test_score_subros_as_supplier_matches_golden(client, as_analyst, session_factory):
    body = score(client, as_analyst)
    assert body["is_what_if"] is False
    assert_matches(body["result"], expected("subros_supplier.json"))
    with session_factory() as db:
        run = db.get(models.ScoreRun, body["run_id"])
        assert (run.kind, run.role, run.config_version, run.is_what_if) == ("trust", "supplier", "v1", False)
        assert len(run.inputs_hash) == 64 and run.created_by is not None


def test_what_if_run_is_saved_and_hidden_from_viewers(client, as_analyst, as_viewer, session_factory):
    real = score(client, as_analyst)
    what_if = score(client, as_analyst, what_if=INTEGRITY_CLEAN)
    assert what_if["is_what_if"] is True
    assert_matches(what_if["result"], expected("subros_supplier_whatif_integrity_clean.json"))
    with session_factory() as db:
        assert db.get(models.ScoreRun, what_if["run_id"]).is_what_if is True

    listing = client.get(f"{API}/companies", headers=as_viewer).json()
    subros = next(c for c in listing if c["id"] == "subros")
    assert subros["latest"]["score"] == real["result"]["score"] == 87
    assert subros["latest"]["verdict"] == "Amber"
    report = client.get(f"{API}/companies/subros/trust-report?role=supplier", headers=as_viewer).json()
    assert (report["score"], report["verdict"]) == (87, "Amber")


def test_analyst_updates_evidence_and_the_score_changes(client, as_analyst, session_factory):
    before = score(client, as_analyst)["result"]
    res = client.put(f"{API}/companies/subros/evidence/B2", headers=as_analyst,
                     json={"level": 100, "verified": True, "source_url": "https://www.screener.in/company/SUBROS/",
                           "source_date": "2026-10-20", "note": "EBITDA margin re-checked"})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "verified"
    after = score(client, as_analyst)["result"]
    assert after["base_score"] > before["base_score"]
    assert after["categories"]["B"]["score_pct"] > before["categories"]["B"]["score_pct"]

    history = client.get(f"{API}/companies/subros/evidence/B2/history", headers=as_analyst).json()
    assert history[0]["level"] == 100 and history[0]["note"] == "EBITDA margin re-checked"


def test_evidence_list_has_all_parameters_with_status(client, as_analyst):
    rows = client.get(f"{API}/companies/subros/evidence", headers=as_analyst).json()
    assert len(rows) == 37
    by_id = {r["parameter_id"]: r for r in rows}
    assert by_id["A1"]["status"] == "missing" and by_id["B6"]["status"] == "verified"


@pytest.mark.parametrize(("body", "field"), [
    ({"level": 30, "verified": False}, "level"),
    ({"level": 50, "verified": True, "source_date": "2026-10-01"}, None),
])
def test_invalid_evidence_is_rejected(client, as_analyst, body, field):
    res = client.put(f"{API}/companies/subros/evidence/A1", headers=as_analyst, json=body)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
    if field:
        assert res.json()["error"]["field"] == field


def test_flags_change_the_score(client, as_analyst):
    res = client.post(f"{API}/companies/subros/flags", headers=as_analyst,
                      json={"type": "cap", "code": "going_concern_uncertainty", "note": "test"})
    assert res.status_code == 201, res.text
    capped = score(client, as_analyst)["result"]
    assert (capped["score"], capped["binding_limit"]) == (60, "cap")
    flag_url = f"{API}/companies/subros/flags/{res.json()['id']}"
    assert client.delete(flag_url, headers=as_analyst).status_code == 204
    assert score(client, as_analyst)["result"]["score"] == 87


def test_unknown_flag_code_is_rejected(client, as_analyst):
    res = client.post(f"{API}/companies/subros/flags", headers=as_analyst,
                      json={"type": "cap", "code": "nope"})
    assert res.status_code == 422 and res.json()["error"]["field"] == "code"


def test_gates_and_trends(client, as_analyst):
    res = client.put(f"{API}/companies/subros/gates", headers=as_analyst,
                     json={"V1": "passed", "V2": "passed", "V3": "passed"})
    assert res.status_code == 200 and res.json()["gates"]["V3"] == "passed"
    res = client.put(f"{API}/companies/subros/trends", headers=as_analyst,
                     json={"operating_margin": {"direction": "improving", "note": "Q2 recovery"}})
    assert res.json()["operating_margin"] == {"direction": "improving", "note": "Q2 recovery"}
    r = score(client, as_analyst)["result"]
    assert r["outlook"] == "Stable"
    assert "gates_pending" not in [x["code"] for x in r["reasons"]]


def test_unknown_role_is_422(client, as_analyst):
    res = client.post(f"{API}/companies/subros/trust-score", json={"role": "landlord"}, headers=as_analyst)
    assert res.status_code == 422 and res.json()["error"]["field"] == "role"


def test_unknown_company_is_404(client, as_viewer):
    res = client.get(f"{API}/companies/nope", headers=as_viewer)
    assert res.status_code == 404 and res.json()["error"]["code"] == "not_found"


def test_analyst_can_create_and_patch_a_company(client, as_analyst):
    res = client.post(f"{API}/companies", headers=as_analyst,
                      json={"id": "new-co-demo", "name": "New Co (Demo)", "fictional": True})
    assert res.status_code == 201, res.text
    assert client.post(f"{API}/companies", headers=as_analyst,
                       json={"id": "new-co-demo", "name": "Again (Demo)"}).status_code == 409
    res = client.patch(f"{API}/companies/new-co-demo", headers=as_analyst, json={"hq_state": "gujarat"})
    assert res.json()["hq_state"] == "gujarat"
