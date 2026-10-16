"""track prompt and completion token usage for AI queries"""
from alembic import op
import sqlalchemy as sa

revision = "0005_ai_token_usage"
down_revision = "0004_claim_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_query_logs", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("chat_query_logs", sa.Column("completion_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_query_logs", "completion_tokens")
    op.drop_column("chat_query_logs", "prompt_tokens")
