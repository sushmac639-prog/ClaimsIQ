"""add soft archival for claims and retain status history"""
from alembic import op
import sqlalchemy as sa

revision = "0004_claim_archive"
down_revision = "0003_revoked_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_claims_archived_at", "claims", ["archived_at"], unique=False)
    # Prevent a physical claim deletion from cascading into status history.
    with op.batch_alter_table("claim_status_history") as batch_op:
        batch_op.drop_constraint("claim_status_history_claim_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_claim_status_history_claim_id_claims",
            "claims", ["claim_id"], ["id"], ondelete="RESTRICT"
        )


def downgrade() -> None:
    with op.batch_alter_table("claim_status_history") as batch_op:
        batch_op.drop_constraint("fk_claim_status_history_claim_id_claims", type_="foreignkey")
        batch_op.create_foreign_key(
            "claim_status_history_claim_id_fkey", "claims", ["claim_id"], ["id"], ondelete="CASCADE"
        )
    op.drop_index("ix_claims_archived_at", table_name="claims")
    op.drop_column("claims", "archived_at")
