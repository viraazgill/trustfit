"""SMEs get an owner: a viewer sees and edits only their own briefs (plus fictional demo SMEs).
score_runs.config_version widens to hold every config a run used ("trust:v1 fit:v1 gap_bridge:v1").

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("smes", sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.add_column("smes", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                                    server_default=sa.func.now()))
    op.create_index("ix_smes_owner_id", "smes", ["owner_id"])
    op.alter_column("score_runs", "config_version", type_=sa.String(100), existing_type=sa.String(20))


def downgrade() -> None:
    op.alter_column("score_runs", "config_version", type_=sa.String(20), existing_type=sa.String(100))
    op.drop_index("ix_smes_owner_id", table_name="smes")
    op.drop_column("smes", "created_at")
    op.drop_column("smes", "owner_id")
