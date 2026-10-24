"""Typed loader for config/trust_v1.yaml. Every number the Trust engine uses comes from here."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

POINTS_TOTAL = 100  # category weights per role and splits per category are percentages


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoleSpec(_Model):
    label: str


class DimensionSpec(_Model):
    label: str
    question: str
    categories: list[str]


class CategorySpec(_Model):
    label: str
    dimension: str


class ParameterSpec(_Model):
    category: str
    name: str
    tier: str
    recheck_days: int | None = None
    knockout_at_zero: bool = False
    max_level_if_revenue_below_25_crore: int | None = None
    note: str | None = None
    rubric: dict[int, str]  # confidential: analyst/admin only
    where_to_check: str     # confidential: analyst/admin only


class Freshness(_Model):
    max_source_age_days: int


class KnockoutSpec(_Model):
    label: str
    check: str


class CapSpec(_Model):
    label: str
    max_score: int
    check: str


class FakeReviewsSpec(_Model):
    label: str
    effect: str
    check: str


class NotchSpec(_Model):
    label: str
    points: int
    check: str


class Overrides(_Model):
    knockouts: dict[str, KnockoutSpec]
    caps: dict[str, CapSpec]
    fake_reviews: FakeReviewsSpec
    notches: dict[str, NotchSpec]
    notch_total_limit: int
    weakest_link_margin: int


class GateSpec(_Model):
    label: str
    check: str


class Band(_Model):
    min: int
    label: str


class ConfidenceRules(_Model):
    no_score_below: int
    provisional_below: int
    dimension_provisional_below: int


class VerdictRules(_Model):
    red_below: int
    green_from: int
    fit_red_below: int
    fit_green_from: int


class OutlookRules(_Model):
    signals: dict[str, str]
    positive_if_improving_at_least: int
    watch_if_worsening_at_least: int


class TrustConfig(_Model):
    version: str
    scale_levels: list[int]
    roles: dict[str, RoleSpec]
    dimensions: dict[str, DimensionSpec]
    categories: dict[str, CategorySpec]
    category_weights: dict[str, dict[str, int]]
    parameter_splits: dict[str, dict[str, int]]
    freshness: Freshness
    parameters: dict[str, ParameterSpec]
    overrides: Overrides
    gates: dict[str, GateSpec]
    bands: list[Band]
    confidence: ConfidenceRules
    verdict: VerdictRules
    outlook: OutlookRules
    service_provider_trust_role: str
    disclaimer: str

    @model_validator(mode="after")
    def _check(self) -> TrustConfig:
        errors: list[str] = []
        cats = set(self.categories)
        for pid, spec in self.parameters.items():
            if spec.category not in cats:
                errors.append(f"parameter {pid}: unknown category {spec.category!r}")
            if sorted(spec.rubric) != sorted(self.scale_levels):
                errors.append(f"parameter {pid}: rubric levels {sorted(spec.rubric)} "
                              f"must be {self.scale_levels}")
        for dim, spec in self.dimensions.items():
            for cat in spec.categories:
                if cat not in cats or self.categories[cat].dimension != dim:
                    errors.append(f"dimension {dim}: category {cat} does not belong to it")
        if set(self.category_weights) != set(self.roles):
            errors.append(f"category_weights roles {sorted(self.category_weights)} "
                          f"!= roles {sorted(self.roles)}")
        for role, weights in self.category_weights.items():
            if set(weights) != cats:
                errors.append(f"category_weights.{role}: categories {sorted(weights)} != {sorted(cats)}")
            if sum(weights.values()) != POINTS_TOTAL:
                errors.append(f"category_weights.{role} must sum to {POINTS_TOTAL}, "
                              f"got {sum(weights.values())}")
        default = self.parameter_splits.get("default", {})
        for pid in self.parameters:
            if pid not in default:
                errors.append(f"parameter_splits.default is missing {pid}")
        for key, splits in self.parameter_splits.items():
            for pid in splits:
                if pid not in self.parameters:
                    errors.append(f"parameter_splits.{key}: unknown parameter {pid}")
            if key != "default" and key not in self.roles:
                errors.append(f"parameter_splits.{key}: unknown role")
        if not errors:
            for role in self.roles:
                for cat in self.categories:
                    total = sum(self.split(role, pid)
                                for pid, s in self.parameters.items() if s.category == cat)
                    if total != POINTS_TOTAL:
                        errors.append(f"parameter split for {role}, category {cat} "
                                      f"must sum to {POINTS_TOTAL}, got {total}")
        if self.service_provider_trust_role not in self.roles:
            errors.append(f"service_provider_trust_role {self.service_provider_trust_role!r} is not a role")
        if errors:
            raise ValueError("invalid trust config:\n  " + "\n  ".join(errors))
        return self

    def split(self, role: str, pid: str) -> int:
        """A parameter's percent of its category, after role overrides."""
        return self.parameter_splits.get(role, {}).get(pid, self.parameter_splits["default"][pid])

    def parameter_points(self, role: str, pid: str) -> float:
        """Category weight x split / 100 (supplier A4 = 15 x 35 / 100 = 5.25)."""
        return self.category_weights[role][self.parameters[pid].category] * self.split(role, pid) / 100

    def dimension_of(self, category: str) -> str:
        return self.categories[category].dimension


def load_trust_config(path: str | os.PathLike[str]) -> TrustConfig:
    """Load and validate a Trust config file. Raises on any inconsistency."""
    text = Path(path).read_text(encoding="utf-8")
    return TrustConfig.model_validate(yaml.safe_load(text))


def default_config_dir() -> Path:
    """$CONFIG_DIR, else ./config, else the repo's config/ next to this package (editable installs)."""
    env = os.environ.get("CONFIG_DIR")
    if env:
        return Path(env)
    for candidate in (Path.cwd() / "config", Path(__file__).resolve().parents[3] / "config"):
        if (candidate / "trust_v1.yaml").is_file():
            return candidate
    raise FileNotFoundError("config/trust_v1.yaml not found; set CONFIG_DIR or pass --config-dir")
