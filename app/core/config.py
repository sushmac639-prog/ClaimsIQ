from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClaimIQ"
    app_env: str = "development"
    debug: bool = False
    database_url: str
    db_echo: bool = False
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # AI / RAG
    # Provider can be "azure_foundry" (recommended for the capstone) or "openai".
    ai_provider: str = "azure_foundry"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-5.6-luna"
    openai_embedding_model: str = "text-embedding-3-small"
    # Microsoft Foundry / Azure OpenAI OpenAI-v1 compatible endpoint.
    # Example Foundry resource endpoint: https://<resource>.services.ai.azure.com/openai/v1/
    azure_openai_api_key: str = ""
    azure_openai_base_url: str = "https://hr-ai-portal.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview"
    azure_openai_chat_model: str = "hr-app-gpt-5.5"
    azure_openai_embedding_model: str = "hr-embedding"
    llm_timeout_seconds: float = 60.0
    rag_top_k: int = 5
    rag_min_similarity: float = 0.55
    rag_max_context_chars: int = 12000
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 200
    rag_embed_batch_size: int = 32
    chroma_persist_directory: Path = Path("./data/chroma")
    chroma_collection: str = "claimiq_policy_chunks"
    document_storage_directory: Path = Path("./data/documents")
    max_document_size_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
