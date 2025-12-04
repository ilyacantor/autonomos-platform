"""
Connection Intent Schemas for AAM Auto-Onboarding

These schemas define the contract between AOD (AOS Discover) and AAM for
auto-onboarding connections in Safe Mode with 90% day-one coverage SLO.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class ConnectionEvidence(BaseModel):
    """Evidence of connection sanctioning from AOD"""
    status: str = Field(..., description="Sanctioning status (Sanctioned, Pending, Unsanctioned)")
    source: str = Field(..., description="Evidence source (IdP, CMDB, Procurement, CASB)")
    ts: str = Field(..., description="ISO8601 timestamp of evidence")


class ConnectionOwner(BaseModel):
    """Connection ownership metadata from AOD"""
    user: str = Field(..., description="Owner email or UPN")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    why: str = Field(..., description="Attribution reason (oauth_consenter, admin, usage, expense, idp_owner)")


class ConnectionIntent(BaseModel):
    """
    Connection intent payload from AOD requesting auto-onboarding
    
    This schema represents a discovered data source that AAM should
    attempt to onboard in Safe Mode.
    """
    source_type: str = Field(
        ...,
        description="Source type from allowlist (salesforce, gworkspace_drive, m365_sharepoint, etc.)"
    )
    resource_ids: List[str] = Field(
        ...,
        description="Resource identifiers (tenant_id, org_id, site, repo, bucket, db_uri)"
    )
    scopes_mode: str = Field(
        default="safe_readonly",
        description="Access scope mode (safe_readonly for auto-onboarding)"
    )
    credential_locator: str = Field(
        ...,
        description="Credential reference (vault:..., env:..., consent:..., sp:...)"
    )
    namespace: str = Field(
        default="autonomy",
        description="Namespace for connection isolation (autonomy or demo)"
    )
    risk_level: str = Field(
        ...,
        description="Risk assessment (low, med, high)"
    )
    evidence: ConnectionEvidence = Field(
        ...,
        description="Sanctioning evidence from discovery"
    )
    owner: ConnectionOwner = Field(
        ...,
        description="Ownership metadata from discovery"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "salesforce",
                "resource_ids": ["org_00D123456789ABC"],
                "scopes_mode": "safe_readonly",
                "credential_locator": "vault:salesforce-prod-token",
                "namespace": "autonomy",
                "risk_level": "low",
                "evidence": {
                    "status": "Sanctioned",
                    "source": "IdP",
                    "ts": "2025-11-08T18:00:00Z"
                },
                "owner": {
                    "user": "admin@company.com",
                    "confidence": 0.95,
                    "why": "oauth_consenter"
                }
            }
        }


class OnboardingResult(BaseModel):
    """
    Result of connection auto-onboarding attempt
    
    Returned from POST /connections/onboard to indicate success/failure
    and provide details about the onboarding outcome.
    """
    connection_id: Optional[UUID] = Field(None, description="UUID of created/updated connection")
    status: str = Field(..., description="Connection status (ACTIVE, PENDING, FAILED, HEALING)")
    namespace: str = Field(..., description="Connection namespace (autonomy or demo)")
    first_sync_rows: Optional[int] = Field(None, description="Row count from tiny first sync (≤20)")
    latency_ms: Optional[float] = Field(None, description="Response time for first sync")
    funnel_stage: str = Field(
        ...,
        description="Funnel stage (eligible, reachable, active, awaiting_credentials, network_blocked, unsupported_type, error)"
    )
    message: str = Field(..., description="Human-readable outcome message")
    error: Optional[str] = Field(None, description="Error details if onboarding failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "ACTIVE",
                "namespace": "autonomy",
                "first_sync_rows": 15,
                "latency_ms": 250.5,
                "funnel_stage": "active",
                "message": "Onboarded successfully in Safe Mode with 15 records synced",
                "error": None
            }
        }


class FunnelMetrics(BaseModel):
    """
    Auto-onboarding funnel metrics for SLO tracking
    
    Tracks progression through the onboarding funnel:
    eligible → reachable → active
    
    SLO: coverage = active / eligible ≥ 0.90
    """
    namespace: str = Field(..., description="Namespace filter (autonomy or demo)")
    eligible: int = Field(0, description="Mappable + sanctioned + credentialed intents received")
    reachable: int = Field(0, description="Passed health check")
    active: int = Field(0, description="Tiny first sync succeeded (ACTIVE state)")
    awaiting_credentials: int = Field(0, description="Missing credentials")
    network_blocked: int = Field(0, description="Health check failed (network/firewall)")
    unsupported_type: int = Field(0, description="Source type not in allowlist")
    healing: int = Field(0, description="In HEALING state (drift/permissions)")
    error: int = Field(0, description="Onboarding exception/error")
    coverage: float = Field(0.0, ge=0.0, le=1.0, description="SLO coverage = active / eligible")
    slo_met: bool = Field(False, description="Whether coverage ≥ 0.90")
    target: float = Field(0.90, description="SLO target coverage")
    
    class Config:
        json_schema_extra = {
            "example": {
                "namespace": "autonomy",
                "eligible": 100,
                "reachable": 95,
                "active": 92,
                "awaiting_credentials": 3,
                "network_blocked": 2,
                "unsupported_type": 1,
                "healing": 1,
                "error": 1,
                "coverage": 0.92,
                "slo_met": True,
                "target": 0.90
            }
        }


class OnboardBatchRequest(BaseModel):
    """Batch onboarding request for multiple connection intents"""
    intents: List[ConnectionIntent] = Field(..., description="List of connection intents to onboard")
    
    class Config:
        json_schema_extra = {
            "example": {
                "intents": [
                    {
                        "source_type": "salesforce",
                        "resource_ids": ["org_00D123456789ABC"],
                        "scopes_mode": "safe_readonly",
                        "credential_locator": "env:SALESFORCE_TOKEN",
                        "namespace": "autonomy",
                        "risk_level": "low",
                        "evidence": {
                            "status": "Sanctioned",
                            "source": "IdP",
                            "ts": "2025-11-08T18:00:00Z"
                        },
                        "owner": {
                            "user": "admin@company.com",
                            "confidence": 0.95,
                            "why": "oauth_consenter"
                        }
                    }
                ]
            }
        }


class OnboardBatchResult(BaseModel):
    """Result of batch onboarding operation"""
    total: int = Field(..., description="Total intents processed")
    succeeded: int = Field(..., description="Successfully onboarded")
    failed: int = Field(..., description="Failed to onboard")
    results: List[OnboardingResult] = Field(..., description="Individual onboarding results")
    funnel: FunnelMetrics = Field(..., description="Updated funnel metrics after batch")
