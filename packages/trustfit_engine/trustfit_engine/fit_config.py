"""Typed loader for config/fit_v1.yaml. Every number the Fit engine uses comes from here."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

Importance = Literal["must", "important", "nice", "irrelevant"]
FIT_CATEGORIES = ("strong_fit", "possible_fit", "not_a_fit")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactorSpec(_Model):
    label: str
    base_weight: float


class StatePriorityWeights(_Model):
    primary: float
    secondary: float


class Conflict(_Model):
    blocking_relations: list[str]
    partial_relations: list[str]


class FitCategory(_Model):
    label: str
    action: str
    min_score: float | None = None
    min_confidence: float | None = None
    rule: str | None = None


class Vocabularies(_Model):
    sectors: list[str]
    related_sectors: dict[str, list[str]]
    product_families: dict[str, list[str]]
    channels: list[str]
    states: list[str]


class FitConfig(_Model):
    version: str
    scale_levels: list[int]
    factors: dict[str, FactorSpec]
    importance_multipliers: dict[Importance, float]
    role_default_importance: dict[str, dict[str, Importance]]
    state_priority_weights: StatePriorityWeights
    coverage_levels: list[tuple[float, int]]
    capacity_levels: list[tuple[float, int]]
    conflict: Conflict
    categories: dict[str, FitCategory]
    vocabularies: Vocabularies

    @model_validator(mode="after")
    def _check(self) -> FitConfig:
        errors: list[str] = []
        if set(self.importance_multipliers) != {"must", "important", "nice", "irrelevant"}:
            errors.append("importance_multipliers must define must, important, nice and irrelevant")
        for role, imp in self.role_default_importance.items():
            if set(imp) != set(self.factors):
                errors.append(f"role_default_importance.{role}: factors {sorted(imp)} != {sorted(self.factors)}")
        for name in ("coverage_levels", "capacity_levels"):
            table = getattr(self, name)
            thresholds = [t for t, _ in table]
            if thresholds != sorted(thresholds, reverse=True):
                errors.append(f"{name}: thresholds must be listed from highest to lowest")
            for _, level in table:
                if level not in self.scale_levels:
                    errors.append(f"{name}: level {level} is not one of {self.scale_levels}")
        if set(self.categories) != set(FIT_CATEGORIES):
            errors.append(f"categories must be {list(FIT_CATEGORIES)}")
        else:
            if self.categories["strong_fit"].min_score is None or self.categories["strong_fit"].min_confidence is None:
                errors.append("categories.strong_fit needs min_score and min_confidence")
            if self.categories["possible_fit"].min_score is None:
                errors.append("categories.possible_fit needs min_score")
        overlap = set(self.conflict.blocking_relations) & set(self.conflict.partial_relations)
        if overlap:
            errors.append(f"conflict: {sorted(overlap)} are both blocking and partial")
        voc = self.vocabularies
        for sector, related in voc.related_sectors.items():
            for s in [sector, *related]:
                if s not in voc.sectors:
                    errors.append(f"vocabularies.related_sectors: unknown sector {s!r}")
        if errors:
            raise ValueError("invalid fit config:\n  " + "\n  ".join(errors))
        return self

    @property
    def relations(self) -> list[str]:
        return [*self.conflict.blocking_relations, *self.conflict.partial_relations]


def load_fit_config(path: str | os.PathLike[str]) -> FitConfig:
    """Load and validate a Fit config file. Raises on any inconsistency."""
    return FitConfig.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
