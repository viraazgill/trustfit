"""Typed loader for config/gap_bridge_v1.yaml. Every number the Gap Bridge uses comes from here."""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

CompanyType = Literal["business_partner", "service_provider"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReadinessDimension(_Model):
    label: str
    jetro_ask: str
    questions: dict[str, str]


class SeverityLabel(_Model):
    min: float
    label: str


class Capability(_Model):
    label: str
    source: Literal["trust", "fit", "service_states", "declared"]
    parameters: list[str] | None = None  # source trust: the Trust parameters it is derived from
    factor: str | None = None            # source fit: the Fit factor it is derived from
    applies_to: CompanyType | None = None


class MatchWeights(_Model):
    fit: float
    gap_coverage: float


class BridgeRules(_Model):
    match_weights: MatchWeights
    max_supporting_partners: int
    min_marginal_gain: float
    target_team_coverage: float
    per_gap_top_n: int
    per_gap_min_coverage: float
    list_gaps_with_labels: list[str]
    partly_covered_below: float
    not_covered_below: float


class BridgeConfig(_Model):
    version: str
    answer_scale: dict[int, str]
    dimensions: dict[str, ReadinessDimension]
    relevance: dict[str, dict[str, float]]
    severity_labels: list[SeverityLabel]
    covered_by_trustfit: list[str]
    capabilities: dict[str, Capability]
    unverified_factor: float
    gap_needs: dict[str, dict[str, float]]
    bridge: BridgeRules

    @model_validator(mode="after")
    def _check(self) -> BridgeConfig:
        errors: list[str] = []
        dims = set(self.dimensions)
        for role, rel in self.relevance.items():
            if set(rel) != dims:
                errors.append(f"relevance.{role}: dimensions {sorted(rel)} != {sorted(dims)}")
        mins = [s.min for s in self.severity_labels]
        if mins != sorted(mins, reverse=True) or not mins or mins[-1] != 0:
            errors.append("severity_labels must run from highest min down to 0")
        for d in self.covered_by_trustfit:
            if d not in dims:
                errors.append(f"covered_by_trustfit: unknown dimension {d}")
        for cap, spec in self.capabilities.items():
            if spec.source == "trust" and not spec.parameters:
                errors.append(f"capability {cap}: source trust needs parameters")
            if spec.source == "fit" and not spec.factor:
                errors.append(f"capability {cap}: source fit needs a factor")
        for gap, needs in self.gap_needs.items():
            if gap not in dims or gap in self.covered_by_trustfit:
                errors.append(f"gap_needs.{gap}: not a partner-coverable dimension")
            for cap in needs:
                if cap not in self.capabilities:
                    errors.append(f"gap_needs.{gap}: unknown capability {cap}")
            if not math.isclose(sum(needs.values()), 1.0, abs_tol=1e-9):
                errors.append(f"gap_needs.{gap} weights must sum to 1, got {sum(needs.values())}")
        missing = dims - set(self.covered_by_trustfit) - set(self.gap_needs)
        if missing:
            errors.append(f"gap_needs is missing {sorted(missing)}")
        labels = {s.label for s in self.severity_labels}
        for label in self.bridge.list_gaps_with_labels:
            if label not in labels:
                errors.append(f"bridge.list_gaps_with_labels: unknown severity label {label!r}")
        if errors:
            raise ValueError("invalid gap bridge config:\n  " + "\n  ".join(errors))
        return self

    @property
    def max_answer(self) -> int:
        return max(self.answer_scale)

    @property
    def questions(self) -> dict[str, str]:
        """Every readiness question id -> its dimension."""
        return {q: d for d, spec in self.dimensions.items() for q in spec.questions}


def load_bridge_config(path: str | os.PathLike[str]) -> BridgeConfig:
    """Load and validate a Gap Bridge config file. Raises on any inconsistency."""
    return BridgeConfig.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
