"""Typed engine inputs. Results are plain dicts with exactly the reference's keys
(see `TrustResult` for their shape) so they serialise straight to the golden JSON."""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FlagType = Literal["knockout", "cap", "notch", "fake_reviews"]
GateStatus = Literal["passed", "pending", "failed"]
Direction = Literal["improving", "stable", "worsening"]


class Evidence(BaseModel):
    level: int
    verified: bool
    source_url: str | None = None
    source_date: dt.date | None = None
    checked_at: dt.date | None = None
    note: str | None = None  # analyst note: confidential


class Flag(BaseModel):
    type: FlagType
    code: str
    note: str | None = None
    source_url: str | None = None


class Trend(BaseModel):
    direction: Direction
    note: str | None = None


class Company(BaseModel):
    """One Indian company. Seed-only fields (cin, description, hq_state, ...) are kept as extras."""
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    fictional: bool = False
    type: Literal["business_partner", "service_provider"] = "business_partner"
    roles_offered: list[str] = Field(default_factory=list)
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    flags: list[Flag] = Field(default_factory=list)
    gates: dict[str, GateStatus] = Field(default_factory=dict)  # absent = pending
    trends: dict[str, Trend] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)       # Fit attributes (phase 4)
    capabilities: dict[str, Any] = Field(default_factory=dict)  # Gap Bridge tags (phase 5)


class Sme(BaseModel):
    """One Japanese SME's brief (Fit) and readiness answers (Gap Bridge). Descriptive fields such as
    name, city and employees are kept as extras."""
    model_config = ConfigDict(extra="allow")

    id: str
    sector: str
    products: list[str] = Field(default_factory=list)
    role_sought: str
    target_states: dict[str, list[str]] = Field(default_factory=dict)  # {primary: [...], secondary: [...]}
    channels_needed: list[str] = Field(default_factory=list)
    volume_units_per_month: int | None = None
    after_sales_need: Literal["none", "basic", "full"] = "none"
    competitors: list[str] = Field(default_factory=list)
    factor_importance: dict[str, str] = Field(default_factory=dict)
    readiness_answers: dict[str, int] = Field(default_factory=dict)


class WhatIf(BaseModel):
    """Hypothetical evidence (treated as verified, dated as_of) and gate results."""
    model_config = ConfigDict(extra="forbid")

    evidence: dict[str, int] = Field(default_factory=dict)
    gates: dict[str, GateStatus] = Field(default_factory=dict)


class Reason(BaseModel):
    code: str
    text: str


class CategoryStats(BaseModel):
    label: str
    points: float
    verified_points: float
    earned_points: float
    verified_pct: float | None
    score_pct: float | None


class ParameterResult(BaseModel):
    status: Literal["missing", "unverified", "stale", "excluded", "verified"]
    level: int | None
    points: float


class TrustResult(BaseModel):
    """Shape of a `score_trust` result. Knock-out and insufficient-data results omit the
    score breakdown, so those fields are optional."""
    model_config = ConfigDict(extra="forbid")

    company_id: str
    role: str
    as_of: str
    weight_set: str
    what_if: bool
    eligible: bool
    status: Literal["scored", "insufficient_data", "not_eligible"]
    score: int | None
    band: str | None
    confidence: float | None
    provisional: bool | None
    verdict: Literal["Green", "Amber", "Red"]
    outlook: str | None
    reasons: list[Reason]
    knockouts: list[Reason] | None = None
    score_raw: float | None = None
    base_score: float | None = None
    notches: int | None = None
    notch_list: list[dict[str, Any]] | None = None
    weakest_dimension: float | None = None
    weakest_limit: float | None = None
    cap: int | None = None
    cap_list: list[dict[str, Any]] | None = None
    binding_limit: Literal["score", "weakest_link", "cap"] | None = None
    categories: dict[str, CategoryStats] | None = None
    dimensions: dict[str, CategoryStats] | None = None
    gates: dict[str, GateStatus] | None = None
    parameters: dict[str, ParameterResult] | None = None
    next_checks: list[dict[str, Any]] | None = None
