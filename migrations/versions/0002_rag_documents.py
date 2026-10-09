"""add policy documents, vector chunks, and AI query logs"""
from alembic import op
import sqlalchemy as sa

revision = "0002_rag_documents"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:    
    document_status = sa.Enum(
        "processing", "active", "inactive", "failed", name="document_status", create_type=False,
    )
    bind = op.get_bind()
    document_status.create(bind, checkfirst=True)
    
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(100)),
        sa.Column("policy_id", sa.Integer(), nullable=True),
        sa.Column("status", document_status, nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("checksum_sha256"),
    )
    op.create_index("ix_documents_region", "documents", ["region"], unique=False)
    op.create_index("ix_documents_policy_id", "documents", ["policy_id"], unique=False)

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("section_reference", sa.String(255)),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("vector_id", sa.String(255), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),
        sa.UniqueConstraint("vector_id"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"], unique=False)

    op.create_table(
        "chat_query_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text()),
        sa.Column("model_name", sa.String(150), nullable=False),
        sa.Column("source_references", sa.Text()),
        sa.Column("retrieved_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("no_match", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_chat_query_logs_user_id", "chat_query_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chat_query_logs_user_id", table_name="chat_query_logs")
    op.drop_table("chat_query_logs")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_policy_id", table_name="documents")
    op.drop_index("ix_documents_region", table_name="documents")
    op.drop_table("documents")
    sa.Enum(name="document_status").drop(op.get_bind(), checkfirst=True)
