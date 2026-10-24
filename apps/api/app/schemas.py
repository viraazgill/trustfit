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


class ViewerPending(BaseModel):
    """One line of the SME-facing 'What turns it Green': a category's unchecked points, or a pending gate."""
    type: Literal["category", "gate"]
    id: str
    label: str
    count: int = Field(description="Unchecked parameters in the category (1 for a gate)")
    points: float | None = Field(description="Points still unverified in the category; null for a gate")
    priority: bool = Field(description="In a dimension under the verified minimum: check these first")


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
    pending: list[ViewerPending] = Field(default_factory=list,
                                         description="What turns it Green, by category (no parameter detail)")
    disclaimer: str = DISCLAIMER_FIELD


# ---------------------------------------------------------------- SMEs and Fit (viewer-safe)

Importance = Literal["must", "important", "nice", "irrelevant"]
RoleSought = Literal["supplier", "distributor", "jv_partner"]
AfterSalesNeed = Literal["none", "basic", "full"]


class TargetStates(_In):
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)


class SmeIn(_In):
    """An SME brief. Vocabulary values (sector, states, channels) are checked against config/fit_v1.yaml."""
    name: str = Field(min_length=1, max_length=300)
    country: str | None = "Japan"
    city: str | None = None
    employees: int | None = Field(default=None, ge=1)
    description: str | None = None
    sector: str
    products: list[str] = Field(default_factory=list)
    role_sought: RoleSought
    target_states: TargetStates
    channels_needed: list[str] = Field(default_factory=list)
    volume_units_per_month: int = Field(ge=1)
    after_sales_need: AfterSalesNeed = "none"
    competitors: list[str] = Field(default_factory=list)
    factor_importance: dict[str, Importance] = Field(default_factory=dict)


class SmePatch(_In):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    country: str | None = None
    city: str | None = None
    employees: int | None = Field(default=None, ge=1)
    description: str | None = None
    sector: str | None = None
    products: list[str] | None = None
    role_sought: RoleSought | None = None
    target_states: TargetStates | None = None
    channels_needed: list[str] | None = None
    volume_units_per_month: int | None = Field(default=None, ge=1)
    after_sales_need: AfterSalesNeed | None = None
    competitors: list[str] | None = None
    factor_importance: dict[str, Importance] | None = None


class SmeOut(BaseModel):
    id: str
    name: str
    fictional: bool
    country: str | None
    city: str | None
    employees: int | None
    description: str | None
    sector: str
    products: list[str]
    role_sought: str
    target_states: TargetStates
    channels_needed: list[str]
    volume_units_per_month: int | None
    after_sales_need: str | None
    competitors: list[str]
    factor_importance: dict[str, str]
    readiness_answers: dict[str, int]
    mine: bool = Field(description="The signed-in user owns this SME and may edit it")


class FitFactor(BaseModel):
    label: str
    importance: str
    weight: float
    level: int | None
    verified: bool


class FitConflict(BaseModel):
    brand: str
    relation: str


class TrustSummary(BaseModel):
    role: str
    eligible: bool
    status: str
    score: int | None
    band: str | None
    confidence: float | None
    provisional: bool | None
    verdict: Verdict


class ViewerFit(BaseModel):
    company_id: str
    company_name: str
    fictional: bool
    sme_id: str
    role: str
    score: int | None
    score_raw: float | None
    confidence: float
    category: Literal["strong_fit", "possible_fit", "not_a_fit"]
    category_label: str
    action: str
    factors: dict[str, FitFactor]
    gaps: list[str]
    competitor_conflict: bool
    conflict: FitConflict | None = Field(description="The blocking competitor relation, when there is one")
    trust: TrustSummary
    combined_verdict: Verdict = Field(description="Trust verdict after Fit (it can lower it, never raise it)")
    reasons: list[ViewerReason]
    disclaimer: str = DISCLAIMER_FIELD


# ---------------------------------------------------------------- readiness and Gap Bridge (viewer-safe)

class ReadinessIn(_In):
    answers: dict[str, int] = Field(description="Question id (R1.1 ... R6.3) -> answer on the 0-4 scale")


class ReadinessDimension(BaseModel):
    label: str
    jetro_ask: str
    readiness: float
    severity: float
    severity_label: str
    covered_by_trustfit: bool


class ReadinessOut(BaseModel):
    sme_id: str
    answered: bool
    answers: dict[str, int]
    dimensions: dict[str, ReadinessDimension] = Field(default_factory=dict)


class BridgeCompany(BaseModel):
    company_id: str
    name: str
    fictional: bool
    type: str
    trust_role: str
    trust_score: int | None
    trust_verdict: Verdict
    provisional: bool | None
    fit: int | None
    fit_category: str | None
    combined_verdict: Verdict
    eligible: bool
    excluded_because: list[str]
    strengths: dict[str, float]
    gap_coverage: float
    per_gap: dict[str, float]
    match: float | None = None


class BridgeRanking(BaseModel):
    company_id: str
    match: float
    fit: int
    gap_coverage: float


class BridgeCovers(BaseModel):
    gap: str
    capability: str
    label: str
    strength: float
    verified: bool


class BridgeTeamMember(BaseModel):
    company_id: str
    slot: Literal["primary", "support"]
    gain: float
    covers: list[BridgeCovers]


class BridgeGapStatus(BaseModel):
    team_coverage: float
    status: Literal["covered", "partly covered", "not covered"]


class BridgeShortlistEntry(BaseModel):
    company_id: str
    coverage: float
    reason: str = Field(description="One line from the company's strongest capability for this gap")


class ViewerBridge(BaseModel):
    sme_id: str
    as_of: dt.date
    config_version: str
    readiness: dict[str, ReadinessDimension]
    companies: list[BridgeCompany]
    primary_ranking: list[BridgeRanking]
    team: list[BridgeTeamMember]
    team_coverage: float
    gap_status: dict[str, BridgeGapStatus]
    per_gap: dict[str, list[BridgeShortlistEntry]]
    disclaimer: str = DISCLAIMER_FIELD


class ResetOut(BaseModel):
    as_of: dt.date
    added: dict[str, int]


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


class PublicConfidence(BaseModel):
    no_score_below: int
    provisional_below: int
    dimension_provisional_below: int


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
    confidence: PublicConfidence
    service_provider_trust_role: str
    scoring_date: dt.date = Field(description="The date every score is computed as of")
    fixed_scoring_date: bool = Field(description="True when SCORING_AS_OF pins the date (demo mode)")


class PublicFitFactor(BaseModel):
    label: str
    base_weight: float


class PublicFitCategory(BaseModel):
    label: str
    action: str


class PublicFitConfig(BaseModel):
    version: str
    factors: dict[str, PublicFitFactor]
    importance_levels: list[str]
    role_default_importance: dict[str, dict[str, str]]
    categories: dict[str, PublicFitCategory]
    sectors: list[str]
    product_families: dict[str, list[str]]
    channels: list[str]
    states: list[str]
    after_sales_needs: list[str]
    relations: list[str]


class PublicReadinessDimension(BaseModel):
    label: str
    jetro_ask: str
    questions: dict[str, str]


class PublicBridgeConfig(BaseModel):
    version: str
    answer_scale: dict[int, str]
    dimensions: dict[str, PublicReadinessDimension]
    severity_labels: list[dict[str, Any]]
    covered_by_trustfit: list[str]
    capabilities: dict[str, str] = Field(description="capability -> label")
    gap_needs: dict[str, dict[str, float]]
    target_team_coverage: float = Field(description="The India entry team stops growing at this coverage %")
