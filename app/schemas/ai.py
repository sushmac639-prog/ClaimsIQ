from pydantic import BaseModel, ConfigDict, Field


class SourceCitation(BaseModel):
    document_id: int
    filename: str
    page_number: int | None
    section_reference: str | None
    chunk_index: int
    similarity: float


class AIQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=10)
    policy_id: int | None = Field(default=None, ge=1)


class AIQueryResponse(BaseModel):
    answer: str
    model: str
    sources: list[SourceCitation]
    no_match: bool
    query_log_id: int


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    region: str | None
    policy_id: int | None
    status: str
    file_size_bytes: int
    failure_reason: str | None = None


class DocumentStatusUpdate(BaseModel):
    active: bool
