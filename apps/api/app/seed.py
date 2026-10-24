"""Load the seed data: python -m app.seed [--reset]

Loads Subros, the demo companies (via the engine's seed_io, resolving "today-Nd" against the scoring
date) and the demo SME, plus admin / analyst / viewer users from the SEED_* settings. Without
--reset, rows that already exist are left alone; --reset wipes every table first (run before a demo).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models
from app.auth import hash_password
from app.db import SessionLocal
from app.services.scoring import trust_config
from app.settings import scoring_date, settings
from trustfit_engine.models import Company
from trustfit_engine.seed_io import load_companies

COMPANY_FILES = ("subros.json", "demo_companies.json")
SME_FILES = ("demo_sme_sorano.json",)
COMPANY_COLUMNS = ("cin", "nse_code", "bse_code", "msme_category", "hq_state", "description")
SME_COLUMNS = ("name", "fictional", "country", "city", "employees", "description", "sector", "products",
               "role_sought", "target_states", "channels_needed", "volume_units_per_month",
               "after_sales_need", "competitors", "factor_importance", "readiness_answers")


def reset(db: Session, keep_users: bool = False) -> None:
    tables = [models.ScoreRun, models.EvidenceHistory, models.Evidence, models.Flag, models.Sme,
              models.Company]
    for table in tables if keep_users else [*tables, models.User]:
        db.execute(delete(table))


def seed_users(db: Session) -> int:
    added = 0
    for role in ("admin", "analyst", "viewer"):
        email = getattr(settings, f"SEED_{role.upper()}_EMAIL").strip().lower()
        if db.scalar(select(models.User).where(models.User.email == email)):
            continue
        db.add(models.User(email=email, role=role,
                           password_hash=hash_password(getattr(settings, f"SEED_{role.upper()}_PASSWORD"))))
        added += 1
    return added


def company_row(c: Company) -> models.Company:
    extra = c.model_extra or {}
    row = models.Company(
        id=c.id, name=c.name, fictional=c.fictional, type=c.type, roles_offered=c.roles_offered,
        profile=c.profile, capabilities=c.capabilities, gates=dict(c.gates),
        trends={k: t.model_dump() for k, t in c.trends.items()},
        **{k: extra.get(k) for k in COMPANY_COLUMNS},
    )
    row.evidence = [models.Evidence(parameter_id=pid, **ev.model_dump()) for pid, ev in c.evidence.items()]
    row.flags = [models.Flag(**f.model_dump()) for f in c.flags]
    return row


def seed_companies(db: Session, as_of: dt.date) -> int:
    added = 0
    for name in COMPANY_FILES:
        for c in load_companies(settings.SEED_DIR / name, trust_config(), as_of):
            if c.fictional and not c.name.endswith("(Demo)"):
                raise ValueError(f"fictional company {c.id!r} must keep '(Demo)' in its name")
            if db.get(models.Company, c.id) is None:
                db.add(company_row(c))
                added += 1
    return added


def seed_smes(db: Session) -> int:
    added = 0
    for name in SME_FILES:
        raw = json.loads((settings.SEED_DIR / name).read_text(encoding="utf-8"))
        if db.get(models.Sme, raw["id"]) is None:
            db.add(models.Sme(id=raw["id"], **{k: raw[k] for k in SME_COLUMNS if k in raw}))
            added += 1
    return added


def seed(db: Session, as_of: dt.date, wipe: bool = False, keep_users: bool = False) -> dict[str, int]:
    """Load the seed files. `wipe` empties the tables first; `keep_users` spares the users table (the
    admin's "Reset demo data" button, so whoever pressed it stays signed in)."""
    if wipe:
        reset(db, keep_users=keep_users)
    counts = {"users": seed_users(db), "companies": seed_companies(db, as_of), "smes": seed_smes(db)}
    db.commit()
    return counts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.seed", description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="wipe every table, then reload")
    args = parser.parse_args(argv)
    as_of = scoring_date()
    with SessionLocal() as db:
        counts = seed(db, as_of, wipe=args.reset)
    added = ", ".join(f"{n} {k}" for k, n in counts.items())
    print(f"seed ({'reset' if args.reset else 'incremental'}, dates as of {as_of}): added {added}")


if __name__ == "__main__":
    main()
