"""Initial schema: users, companies, evidence, evidence_history, flags, smes, score_runs.

Revision ID: 0001
Revises:
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'analyst', 'viewer')", name="ck_users_role"),
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("fictional", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("type", sa.String(30), nullable=False, server_default="business_partner"),
        sa.Column("roles_offered", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("cin", sa.String(30)),
        sa.Column("nse_code", sa.String(30)),
        sa.Column("bse_code", sa.String(30)),
        sa.Column("msme_category", sa.String(30)),
        sa.Column("hq_state", sa.String(60)),
        sa.Column("description", sa.Text),
        sa.Column("profile", JSONB, nullable=False, server_default="{}"),
        sa.Column("capabilities", JSONB, nullable=False, server_default="{}"),
        sa.Column("gates", JSONB, nullable=False, server_default="{}"),
        sa.Column("trends", JSONB, nullable=False, server_default="{}"),
        sa.CheckConstraint("type IN ('business_partner', 'service_provider')", name="ck_companies_type"),
    )
    op.create_table(
        "evidence",
        sa.Column("company_id", sa.String(100), sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("parameter_id", sa.String(4), primary_key=True),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("source_url", sa.Text),
        sa.Column("source_date", sa.Date),
        sa.Column("checked_at", sa.Date),
        sa.Column("note", sa.Text),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("level IN (0, 25, 50, 75, 100)", name="ck_evidence_level"),
        sa.CheckConstraint("NOT verified OR (source_url IS NOT NULL AND source_date IS NOT NULL)",
                           name="ck_evidence_verified_has_source"),
    )
    op.create_table(
        "evidence_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("company_id", sa.String(100), sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("parameter_id", sa.String(4), nullable=False),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("verified", sa.Boolean, nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("source_date", sa.Date),
        sa.Column("checked_at", sa.Date),
        sa.Column("note", sa.Text),
        sa.Column("changed_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "flags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("company_id", sa.String(100), sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("note", sa.Text),
        sa.Column("source_url", sa.Text),
        sa.CheckConstraint("type IN ('knockout', 'cap', 'notch', 'fake_reviews')", name="ck_flags_type"),
    )
    op.create_table(
        "smes",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("fictional", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("country", sa.String(60)),
        sa.Column("city", sa.String(100)),
        sa.Column("employees", sa.Integer),
        sa.Column("description", sa.Text),
        sa.Column("sector", sa.String(60), nullable=False),
        sa.Column("products", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("role_sought", sa.String(30), nullable=False),
        sa.Column("target_states", JSONB, nullable=False, server_default="{}"),
        sa.Column("channels_needed", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("volume_units_per_month", sa.Integer),
        sa.Column("after_sales_need", sa.String(30)),
        sa.Column("competitors", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("factor_importance", JSONB, nullable=False, server_default="{}"),
        sa.Column("readiness_answers", JSONB, nullable=False, server_default="{}"),
    )
    op.create_table(
        "score_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("company_id", sa.String(100), sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  index=True),
        sa.Column("sme_id", sa.String(100), sa.ForeignKey("smes.id", ondelete="CASCADE"), index=True),
        sa.Column("role", sa.String(30)),
        sa.Column("config_version", sa.String(20), nullable=False),
        sa.Column("as_of", sa.Date, nullable=False),
        sa.Column("inputs_hash", sa.String(64), nullable=False),
        sa.Column("is_what_if", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("result", JSONB, nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('trust', 'fit', 'bridge')", name="ck_score_runs_kind"),
    )


def downgrade() -> None:
    for table in ("score_runs", "smes", "flags", "evidence_history", "evidence", "companies", "users"):
        op.drop_table(table)
