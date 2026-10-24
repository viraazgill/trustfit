from typing import Any

from fastapi import APIRouter, Depends

from app.auth import analyst
from app.schemas import PublicConfig
from app.services.scoring import trust_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/public")
def public_config() -> PublicConfig:
    """Categories, dimensions and role weights. No rubric text or check instructions."""
    cfg = trust_config()
    return PublicConfig(
        version=cfg.version, disclaimer=cfg.disclaimer, scale_levels=cfg.scale_levels,
        roles={k: {"label": v.label} for k, v in cfg.roles.items()},
        dimensions={k: v.model_dump() for k, v in cfg.dimensions.items()},
        categories={k: v.model_dump() for k, v in cfg.categories.items()},
        category_weights=cfg.category_weights,
        bands=[b.model_dump() for b in cfg.bands],
        gates={k: {"label": v.label} for k, v in cfg.gates.items()},
        outlook_signals=cfg.outlook.signals,
        confidence=cfg.confidence.model_dump(),
        service_provider_trust_role=cfg.service_provider_trust_role,
    )


@router.get("/rubrics", dependencies=[Depends(analyst)])
def rubrics() -> dict[str, Any]:
    """CONFIDENTIAL (analyst/admin): parameter rubrics, where to check, override and gate checks."""
    cfg = trust_config()
    return {
        "version": cfg.version,
        "parameter_splits": cfg.parameter_splits,
        "parameters": {k: v.model_dump() for k, v in cfg.parameters.items()},
        "overrides": cfg.overrides.model_dump(),
        "gates": {k: v.model_dump() for k, v in cfg.gates.items()},
        "freshness": cfg.freshness.model_dump(),
    }
