"""
Context Sharing Protocol with Shift-Left PII Detection

Implements the "Shift-Left" security pattern by detecting PII at the ingress
point of the A2A delegation module, before context is shared between agents.

The shift-left approach moves PII detection earlier in the data flow:
- Traditional: Detect PII at output/egress
- Shift-Left: Detect PII at input/ingress

Benefits:
- Prevents PII from propagating through the agent delegation chain
- Reduces exposure window for sensitive data
- Enables policy-based handling (BLOCK, REDACT, WARN, ALLOW)
- Provides telemetry for RACI compliance (Security owns PII detection)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..trust.pii import PIIDetector, PIIRedactor, PIIMatch, PIIType, get_pii_detector
from ..fabric.router import FabricContext, ActionRouter

logger = logging.getLogger(__name__)


class PIIPolicy(str, Enum):
    """Policy for handling detected PII in context."""
    BLOCK = "BLOCK"     # Reject the delegation if PII is found
    REDACT = "REDACT"   # Automatically redact PII and proceed
    WARN = "WARN"       # Log warning but allow (default)
    ALLOW = "ALLOW"     # Bypass PII scanning entirely


class RiskLevel(str, Enum):
    """Risk level based on PII detection results."""
    NONE = "none"           # No PII detected
    LOW = "low"             # Low-sensitivity PII (e.g., IP addresses)
    MEDIUM = "medium"       # Medium-sensitivity PII (e.g., email, phone)
    HIGH = "high"           # High-sensitivity PII (e.g., SSN, credit card)
    CRITICAL = "critical"   # Critical PII (e.g., passwords, API keys)


PII_TYPE_RISK_LEVELS: Dict[PIIType, RiskLevel] = {
    PIIType.EMAIL: RiskLevel.MEDIUM,
    PIIType.PHONE: RiskLevel.MEDIUM,
    PIIType.SSN: RiskLevel.HIGH,
    PIIType.CREDIT_CARD: RiskLevel.HIGH,
    PIIType.IP_ADDRESS: RiskLevel.LOW,
    PIIType.DATE_OF_BIRTH: RiskLevel.MEDIUM,
    PIIType.ADDRESS: RiskLevel.MEDIUM,
    PIIType.NAME: RiskLevel.LOW,
    PIIType.PASSPORT: RiskLevel.HIGH,
    PIIType.DRIVER_LICENSE: RiskLevel.HIGH,
    PIIType.BANK_ACCOUNT: RiskLevel.HIGH,
    PIIType.API_KEY: RiskLevel.CRITICAL,
    PIIType.PASSWORD: RiskLevel.CRITICAL,
}


@dataclass
class PIIScanResult:
    """
    Result of a PII scan on delegation context.
    
    Contains scan results including matches found, redaction applied,
    and the calculated risk level for RACI compliance reporting.
    """
    scan_id: str
    scanned_at: datetime = field(default_factory=datetime.utcnow)
    
    pii_detected: bool = False
    match_count: int = 0
    matches: List[Dict[str, Any]] = field(default_factory=list)
    
    pii_types_found: Set[str] = field(default_factory=set)
    risk_level: RiskLevel = RiskLevel.NONE
    
    redaction_applied: bool = False
    redacted_fields: List[str] = field(default_factory=list)
    
    policy_applied: PIIPolicy = PIIPolicy.WARN
    policy_action_taken: str = ""
    
    scan_duration_ms: int = 0
    error: Optional[str] = None
    
    primary_plane_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scan_id": self.scan_id,
            "scanned_at": self.scanned_at.isoformat(),
            "pii_detected": self.pii_detected,
            "match_count": self.match_count,
            "matches": self.matches,
            "pii_types_found": list(self.pii_types_found),
            "risk_level": self.risk_level.value,
            "redaction_applied": self.redaction_applied,
            "redacted_fields": self.redacted_fields,
            "policy_applied": self.policy_applied.value,
            "policy_action_taken": self.policy_action_taken,
            "scan_duration_ms": self.scan_duration_ms,
            "error": self.error,
            "primary_plane_id": self.primary_plane_id,
            "tenant_id": self.tenant_id,
        }


@dataclass
class SafeContext:
    """
    A validated context that has been scanned for PII.
    
    The SafeContext wraps a DelegationContext and provides guarantees
    about PII handling based on the applied policy:
    - BLOCK policy: SafeContext only created if no PII found
    - REDACT policy: SafeContext contains redacted context
    - WARN/ALLOW policy: SafeContext may contain PII but scan was performed
    """
    original_input: str
    original_context: Dict[str, Any] = field(default_factory=dict)
    delegation_reason: Optional[str] = None
    delegated_capability: Optional[str] = None
    max_steps: Optional[int] = None
    max_cost_usd: Optional[float] = None
    timeout_seconds: int = 300
    delegation_chain: List[str] = field(default_factory=list)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    
    scan_result: Optional[PIIScanResult] = None
    is_validated: bool = False
    validated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_input": self.original_input,
            "original_context": self.original_context,
            "delegation_reason": self.delegation_reason,
            "delegated_capability": self.delegated_capability,
            "max_steps": self.max_steps,
            "max_cost_usd": self.max_cost_usd,
            "timeout_seconds": self.timeout_seconds,
            "delegation_chain": self.delegation_chain,
            "shared_state": self.shared_state,
            "is_validated": self.is_validated,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "scan_result": self.scan_result.to_dict() if self.scan_result else None,
        }


class PIIBlockedException(Exception):
    """Raised when PII is detected and policy is BLOCK."""
    
    def __init__(self, scan_result: PIIScanResult, message: Optional[str] = None):
        self.scan_result = scan_result
        self.message = message or f"PII detected ({scan_result.match_count} matches), policy is BLOCK"
        super().__init__(self.message)


class ContextSharingProtocol:
    """
    Protocol for securely sharing context between agents with PII detection.
    
    Implements the shift-left security pattern by scanning all DelegationContext
    objects at ingress, before they are shared with delegatee agents.
    
    Features:
    - Automatic PII detection on context ingress
    - Configurable policies: BLOCK, REDACT, WARN, ALLOW
    - Metrics/telemetry emission for RACI compliance
    - Integration with FabricContext for Primary_Plane_ID tracking
    
    Example usage:
        protocol = ContextSharingProtocol(policy=PIIPolicy.REDACT)
        safe_context = await protocol.process_ingress(delegation_context)
    """
    
    def __init__(
        self,
        policy: PIIPolicy = PIIPolicy.WARN,
        detector: Optional[PIIDetector] = None,
        enabled_pii_types: Optional[Set[PIIType]] = None,
        tenant_id: str = "default",
    ):
        """
        Initialize the context sharing protocol.
        
        Args:
            policy: Default PII handling policy
            detector: Custom PII detector instance
            enabled_pii_types: Specific PII types to detect (None = all)
            tenant_id: Tenant ID for telemetry
        """
        self.default_policy = policy
        self.detector = detector or get_pii_detector()
        self.redactor = PIIRedactor(detector=self.detector)
        self.enabled_pii_types = enabled_pii_types
        self.tenant_id = tenant_id
        
        self._scan_count = 0
        self._pii_detection_count = 0
        self._block_count = 0
        self._redact_count = 0
        
        self._fabric_context: Optional[FabricContext] = None
    
    def set_fabric_context(self, context: FabricContext) -> None:
        """
        Set the fabric context for telemetry integration.
        
        The Primary_Plane_ID from FabricContext is included in all
        PII detection telemetry for traceability.
        """
        self._fabric_context = context
    
    def _get_fabric_context(self) -> Optional[FabricContext]:
        """Get the current fabric context, creating if needed."""
        if self._fabric_context is None:
            try:
                router = ActionRouter(self.tenant_id)
                self._fabric_context = router.get_fabric_context()
            except Exception as e:
                logger.warning(f"Could not get fabric context: {e}")
        return self._fabric_context
    
    def _calculate_risk_level(self, pii_types: Set[PIIType]) -> RiskLevel:
        """Calculate overall risk level from detected PII types."""
        if not pii_types:
            return RiskLevel.NONE
        
        risk_order = [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_risk = RiskLevel.NONE
        
        for pii_type in pii_types:
            type_risk = PII_TYPE_RISK_LEVELS.get(pii_type, RiskLevel.MEDIUM)
            if risk_order.index(type_risk) > risk_order.index(max_risk):
                max_risk = type_risk
        
        return max_risk
    
    def _serialize_context_for_scan(self, context: Any) -> str:
        """Serialize context fields to text for scanning."""
        if hasattr(context, 'to_dict'):
            data = context.to_dict()
        elif isinstance(context, dict):
            data = context
        else:
            data = {"value": str(context)}
        
        parts = []
        for key, value in data.items():
            if isinstance(value, str):
                parts.append(f"{key}: {value}")
            elif isinstance(value, dict):
                parts.append(f"{key}: {json.dumps(value)}")
            elif isinstance(value, list):
                parts.append(f"{key}: {json.dumps(value)}")
            else:
                parts.append(f"{key}: {str(value)}")
        
        return "\n".join(parts)
    
    def _emit_telemetry(self, scan_result: PIIScanResult) -> None:
        """
        Emit telemetry for PII detection.
        
        Per the RACI matrix, Security owns PII detection. This telemetry
        enables security monitoring and compliance reporting.
        """
        fabric_ctx = self._get_fabric_context()
        
        telemetry_event = {
            "event_type": "pii_detection",
            "timestamp": scan_result.scanned_at.isoformat(),
            "scan_id": scan_result.scan_id,
            "pii_detected": scan_result.pii_detected,
            "match_count": scan_result.match_count,
            "pii_types": list(scan_result.pii_types_found),
            "risk_level": scan_result.risk_level.value,
            "policy_applied": scan_result.policy_applied.value,
            "policy_action": scan_result.policy_action_taken,
            "redaction_applied": scan_result.redaction_applied,
            "tenant_id": self.tenant_id,
            "primary_plane_id": fabric_ctx.primary_plane_id if fabric_ctx else None,
            "fabric_preset": fabric_ctx.fabric_preset.value if fabric_ctx else None,
            "scan_duration_ms": scan_result.scan_duration_ms,
        }
        
        if scan_result.pii_detected:
            if scan_result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                logger.warning(f"PII Detection [HIGH RISK]: {json.dumps(telemetry_event)}")
            else:
                logger.info(f"PII Detection: {json.dumps(telemetry_event)}")
        else:
            logger.debug(f"PII Scan Clear: {json.dumps(telemetry_event)}")
    
    async def process_ingress(
        self,
        context: Any,
        policy: Optional[PIIPolicy] = None,
        scan_id: Optional[str] = None,
    ) -> SafeContext:
        """
        Process a context at ingress with PII detection.
        
        This is the main entry point for the shift-left pattern. All
        DelegationContext objects should pass through here before being
        shared with delegatee agents.
        
        Args:
            context: The DelegationContext or dict to process
            policy: Override policy for this scan (uses default if None)
            scan_id: Custom scan ID for tracking
        
        Returns:
            SafeContext with validated/redacted content
        
        Raises:
            PIIBlockedException: If PII detected and policy is BLOCK
        """
        from uuid import uuid4
        import time
        
        start_time = time.time()
        effective_policy = policy or self.default_policy
        scan_id = scan_id or str(uuid4())
        
        self._scan_count += 1
        
        fabric_ctx = self._get_fabric_context()
        
        scan_result = PIIScanResult(
            scan_id=scan_id,
            policy_applied=effective_policy,
            primary_plane_id=fabric_ctx.primary_plane_id if fabric_ctx else None,
            tenant_id=self.tenant_id,
        )
        
        if hasattr(context, 'to_dict'):
            context_dict = context.to_dict()
        elif isinstance(context, dict):
            context_dict = context.copy()
        else:
            context_dict = {"original_input": str(context)}
        
        if effective_policy == PIIPolicy.ALLOW:
            scan_result.policy_action_taken = "bypassed"
            scan_result.scan_duration_ms = int((time.time() - start_time) * 1000)
            
            safe_context = SafeContext(
                original_input=context_dict.get("original_input", ""),
                original_context=context_dict.get("original_context", {}),
                delegation_reason=context_dict.get("delegation_reason"),
                delegated_capability=context_dict.get("delegated_capability"),
                max_steps=context_dict.get("max_steps"),
                max_cost_usd=context_dict.get("max_cost_usd"),
                timeout_seconds=context_dict.get("timeout_seconds", 300),
                delegation_chain=context_dict.get("delegation_chain", []),
                shared_state=context_dict.get("shared_state", {}),
                scan_result=scan_result,
                is_validated=True,
                validated_at=datetime.utcnow(),
            )
            
            self._emit_telemetry(scan_result)
            return safe_context
        
        try:
            text_to_scan = self._serialize_context_for_scan(context_dict)
            matches = self.detector.detect(text_to_scan)
            
            scan_result.pii_detected = len(matches) > 0
            scan_result.match_count = len(matches)
            scan_result.matches = [m.to_dict() for m in matches]
            scan_result.pii_types_found = {m.pii_type.value for m in matches}
            scan_result.risk_level = self._calculate_risk_level({m.pii_type for m in matches})
            
            if scan_result.pii_detected:
                self._pii_detection_count += 1
            
        except Exception as e:
            scan_result.error = str(e)
            logger.error(f"PII scan error: {e}")
            scan_result.scan_duration_ms = int((time.time() - start_time) * 1000)
            self._emit_telemetry(scan_result)
            
            safe_context = SafeContext(
                original_input=context_dict.get("original_input", ""),
                original_context=context_dict.get("original_context", {}),
                delegation_reason=context_dict.get("delegation_reason"),
                delegated_capability=context_dict.get("delegated_capability"),
                max_steps=context_dict.get("max_steps"),
                max_cost_usd=context_dict.get("max_cost_usd"),
                timeout_seconds=context_dict.get("timeout_seconds", 300),
                delegation_chain=context_dict.get("delegation_chain", []),
                shared_state=context_dict.get("shared_state", {}),
                scan_result=scan_result,
                is_validated=False,
                validated_at=datetime.utcnow(),
            )
            return safe_context
        
        if effective_policy == PIIPolicy.BLOCK and scan_result.pii_detected:
            self._block_count += 1
            scan_result.policy_action_taken = "blocked"
            scan_result.scan_duration_ms = int((time.time() - start_time) * 1000)
            self._emit_telemetry(scan_result)
            raise PIIBlockedException(scan_result)
        
        if effective_policy == PIIPolicy.REDACT and scan_result.pii_detected:
            self._redact_count += 1
            scan_result.redaction_applied = True
            scan_result.policy_action_taken = "redacted"
            
            redacted_context = self._redact_context(context_dict, scan_result)
            context_dict = redacted_context
        
        elif effective_policy == PIIPolicy.WARN and scan_result.pii_detected:
            scan_result.policy_action_taken = "warned"
            logger.warning(
                f"PII detected in delegation context (scan_id={scan_id}): "
                f"{scan_result.match_count} matches, risk_level={scan_result.risk_level.value}"
            )
        
        else:
            scan_result.policy_action_taken = "allowed"
        
        scan_result.scan_duration_ms = int((time.time() - start_time) * 1000)
        
        safe_context = SafeContext(
            original_input=context_dict.get("original_input", ""),
            original_context=context_dict.get("original_context", {}),
            delegation_reason=context_dict.get("delegation_reason"),
            delegated_capability=context_dict.get("delegated_capability"),
            max_steps=context_dict.get("max_steps"),
            max_cost_usd=context_dict.get("max_cost_usd"),
            timeout_seconds=context_dict.get("timeout_seconds", 300),
            delegation_chain=context_dict.get("delegation_chain", []),
            shared_state=context_dict.get("shared_state", {}),
            scan_result=scan_result,
            is_validated=True,
            validated_at=datetime.utcnow(),
        )
        
        self._emit_telemetry(scan_result)
        
        return safe_context
    
    def _redact_context(
        self,
        context_dict: Dict[str, Any],
        scan_result: PIIScanResult,
    ) -> Dict[str, Any]:
        """Redact PII from context fields."""
        redacted = context_dict.copy()
        
        if "original_input" in redacted and isinstance(redacted["original_input"], str):
            redacted_text, _ = self.redactor.redact(redacted["original_input"])
            if redacted_text != redacted["original_input"]:
                redacted["original_input"] = redacted_text
                scan_result.redacted_fields.append("original_input")
        
        if "delegation_reason" in redacted and isinstance(redacted["delegation_reason"], str):
            redacted_text, _ = self.redactor.redact(redacted["delegation_reason"])
            if redacted_text != redacted["delegation_reason"]:
                redacted["delegation_reason"] = redacted_text
                scan_result.redacted_fields.append("delegation_reason")
        
        if "original_context" in redacted and isinstance(redacted["original_context"], dict):
            for key, value in redacted["original_context"].items():
                if isinstance(value, str):
                    redacted_text, matches = self.redactor.redact(value)
                    if matches:
                        redacted["original_context"][key] = redacted_text
                        scan_result.redacted_fields.append(f"original_context.{key}")
        
        if "shared_state" in redacted and isinstance(redacted["shared_state"], dict):
            for key, value in redacted["shared_state"].items():
                if isinstance(value, str):
                    redacted_text, matches = self.redactor.redact(value)
                    if matches:
                        redacted["shared_state"][key] = redacted_text
                        scan_result.redacted_fields.append(f"shared_state.{key}")
        
        return redacted
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get protocol statistics for monitoring."""
        return {
            "total_scans": self._scan_count,
            "pii_detections": self._pii_detection_count,
            "blocks": self._block_count,
            "redactions": self._redact_count,
            "detection_rate": (
                self._pii_detection_count / self._scan_count
                if self._scan_count > 0 else 0.0
            ),
            "default_policy": self.default_policy.value,
            "tenant_id": self.tenant_id,
        }


_context_sharing_protocol: Optional[ContextSharingProtocol] = None


def get_context_sharing_protocol(
    policy: PIIPolicy = PIIPolicy.WARN,
    tenant_id: str = "default",
) -> ContextSharingProtocol:
    """Get or create the global context sharing protocol instance."""
    global _context_sharing_protocol
    if _context_sharing_protocol is None:
        _context_sharing_protocol = ContextSharingProtocol(
            policy=policy,
            tenant_id=tenant_id,
        )
    return _context_sharing_protocol
