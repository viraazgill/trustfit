"""Readiness and the Gap Bridge through the API (docs/04-gap-bridge-spec.md golden numbers for Sorano)."""
import json

import pytest
from conftest import REPO_ROOT, assert_matches
from sqlalchemy import select

from app import models

API = "/api/v1"
GOLDEN_FILE = REPO_ROOT / "reference" / "expected" / "demo_gap_bridge_sorano.json"
GOLDEN = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
QUESTIONS = [q for d in ("R1.1 R1.2 R1.3", "R2.1 R2.2", "R3.1 R3.2 R3.3", "R4.1 R4.2 R4.3", "R5.1 R5.2",
                         "R6.1 R6.2 R6.3") for q in d.split()]
BRIEF = {"name": "Kaze Pumps (Demo)", "sector": "industrial_instruments", "products": ["flow_meters"],
         "role_sought": "distributor", "target_states": {"primary": ["maharashtra"], "secondary": []},
         "channels_needed": ["industrial_b2b"], "volume_units_per_month": 200, "after_sales_need": "basic",
         "competitors": []}


def bridge(client, headers, sme="sorano"):
    res = client.post(f"{API}/smes/{sme}/bridge", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_sorano_bridge_matches_the_golden_team_and_ranking(client, as_viewer):
    body = bridge(client, as_viewer)
    for key in ("readiness", "primary_ranking", "gap_status", "team_coverage"):
        assert_matches(body[key], GOLDEN[key])
    golden_team = [{**m, "covers": [{**c, "verified": True} for c in m["covers"]]} for m in GOLDEN["team"]]
    assert_matches(body["team"], golden_team)
    assert [m["company_id"] for m in body["team"]] == [
        "deccan-instrumentation", "certipath", "nihon-india-bridge", "swift-cargo"]
    assert round(body["team_coverage"]) == 82
    assert body["disclaimer"] == "TrustFit Score is not a credit rating or investment advice."


def test_every_demo_company_matches_the_golden_evaluation(client, as_viewer):
    companies = {c["company_id"]: c for c in bridge(client, as_viewer)["companies"]}
    for expected in GOLDEN["companies"]:
        actual = {k: v for k, v in companies[expected["company_id"]].items() if k in expected}
        assert_matches(actual, expected)
        assert companies[expected["company_id"]]["fictional"] is True
    assert companies["subros"]["fictional"] is False  # the database also holds the real company


def test_exclusions_carry_their_reason(client, as_viewer):
    excluded = {c["company_id"]: c["excluded_because"] for c in bridge(client, as_viewer)["companies"]
                if not c["eligible"]}
    assert excluded == {"western-flow": ["competitor conflict: represents Flowtek (Demo)"],
                        "konkan-trade": ["knock-out"]}


def test_shortlists_explain_each_recommendation(client, as_viewer):
    per_gap = bridge(client, as_viewer)["per_gap"]
    assert per_gap["R4"][0] == {"company_id": "certipath", "coverage": 0.625,
                                "reason": "Certification support (BIS and others) 100%, verified"}
    assert set(per_gap) == {"R1", "R4", "R5", "R6"}  # critical and significant gaps only


def test_bridge_runs_are_saved(client, as_viewer, session_factory):
    bridge(client, as_viewer)
    with session_factory() as db:
        run = db.scalars(select(models.ScoreRun).where(models.ScoreRun.kind == "bridge")).one()
        assert (run.sme_id, run.config_version) == ("sorano", "trust:v1 fit:v1 gap_bridge:v1")


def test_sorano_readiness(client, as_viewer):
    body = client.get(f"{API}/smes/sorano/readiness", headers=as_viewer).json()
    assert body["answered"] is True
    assert_matches(body["dimensions"], GOLDEN["readiness"])


def test_new_sme_answers_the_readiness_check(client, as_viewer):
    sme = client.post(f"{API}/smes", json=BRIEF, headers=as_viewer).json()
    assert client.get(f"{API}/smes/{sme['id']}/readiness", headers=as_viewer).json()["answered"] is False
    assert client.post(f"{API}/smes/{sme['id']}/bridge", headers=as_viewer).status_code == 409
    answers = {q: 2 for q in QUESTIONS}
    res = client.put(f"{API}/smes/{sme['id']}/readiness", json={"answers": answers}, headers=as_viewer)
    assert res.status_code == 200, res.text
    dims = res.json()["dimensions"]
    assert dims["R1"]["readiness"] == 50.0 and dims["R1"]["severity"] == 60.0  # 50 x relevance 1.2
    assert bridge(client, as_viewer, sme["id"])["team"]


@pytest.mark.parametrize(("answers", "message"), [
    ({"R1.1": 2}, "missing"),
    ({**{q: 1 for q in QUESTIONS}, "R1.1": 7}, "must be one of"),
    ({**{q: 1 for q in QUESTIONS}, "R7.1": 1}, "unknown"),
])
def test_invalid_answers_are_rejected(client, as_viewer, answers, message):
    sme = client.post(f"{API}/smes", json=BRIEF, headers=as_viewer).json()
    res = client.put(f"{API}/smes/{sme['id']}/readiness", json={"answers": answers}, headers=as_viewer)
    assert res.status_code == 422 and message in res.json()["error"]["message"]


def test_viewers_cannot_change_the_demo_smes_answers(client, as_viewer):
    all_done = {"answers": {q: 4 for q in QUESTIONS}}
    res = client.put(f"{API}/smes/sorano/readiness", json=all_done, headers=as_viewer)
    assert res.status_code == 403


def test_public_bridge_config(client):
    body = client.get(f"{API}/config/bridge").json()
    assert sum(len(d["questions"]) for d in body["dimensions"].values()) == 16
    assert body["answer_scale"]["4"] == "Done and validated" and body["covered_by_trustfit"] == ["R2"]
