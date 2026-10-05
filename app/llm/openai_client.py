from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings


class OpenAIUnavailableError(RuntimeError):
    pass


class OpenAIClient:
    """LangChain wrapper supporting Microsoft Foundry/Azure OpenAI or direct OpenAI.

    For the capstone, Microsoft Foundry is the recommended provider. Foundry's
    OpenAI-v1 compatible endpoint keeps the application code simple while still
    using Azure-managed model deployments.
    """

    def __init__(self) -> None:
        provider = settings.ai_provider.strip().lower()
        if provider == "azure_foundry":
            api_key = settings.azure_openai_api_key
            base_url = settings.azure_openai_base_url.rstrip("/")
            chat_model = settings.azure_openai_chat_model
            embedding_model = settings.azure_openai_embedding_model
            if not api_key or not base_url:
                raise OpenAIUnavailableError(
                    "AZURE_OPENAI_API_KEY and AZURE_OPENAI_BASE_URL are required when AI_PROVIDER=azure_foundry"
                )
            common = {"api_key": api_key, "base_url": base_url}
        elif provider == "openai":
            api_key = settings.openai_api_key
            chat_model = settings.openai_chat_model
            embedding_model = settings.openai_embedding_model
            if not api_key:
                raise OpenAIUnavailableError("OPENAI_API_KEY is not configured")
            common = {"api_key": api_key}
        else:
            raise OpenAIUnavailableError(f"Unsupported AI_PROVIDER: {settings.ai_provider}")

        self.provider = provider
        self.chat_model = chat_model
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            chunk_size=settings.rag_embed_batch_size,
            max_retries=2,
            **common,
        )
        self.chat = ChatOpenAI(
            model=chat_model,
            temperature=0.1,
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
            use_responses_api=True,
            **common,
        )


_client: OpenAIClient | None = None


def get_openai_client() -> OpenAIClient:
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client
