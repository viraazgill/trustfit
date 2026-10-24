"""Command line: python -m trustfit_engine trust seed/subros.json --role supplier --as-of 2026-10-24"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from trustfit_engine.config import default_config_dir, load_trust_config
from trustfit_engine.models import WhatIf
from trustfit_engine.seed_io import load_companies
from trustfit_engine.trust import score_trust


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="trustfit_engine", description="TrustFit scoring engine")
    sub = p.add_subparsers(dest="command", required=True)
    t = sub.add_parser("trust", help="Trust Score for one company, printed as JSON")
    t.add_argument("seed_file", type=Path, help="seed JSON (full or compact format)")
    t.add_argument("--role", required=True)
    t.add_argument("--as-of", required=True, type=dt.date.fromisoformat, help="scoring date, YYYY-MM-DD")
    t.add_argument("--company", help="company id (required when the file holds several)")
    t.add_argument("--what-if", type=Path, help='JSON file: {"evidence": {pid: level}, "gates": {...}}')
    t.add_argument("--config-dir", type=Path, help="defaults to $CONFIG_DIR or ./config")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cfg = load_trust_config((args.config_dir or default_config_dir()) / "trust_v1.yaml")
    companies = load_companies(args.seed_file, cfg, args.as_of)
    if args.company:
        matches = [c for c in companies if c.id == args.company]
        if not matches:
            print(f"no company {args.company!r} in {args.seed_file}", file=sys.stderr)
            return 2
        company = matches[0]
    elif len(companies) == 1:
        company = companies[0]
    else:
        print(f"{args.seed_file} holds {len(companies)} companies; pass --company", file=sys.stderr)
        return 2
    what_if = WhatIf.model_validate_json(args.what_if.read_text(encoding="utf-8")) if args.what_if else None
    result = score_trust(company, args.role, cfg, args.as_of, what_if=what_if)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
