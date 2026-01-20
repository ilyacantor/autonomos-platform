"""
Memory Governance API Endpoints

REST API for memory management:
- Document storage and search
- Right-to-Forget requests
- Consent management
- Data export
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel, Field

from app.agentic.memory.vector_store import (
    VectorStore,
    DocumentType,
    MemoryDocument,
    SearchResult,
    get_vector_store,
)
from app.agentic.memory.governance import (
    MemoryGovernance,
    RetentionPeriod,
    ForgetScope,
    ConsentType,
    ForgetRequest,
    ForgetResult,
    RetentionPolicy,
    UserConsent,
    get_memory_governance,
)

router = APIRouter(prefix="/memory", tags=["memory"])


# Request/Response Models

class DocumentCreateRequest(BaseModel):
    """Request to store a document."""
    content: str
    doc_type: str  # DocumentType value
    metadata: Optional[dict] = None
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class DocumentResponse(BaseModel):
    """Document response."""
    doc_id: str
    tenant_id: str
    content: str
    doc_type: str
    metadata: dict
    conversation_id: Optional[str]
    user_id: Optional[str]
    agent_id: Optional[str]
    created_at: str
    expires_at: Optional[str]


class SearchRequest(BaseModel):
    """Search request."""
    query: str
    limit: int = 10
    doc_types: Optional[List[str]] = None
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    min_score: Optional[float] = None


class SearchResultResponse(BaseModel):
    """Search result."""
    document: DocumentResponse
    score: float
    rank: int


class SearchResponse(BaseModel):
    """Search response."""
    results: List[SearchResultResponse]
    total: int
    query: str


class ForgetRequestCreate(BaseModel):
    """Request to forget user data."""
    scope: str = "all"  # ForgetScope value
    conversation_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    document_types: Optional[List[str]] = None
    agent_id: Optional[str] = None
    require_verification: bool = True


class ForgetRequestResponse(BaseModel):
    """Forget request response."""
    request_id: str
    tenant_id: str
    user_id: str
    scope: str
    conversation_id: Optional[str]
    status: str
    verified: bool
    requested_at: str
    processed_at: Optional[str]


class ForgetVerifyRequest(BaseModel):
    """Request to verify a forget request."""
    verification_code: str


class ForgetResultResponse(BaseModel):
    """Forget result response."""
    request_id: str
    success: bool
    documents_deleted: int
    documents_anonymized: int
    errors: List[str]
    processing_time_ms: float


class ConsentUpdateRequest(BaseModel):
    """Request to update user consent."""
    memory_storage: Optional[bool] = None
    learning: Optional[bool] = None
    analytics: Optional[bool] = None
    personalization: Optional[bool] = None
    third_party: Optional[bool] = None


class ConsentResponse(BaseModel):
    """Consent response."""
    consent_id: str
    user_id: str
    consents: dict
    granted_at: str
    updated_at: str


class RetentionPolicyCreate(BaseModel):
    """Request to create a retention policy."""
    name: str
    default_retention: str = "1_month"
    retention_by_type: Optional[dict] = None
    auto_cleanup_enabled: bool = True


class RetentionPolicyResponse(BaseModel):
    """Retention policy response."""
    policy_id: str
    tenant_id: str
    name: str
    default_retention: str
    retention_by_type: dict
    auto_cleanup_enabled: bool
    created_at: str


class StatsResponse(BaseModel):
    """Memory stats response."""
    total_documents: int
    by_type: dict
    total_conversations: int
    total_users: int


class DataExportResponse(BaseModel):
    """Data export response."""
    export_date: str
    user_id: str
    tenant_id: str
    document_count: int
    documents: List[dict]
    consent: Optional[dict]
    forget_requests: List[dict]


# Helper functions

def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant ID from header."""
    if x_tenant_id:
        return x_tenant_id
    return "00000000-0000-0000-0000-000000000001"


def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header."""
    if x_user_id:
        return x_user_id
    return "00000000-0000-0000-0000-000000000002"


def doc_to_response(doc: MemoryDocument) -> DocumentResponse:
    """Convert document to response."""
    return DocumentResponse(
        doc_id=doc.doc_id,
        tenant_id=doc.tenant_id,
        content=doc.content,
        doc_type=doc.doc_type.value,
        metadata=doc.metadata,
        conversation_id=doc.conversation_id,
        user_id=doc.user_id,
        agent_id=doc.agent_id,
        created_at=doc.created_at.isoformat(),
        expires_at=doc.expires_at.isoformat() if doc.expires_at else None,
    )


# Document endpoints

@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def store_document(
    data: DocumentCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    """Store a document in the vector store."""
    store = get_vector_store()

    try:
        doc_type = DocumentType(data.doc_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {data.doc_type}")

    doc = await store.add_document(
        content=data.content,
        tenant_id=tenant_id,
        doc_type=doc_type,
        metadata=data.metadata,
        conversation_id=data.conversation_id,
        user_id=user_id,
        agent_id=data.agent_id,
        expires_at=data.expires_at,
    )

    return doc_to_response(doc)


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    data: SearchRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    """Search for documents."""
    store = get_vector_store()

    doc_types = None
    if data.doc_types:
        try:
            doc_types = [DocumentType(dt) for dt in data.doc_types]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid doc_type: {e}")

    results = await store.search(
        query=data.query,
        tenant_id=tenant_id,
        limit=data.limit,
        doc_types=doc_types,
        conversation_id=data.conversation_id,
        agent_id=data.agent_id,
        min_score=data.min_score,
    )

    return SearchResponse(
        results=[
            SearchResultResponse(
                document=doc_to_response(r.document),
                score=r.score,
                rank=r.rank,
            )
            for r in results
        ],
        total=len(results),
        query=data.query,
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific document."""
    store = get_vector_store()

    doc = await store.get_document(doc_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc_to_response(doc)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a document."""
    store = get_vector_store()

    success = await store.delete_document(doc_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/conversations/{conversation_id}/history", response_model=List[DocumentResponse])
async def get_conversation_history(
    conversation_id: str,
    limit: int = Query(default=100, le=500),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get conversation history."""
    store = get_vector_store()

    docs = await store.get_conversation_history(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        limit=limit,
    )

    return [doc_to_response(doc) for doc in docs]


@router.get("/stats", response_model=StatsResponse)
async def get_memory_stats(
    tenant_id: str = Depends(get_tenant_id),
):
    """Get memory statistics."""
    store = get_vector_store()
    stats = await store.get_stats(tenant_id)
    return StatsResponse(**stats)


# Forget endpoints

@router.post("/forget", response_model=ForgetRequestResponse, status_code=201)
async def create_forget_request(
    data: ForgetRequestCreate,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    """
    Request to forget user data (GDPR Right to Erasure).

    Creates a forget request that must be verified before processing.
    """
    governance = get_memory_governance()

    try:
        scope = ForgetScope(data.scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {data.scope}")

    doc_types = None
    if data.document_types:
        try:
            doc_types = [DocumentType(dt) for dt in data.document_types]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid doc_type: {e}")

    request = await governance.request_forget(
        tenant_id=tenant_id,
        user_id=user_id,
        scope=scope,
        conversation_id=data.conversation_id,
        date_from=data.date_from,
        date_to=data.date_to,
        document_types=doc_types,
        agent_id=data.agent_id,
        require_verification=data.require_verification,
    )

    return ForgetRequestResponse(
        request_id=request.request_id,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        scope=request.scope.value,
        conversation_id=request.conversation_id,
        status=request.status,
        verified=request.verified,
        requested_at=request.requested_at.isoformat(),
        processed_at=request.processed_at.isoformat() if request.processed_at else None,
    )


@router.post("/forget/{request_id}/verify", response_model=ForgetRequestResponse)
async def verify_forget_request(
    request_id: str,
    data: ForgetVerifyRequest,
):
    """Verify a forget request with the verification code."""
    governance = get_memory_governance()

    success = await governance.verify_forget_request(request_id, data.verification_code)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    request = await governance.get_forget_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return ForgetRequestResponse(
        request_id=request.request_id,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        scope=request.scope.value,
        conversation_id=request.conversation_id,
        status=request.status,
        verified=request.verified,
        requested_at=request.requested_at.isoformat(),
        processed_at=request.processed_at.isoformat() if request.processed_at else None,
    )


@router.post("/forget/{request_id}/process", response_model=ForgetResultResponse)
async def process_forget_request(
    request_id: str,
):
    """Process a verified forget request to delete the data."""
    governance = get_memory_governance()

    request = await governance.get_forget_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if not request.verified:
        raise HTTPException(status_code=400, detail="Request not verified")

    result = await governance.process_forget_request(request_id)

    return ForgetResultResponse(
        request_id=result.request_id,
        success=result.success,
        documents_deleted=result.documents_deleted,
        documents_anonymized=result.documents_anonymized,
        errors=result.errors,
        processing_time_ms=result.processing_time_ms,
    )


@router.get("/forget", response_model=List[ForgetRequestResponse])
async def list_forget_requests(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    """List forget requests for the user."""
    governance = get_memory_governance()

    requests = await governance.list_forget_requests(
        tenant_id=tenant_id,
        user_id=user_id,
        status=status,
    )

    return [
        ForgetRequestResponse(
            request_id=r.request_id,
            tenant_id=r.tenant_id,
            user_id=r.user_id,
            scope=r.scope.value,
            conversation_id=r.conversation_id,
            status=r.status,
            verified=r.verified,
            requested_at=r.requested_at.isoformat(),
            processed_at=r.processed_at.isoformat() if r.processed_at else None,
        )
        for r in requests
    ]


# Consent endpoints

@router.put("/consent", response_model=ConsentResponse)
async def update_consent(
    data: ConsentUpdateRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    """Update user consent preferences."""
    governance = get_memory_governance()

    consents = {}
    if data.memory_storage is not None:
        consents[ConsentType.MEMORY_STORAGE] = data.memory_storage
    if data.learning is not None:
        consents[ConsentType.LEARNING] = data.learning
    if data.analytics is not None:
        consents[ConsentType.ANALYTICS] = data.analytics
    if data.personalization is not None:
        consents[ConsentType.PERSONALIZATION] = data.personalization
    if data.third_party is not None:
        consents[ConsentType.THIRD_PARTY] = data.third_party

    consent = await governance.set_user_consent(
        tenant_id=tenant_id,
        user_id=user_id,
        consents=consents,
    )

    return ConsentResponse(
        consent_id=consent.consent_id,
        user_id=consent.user_id,
        consents={k.value: v for k, v in consent.consents.items()},
        granted_at=consent.granted_at.isoformat(),
        updated_at=consent.updated_at.isoformat(),
    )


@router.get("/consent", response_model=Optional[ConsentResponse])
async def get_consent(
    user_id: str = Depends(get_user_id),
):
    """Get user consent preferences."""
    governance = get_memory_governance()

    consent = await governance.get_user_consent(user_id)
    if not consent:
        return None

    return ConsentResponse(
        consent_id=consent.consent_id,
        user_id=consent.user_id,
        consents={k.value: v for k, v in consent.consents.items()},
        granted_at=consent.granted_at.isoformat(),
        updated_at=consent.updated_at.isoformat(),
    )


# Data export endpoint

@router.get("/export", response_model=DataExportResponse)
async def export_user_data(
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    """
    Export all user data (GDPR Data Portability).

    Returns all data associated with the user in a portable format.
    """
    governance = get_memory_governance()

    export = await governance.export_user_data(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    return DataExportResponse(**export)


# Retention policy endpoints

@router.post("/policies", response_model=RetentionPolicyResponse, status_code=201)
async def create_retention_policy(
    data: RetentionPolicyCreate,
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a retention policy."""
    governance = get_memory_governance()

    try:
        default_retention = RetentionPeriod(data.default_retention)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid retention period: {data.default_retention}"
        )

    retention_by_type = {}
    if data.retention_by_type:
        for doc_type_str, period_str in data.retention_by_type.items():
            try:
                doc_type = DocumentType(doc_type_str)
                period = RetentionPeriod(period_str)
                retention_by_type[doc_type] = period
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

    policy = await governance.create_retention_policy(
        tenant_id=tenant_id,
        name=data.name,
        default_retention=default_retention,
        retention_by_type=retention_by_type,
        auto_cleanup_enabled=data.auto_cleanup_enabled,
    )

    return RetentionPolicyResponse(
        policy_id=policy.policy_id,
        tenant_id=policy.tenant_id,
        name=policy.name,
        default_retention=policy.default_retention.value,
        retention_by_type={k.value: v.value for k, v in policy.retention_by_type.items()},
        auto_cleanup_enabled=policy.auto_cleanup_enabled,
        created_at=policy.created_at.isoformat(),
    )


@router.get("/policies", response_model=List[RetentionPolicyResponse])
async def list_retention_policies(
    tenant_id: str = Depends(get_tenant_id),
):
    """List retention policies."""
    governance = get_memory_governance()

    policies = await governance.list_retention_policies(tenant_id)

    return [
        RetentionPolicyResponse(
            policy_id=p.policy_id,
            tenant_id=p.tenant_id,
            name=p.name,
            default_retention=p.default_retention.value,
            retention_by_type={k.value: v.value for k, v in p.retention_by_type.items()},
            auto_cleanup_enabled=p.auto_cleanup_enabled,
            created_at=p.created_at.isoformat(),
        )
        for p in policies
    ]


# Cleanup endpoint

@router.post("/cleanup", response_model=dict)
async def run_cleanup(
    tenant_id: str = Depends(get_tenant_id),
):
    """Run retention cleanup to remove expired documents."""
    governance = get_memory_governance()

    deleted = await governance.run_retention_cleanup(tenant_id)

    return {
        "deleted_documents": deleted,
        "message": f"Cleaned up {deleted} expired documents",
    }
