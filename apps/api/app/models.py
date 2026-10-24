"""SQLAlchemy models. The migration in db/migrations/versions mirrors these tables."""
from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

USER_ROLES = ("admin", "analyst", "viewer")
COMPANY_TYPES = ("business_partner", "service_provider")
FLAG_TYPES = ("knockout", "cap", "notch", "fake_reviews")
RUN_KINDS = ("trust", "fit", "bridge")
# Mirrors scale_levels in config/trust_v1.yaml; the database enforces it as a CHECK constraint.
EVIDENCE_LEVELS = (0, 25, 50, 75, 100)


def _in(column: str, values: tuple) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(_in("role", USER_ROLES), name="ck_users_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (CheckConstraint(_in("type", COMPANY_TYPES), name="ck_companies_type"),)

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # slug
    name: Mapped[str] = mapped_column(String(300))
    fictional: Mapped[bool] = mapped_column(Boolean, default=False)
    type: Mapped[str] = mapped_column(String(30), default="business_partner")
    roles_offered: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    cin: Mapped[str | None] = mapped_column(String(30))
    nse_code: Mapped[str | None] = mapped_column(String(30))
    bse_code: Mapped[str | None] = mapped_column(String(30))
    msme_category: Mapped[str | None] = mapped_column(String(30))
    hq_state: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    gates: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    trends: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    evidence: Mapped[list[Evidence]] = relationship(back_populates="company", cascade="all, delete-orphan")
    flags: Mapped[list[Flag]] = relationship(back_populates="company", cascade="all, delete-orphan",
                                             order_by="Flag.id")


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(_in("level", EVIDENCE_LEVELS), name="ck_evidence_level"),
        CheckConstraint("NOT verified OR (source_url IS NOT NULL AND source_date IS NOT NULL)",
                        name="ck_evidence_verified_has_source"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True)
    parameter_id: Mapped[str] = mapped_column(String(4), primary_key=True)
    level: Mapped[int] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_date: Mapped[dt.date | None] = mapped_column(Date)
    checked_at: Mapped[dt.date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                    onupdate=func.now())

    company: Mapped[Company] = relationship(back_populates="evidence")


class EvidenceHistory(Base):
    """Append-only: one row per evidence change."""
    __tablename__ = "evidence_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    parameter_id: Mapped[str] = mapped_column(String(4))
    level: Mapped[int] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_date: Mapped[dt.date | None] = mapped_column(Date)
    checked_at: Mapped[dt.date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (CheckConstraint(_in("type", FLAG_TYPES), name="ck_flags_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(String(60))
    note: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Company] = relationship(back_populates="flags")


class Sme(Base):
    __tablename__ = "smes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    fictional: Mapped[bool] = mapped_column(Boolean, default=False)
    country: Mapped[str | None] = mapped_column(String(60))
    city: Mapped[str | None] = mapped_column(String(100))
    employees: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(String(60))
    products: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    role_sought: Mapped[str] = mapped_column(String(30))
    target_states: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    channels_needed: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    volume_units_per_month: Mapped[int | None] = mapped_column(Integer)
    after_sales_need: Mapped[str | None] = mapped_column(String(30))
    competitors: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    factor_importance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    readiness_answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoreRun(Base):
    __tablename__ = "score_runs"
    __table_args__ = (CheckConstraint(_in("kind", RUN_KINDS), name="ck_score_runs_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    sme_id: Mapped[str | None] = mapped_column(ForeignKey("smes.id", ondelete="CASCADE"), index=True)
    role: Mapped[str | None] = mapped_column(String(30))
    config_version: Mapped[str] = mapped_column(String(100))
    as_of: Mapped[dt.date] = mapped_column(Date)
    inputs_hash: Mapped[str] = mapped_column(String(64))
    is_what_if: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
