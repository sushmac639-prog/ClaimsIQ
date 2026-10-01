"""initial auth and crud schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL enum definitions.
    #
    # IMPORTANT:
    # Do NOT call .create() manually here.
    # op.create_table() will create the enum types automatically.

    user_role = sa.Enum(
        "admin",
        "claims_manager",
        "claims_adjuster",
        "support_agent",
        name="user_role",
    )

    policy_status = sa.Enum(
        "active",
        "inactive",
        "expired",
        name="policy_status",
    )

    claim_status = sa.Enum(
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "closed",
        name="claim_status",
    )

    history_old_status = sa.Enum(
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "closed",
        name="history_old_status",
    )

    history_new_status = sa.Enum(
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "closed",
        name="history_new_status",
    )

    # ------------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------------

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email"),
    )

    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # POLICIES
    # ------------------------------------------------------------------

    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_number", sa.String(80), nullable=False),
        sa.Column("policy_type", sa.String(80), nullable=False),
        sa.Column("coverage_description", sa.Text(), nullable=True),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("status", policy_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("policy_number"),
    )

    op.create_index(
        "ix_policies_policy_number",
        "policies",
        ["policy_number"],
        unique=False,
    )

    op.create_index(
        "ix_policies_region",
        "policies",
        ["region"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # CLAIMS
    # ------------------------------------------------------------------

    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_number", sa.String(80), nullable=False),
        sa.Column(
            "policy_id",
            sa.Integer(),
            sa.ForeignKey("policies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assigned_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("claimant_name", sa.String(150), nullable=False),
        sa.Column("claim_type", sa.String(80), nullable=False),
        sa.Column("claim_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("status", claim_status, nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("claim_number"),
    )

    op.create_index(
        "ix_claims_claim_number",
        "claims",
        ["claim_number"],
        unique=False,
    )

    op.create_index(
        "ix_claims_assigned_user_id",
        "claims",
        ["assigned_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_claims_claim_type",
        "claims",
        ["claim_type"],
        unique=False,
    )

    op.create_index(
        "ix_claims_region",
        "claims",
        ["region"],
        unique=False,
    )

    op.create_index(
        "ix_claims_status_region",
        "claims",
        ["status", "region"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # CLAIM NOTES
    # ------------------------------------------------------------------

    op.create_table(
        "claim_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "claim_id",
            sa.Integer(),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------
    # CLAIM STATUS HISTORY
    # ------------------------------------------------------------------

    op.create_table(
        "claim_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "claim_id",
            sa.Integer(),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "old_status",
            history_old_status,
            nullable=True,
        ),
        sa.Column(
            "new_status",
            history_new_status,
            nullable=False,
        ),
        sa.Column(
            "changed_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "justification",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------
    # AUDIT LOGS
    # ------------------------------------------------------------------

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables first because of foreign-key dependencies.
    op.drop_index(
        "ix_audit_logs_action",
        table_name="audit_logs",
    )
    op.drop_table("audit_logs")

    op.drop_table("claim_status_history")

    op.drop_table("claim_notes")

    op.drop_index(
        "ix_claims_status_region",
        table_name="claims",
    )
    op.drop_index(
        "ix_claims_region",
        table_name="claims",
    )
    op.drop_index(
        "ix_claims_claim_type",
        table_name="claims",
    )
    op.drop_index(
        "ix_claims_assigned_user_id",
        table_name="claims",
    )
    op.drop_index(
        "ix_claims_claim_number",
        table_name="claims",
    )
    op.drop_table("claims")

    op.drop_index(
        "ix_policies_region",
        table_name="policies",
    )
    op.drop_index(
        "ix_policies_policy_number",
        table_name="policies",
    )
    op.drop_table("policies")

    op.drop_index(
        "ix_users_email",
        table_name="users",
    )
    op.drop_table("users")

    # Drop PostgreSQL enum types after the tables using them are gone.
    bind = op.get_bind()

    sa.Enum(
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "closed",
        name="history_new_status",
    ).drop(bind, checkfirst=True)

    sa.Enum(
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "closed",
        name="history_old_status",
    ).drop(bind, checkfirst=True)

    sa.Enum(
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "closed",
        name="claim_status",
    ).drop(bind, checkfirst=True)

    sa.Enum(
        "active",
        "inactive",
        "expired",
        name="policy_status",
    ).drop(bind, checkfirst=True)

    sa.Enum(
        "admin",
        "claims_manager",
        "claims_adjuster",
        "support_agent",
        name="user_role",
    ).drop(bind, checkfirst=True)