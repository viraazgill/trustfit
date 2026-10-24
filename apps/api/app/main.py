from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import errors
from app.routers import admin, auth, companies, config, evidence, health, reports, smes, trust
from app.settings import settings

app = FastAPI(title="TrustFit API", version="0.1.0",
              description="TrustFit Score is not a credit rating or investment advice.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
errors.install(app)
for module in (health, auth, config, companies, evidence, trust, smes, reports, admin):
    app.include_router(module.router, prefix="/api/v1")
