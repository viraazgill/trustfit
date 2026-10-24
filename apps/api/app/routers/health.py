from fastapi import APIRouter

import trustfit_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": trustfit_engine.__version__}
