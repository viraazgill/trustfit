"""Viewer (SME) responses must never carry rubric text, where_to_check, check instructions, analyst
notes or evidence source URLs. These tests fail if a viewer schema or response ever does."""
import json

import pytest
from sqlalchemy import select

from app import models, schemas
from app.services.scoring import trust_config

API = "/api/v1"
FORBIDDEN_KEYS = {"rubric", "where_to_check", "check", "note", "notes", "source_url", "evidence",
                  "knockouts", "next_checks", "parameters", "parameter_splits"}
VIEWER_SCHEMAS = [schemas.ViewerTrustReport, schemas.ViewerCompany, schemas.ViewerCompanyListItem,
                  schemas.PublicConfig]


def keys_in_schema(model) -> set[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            found.update(node.get("properties", {}))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(model.model_json_schema())
    return found


def keys_in(data) -> set[str]:
    if isinstance(data, dict):
        return set(data) | {k for v in data.values() for k in keys_in(v)}
    if isinstance(data, list):
        return {k for v in data for k in keys_in(v)}
    return set()


def confidential_strings(session_factory) -> list[str]:
    cfg = trust_config()
    out = [t for p in cfg.parameters.values() for t in (*p.rubric.values(), p.where_to_check)]
    out += [g.check for g in cfg.gates.values()]
    ov = cfg.overrides
    out += [x.check for group in (ov.knockouts, ov.caps, ov.notches) for x in group.values()]
    with session_factory() as db:
        out += [e.note for e in db.scalars(select(models.Evidence)) if e.note]
        out += [e.source_url for e in db.scalars(select(models.Evidence)) if e.source_url]
        out += [f.note for f in db.scalars(select(models.Flag)) if f.note]
        out += [t["note"] for c in db.scalars(select(models.Company))
                for t in c.trends.values() if t.get("note")]
    # Very short rubric levels ("None", "Growing") could match by accident; real leaks are longer.
    return [s for s in out if len(s) >= 12]


@pytest.mark.parametrize("model", VIEWER_SCHEMAS, ids=lambda m: m.__name__)
def test_viewer_schemas_have_no_confidential_fields(model):
    assert not keys_in_schema(model) & FORBIDDEN_KEYS


def viewer_responses(client, headers) -> list:
    out = [client.get(f"{API}/config/public").json(), client.get(f"{API}/companies", headers=headers).json()]
    for c in out[1]:
        out.append(client.get(f"{API}/companies/{c['id']}", headers=headers).json())
        for role in trust_config().roles:
            url = f"{API}/companies/{c['id']}/trust-report?role={role}"
            out.append(client.get(url, headers=headers).json())
    return out


def test_viewer_responses_carry_no_confidential_text(client, as_viewer, as_analyst, session_factory):
    # Knock a demo company out at a 0% parameter: the engine's reason quotes rubric text.
    client.put(f"{API}/companies/western-flow/evidence/A3", headers=as_analyst,
               json={"level": 0, "verified": True, "source_url": "https://example.com/gst",
                     "source_date": "2026-10-20", "checked_at": "2026-10-20", "note": "GST cancelled"})
    client.post(f"{API}/companies/subros/trust-score", json={"role": "supplier"}, headers=as_analyst)

    responses = viewer_responses(client, as_viewer)
    assert not keys_in(responses) & FORBIDDEN_KEYS
    blob = json.dumps(responses, ensure_ascii=False)
    leaks = [s for s in confidential_strings(session_factory) if s in blob]
    assert leaks == []

    url = f"{API}/companies/western-flow/trust-report?role=distributor"
    report = client.get(url, headers=as_viewer).json()
    assert report["verdict"] == "Red" and report["reasons"][0]["code"] == "knockout"


def test_reports_show_the_disclaimer(client, as_viewer):
    report = client.get(f"{API}/companies/subros/trust-report?role=supplier", headers=as_viewer).json()
    assert report["disclaimer"] == "TrustFit Score is not a credit rating or investment advice."
    assert "rating" not in json.dumps(report["reasons"]).lower()


def test_rubrics_are_analyst_only(client, as_analyst):
    body = client.get(f"{API}/config/rubrics", headers=as_analyst).json()
    assert body["parameters"]["A1"]["where_to_check"]
