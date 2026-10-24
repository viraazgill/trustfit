"""Request and response schemas.

Viewer (SME) responses use the `Viewer*`/`Public*` schemas below. They are separate on purpose and
must never carry rubric text, where_to_check, check instructions, analyst notes or evidence source
URLs; tests/test_viewer_safety.py fails if a field like that ever appears.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trustfit_engine.models import GateStatus, WhatIf

Verdict = Literal["Green", "Amber", "Red"]
DISCLAIMER_FIELD = Field(description="TrustFit Score is not a credit rating or investment advice.")


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- auth

class LoginIn(_In):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: str


class MeOut(BaseModel):
    id: int
    email: str
    role: str


# ---------------------------------------------------------------- companies (viewer-safe)

class LatestScore(BaseModel):
    role: str
    score: int | None
    verdict: Verdict
    confidence: float | None
    as_of: dt.date


class ViewerCompanyListItem(BaseModel):
    id: str
    name: str
    fictional: bool
    type: str
    roles_offered: list[str]
    hq_state: str | None
    latest: LatestScore | None = None


class ViewerCompany(BaseModel):
    id: str
    name: str
    fictional: bool
    type: str
    roles_offered: list[str]
    cin: str | None
    nse_code: str | None
    bse_code: str | None
    msme_category: str | None
    hq_state: str | None
    description: str | None
    profile: dict[str, Any]
    capabilities: dict[str, Any]
    gates: dict[str, GateStatus]
    trends: dict[str, str] = Field(description="signal -> direction (analyst notes left out)")


class CompanyCreate(_In):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,99}$")
    name: str = Field(min_length=1, max_length=300)
    fictional: bool = False
    type: Literal["business_partner", "service_provider"] = "business_partner"
    roles_offered: list[str] = Field(default_factory=list)
    cin: str | None = None
    nse_code: str | None = None
    bse_code: str | None = None
    msme_category: str | None = None
    hq_state: str | None = None
    description: str | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    capabilities: dict[str, Any] = Field(default_factory=dict)


class CompanyPatch(_In):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    fictional: bool | None = None
    type: Literal["business_partner", "service_provider"] | None = None
    roles_offered: list[str] | None = None
    cin: str | None = None
    nse_code: str | None = None
    bse_code: str | None = None
    msme_category: str | None = None
    hq_state: str | None = None
    description: str | None = None
    profile: dict[str, Any] | None = None
    capabilities: dict[str, Any] | None = None


# ---------------------------------------------------------------- analyst: evidence, flags, trends

class EvidenceIn(_In):
    level: int
    verified: bool
    source_url: str | None = None
    source_date: dt.date | None = None
    checked_at: dt.date | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _verified_needs_source(self) -> EvidenceIn:
        if self.verified and not self.source_url:
            raise ValueError("verified evidence needs a source_url")
        if self.verified and self.source_date is None:
            raise ValueError("verified evidence needs a source_date")
        return self


class EvidenceRow(BaseModel):
    parameter_id: str
    category: str
    name: str
    status: Literal["missing", "unverified", "stale", "verified"]
    level: int | None = None
    verified: bool | None = None
    source_url: str | None = None
    source_date: dt.date | None = None
    checked_at: dt.date | None = None
    note: str | None = None
    updated_at: dt.datetime | None = None


class EvidenceHistoryRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: int
    verified: bool
    source_url: str | None
    source_date: dt.date | None
    checked_at: dt.date | None
    note: str | None
    changed_by: int | None
    changed_at: dt.datetime


class FlagIn(_In):
    type: Literal["knockout", "cap", "notch", "fake_reviews"]
    code: str = Field(min_length=1, max_length=60)
    note: str | None = None
    source_url: str | None = None


class FlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    code: str
    note: str | None
    source_url: str | None


class TrendIn(_In):
    direction: Literal["improving", "stable", "worsening"]
    note: str | None = None


# ---------------------------------------------------------------- trust

class TrustScoreIn(_In):
    role: str
    what_if: WhatIf | None = None


class TrustRunOut(BaseModel):
    run_id: int
    is_what_if: bool
    result: dict[str, Any] = Field(description="Full engine result (analyst view)")


class ViewerReason(BaseModel):
    code: str
    text: str


class ViewerCategory(BaseModel):
    label: str
    weight: float = Field(description="Points out of 100 for this role")
    verified_pct: float | None
    score_pct: float | None


class ViewerTrustReport(BaseModel):
    company_id: str
    company_name: str
    fictional: bool
    role: str
    as_of: dt.date
    weight_set: str
    eligible: bool
    status: str
    score: int | None
    band: str | None
    confidence: float | None
    provisional: bool | None
    verdict: Verdict
    outlook: str | None
    categories: dict[str, ViewerCategory] = Field(default_factory=dict)
    dimensions: dict[str, ViewerCategory] = Field(default_factory=dict)
    gates: dict[str, GateStatus] = Field(default_factory=dict)
    reasons: list[ViewerReason]
    disclaimer: str = DISCLAIMER_FIELD


# ---------------------------------------------------------------- config

class PublicLabel(BaseModel):
    label: str


class PublicDimension(BaseModel):
    label: str
    question: str
    categories: list[str]


class PublicCategory(BaseModel):
    label: str
    dimension: str


class PublicBand(BaseModel):
    min: int
    label: str


class PublicConfig(BaseModel):
    version: str
    disclaimer: str
    scale_levels: list[int]
    roles: dict[str, PublicLabel]
    dimensions: dict[str, PublicDimension]
    categories: dict[str, PublicCategory]
    category_weights: dict[str, dict[str, int]]
    bands: list[PublicBand]
    gates: dict[str, PublicLabel]
    outlook_signals: dict[str, str]
