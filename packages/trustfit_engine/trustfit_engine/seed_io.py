"""Load seed files into Company models.

Two formats:
- full (seed/subros.json): one company, evidence per parameter with a named source
- compact (seed/demo_companies.json): {"evidence_defaults", "companies": [...]}, levels per category
  in parameter order, null = no verified evidence

Dates may be ISO or "today-Nd", resolved against the scoring date so the demo never goes stale.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

from trustfit_engine.config import TrustConfig
from trustfit_engine.models import Company

_RELATIVE = re.compile(r"^today-(\d+)d$")
_COMPANY_FIELDS_DROPPED = ("_note", "_format", "trust_evidence", "sources", "pending_checks", "as_of")


def resolve_date(value: str | None, as_of: dt.date) -> dt.date | None:
    """ISO date, or 'today-Nd' relative to the scoring date."""
    if value is None:
        return None
    m = _RELATIVE.match(value)
    if m:
        return as_of - dt.timedelta(days=int(m.group(1)))
    return dt.date.fromisoformat(value)


def _full_company(raw: dict[str, Any], as_of: dt.date) -> Company:
    sources = raw.get("sources", {})
    evidence = {}
    for pid, ev in raw.get("evidence", {}).items():
        src = sources.get(ev.get("source"), {})
        evidence[pid] = {
            "level": ev["level"],
            "verified": ev["verified"],
            "source_url": src.get("url"),
            "source_date": resolve_date(ev.get("source_date", src.get("date")), as_of),
            "checked_at": resolve_date(ev.get("checked_at", raw.get("as_of")), as_of),
            "note": ev.get("note"),
        }
    flags = [{"type": f["type"], "code": f["code"], "note": f.get("note"),
              "source_url": f.get("source_url") or sources.get(f.get("source"), {}).get("url")}
             for f in raw.get("flags", [])]
    return _company(raw, evidence, flags, raw.get("trends", {}))


def _compact_company(raw: dict[str, Any], defaults: dict[str, str], cfg: TrustConfig,
                     as_of: dt.date) -> Company:
    evidence = {}
    for cat, levels in raw["trust_evidence"].items():
        pids = [pid for pid, spec in cfg.parameters.items() if spec.category == cat]
        if len(levels) != len(pids):
            raise ValueError(f"{raw['id']}: category {cat} has {len(levels)} levels, expected {len(pids)}")
        for pid, level in zip(pids, levels, strict=True):
            if level is None:
                continue
            evidence[pid] = {
                "level": level,
                "verified": True,
                "source_url": defaults["source_url"].format(company_id=raw["id"], parameter_id=pid),
                "source_date": resolve_date(defaults["source_date"], as_of),
                "checked_at": resolve_date(defaults["checked_at"], as_of),
            }
    trends = {k: {"direction": v} for k, v in raw.get("trends", {}).items()}
    return _company(raw, evidence, raw.get("flags", []), trends)


def _company(raw: dict[str, Any], evidence: dict, flags: list, trends: dict) -> Company:
    rest = {k: v for k, v in raw.items() if k not in _COMPANY_FIELDS_DROPPED}
    return Company.model_validate({**rest, "evidence": evidence, "flags": flags, "trends": trends})


def parse_companies(data: dict[str, Any], cfg: TrustConfig, as_of: dt.date) -> list[Company]:
    """A compact file gives many companies; a full-format file gives one."""
    if "companies" in data:
        return [_compact_company(c, data["evidence_defaults"], cfg, as_of) for c in data["companies"]]
    return [_full_company(data, as_of)]


def load_companies(path: str | os.PathLike[str], cfg: TrustConfig, as_of: dt.date) -> list[Company]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_companies(data, cfg, as_of)
