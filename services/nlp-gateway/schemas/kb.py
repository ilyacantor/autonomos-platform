from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from .common import Environment, BaseResponse


class DocumentMatch(BaseModel):
    doc_id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Document title")
    section: str = Field(..., description="Section within document")
    score: float = Field(..., description="Relevance score")
    snippet: str = Field(..., description="Text snippet")
    citation: str = Field(..., description="Citation format (Doc:Section)")


class KBSearchRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    env: Environment = Field(Environment.PROD, description="Environment")
    query: str = Field(..., description="Natural language query")
    top_k: int = Field(5, description="Number of results to return")


class KBSearchResponse(BaseResponse):
    matches: List[DocumentMatch] = Field(default_factory=list, description="Matching documents")


class IngestItemType(str, Enum):
    FILE = "file"
    URL = "url"
    TEXT = "text"


class IngestItem(BaseModel):
    type: IngestItemType = Field(..., description="Item type")
    location: str = Field(..., description="File path, URL, or text content")
    tags: List[str] = Field(default_factory=list, description="Optional tags")


class IngestPolicy(BaseModel):
    chunk: str = Field("auto", description="Chunking strategy (auto|fixed)")
    max_chunk_tokens: int = Field(1200, description="Maximum tokens per chunk")
    redact_pii: bool = Field(True, description="Enable PII redaction")


class IngestedDocument(BaseModel):
    doc_id: str = Field(..., description="Document identifier")
    chunks: int = Field(..., description="Number of chunks created")
    tags: List[str] = Field(default_factory=list, description="Document tags")


class KBIngestRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    env: Environment = Field(Environment.PROD, description="Environment")
    items: List[IngestItem] = Field(..., description="Items to ingest")
    policy: IngestPolicy = Field(default_factory=IngestPolicy, description="Ingestion policy")


class KBIngestResponse(BaseResponse):
    ingested: List[IngestedDocument] = Field(default_factory=list, description="Ingested documents")
