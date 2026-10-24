from typing import Any, get_args

from fastapi import APIRouter, Depends

from app.auth import analyst
from app.schemas import AfterSalesNeed, PublicBridgeConfig, PublicConfig, PublicFitConfig
from app.services.bridge import bridge_config
from app.services.fit import fit_config
from app.services.scoring import trust_config
from app.settings import scoring_date, settings

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
        scoring_date=scoring_date(), fixed_scoring_date=settings.SCORING_AS_OF is not None,
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


@router.get("/fit")
def public_fit_config() -> PublicFitConfig:
    """Fit factors, role defaults, categories and the brief vocabularies (for the SME wizard)."""
    cfg = fit_config()
    voc = cfg.vocabularies
    return PublicFitConfig(
        version=cfg.version,
        factors={k: v.model_dump() for k, v in cfg.factors.items()},
        importance_levels=list(cfg.importance_multipliers),
        role_default_importance=cfg.role_default_importance,
        categories={k: {"label": v.label, "action": v.action} for k, v in cfg.categories.items()},
        sectors=voc.sectors, product_families=voc.product_families, channels=voc.channels, states=voc.states,
        after_sales_needs=list(get_args(AfterSalesNeed)), relations=cfg.relations,
    )


@router.get("/bridge")
def public_bridge_config() -> PublicBridgeConfig:
    """The 16 readiness questions by JETRO ask, the answer scale, severity labels and capability labels."""
    cfg = bridge_config()
    return PublicBridgeConfig(
        version=cfg.version, answer_scale=cfg.answer_scale,
        dimensions={k: v.model_dump() for k, v in cfg.dimensions.items()},
        severity_labels=[s.model_dump() for s in cfg.severity_labels],
        covered_by_trustfit=cfg.covered_by_trustfit,
        capabilities={k: v.label for k, v in cfg.capabilities.items()}, gap_needs=cfg.gap_needs,
        target_team_coverage=cfg.bridge.target_team_coverage,
    )
