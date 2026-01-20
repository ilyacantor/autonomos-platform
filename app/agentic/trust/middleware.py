"""
Trust Middleware

Unified security layer for agent execution with:
- Pre-execution validation
- Post-execution sanitization
- Configurable actions (block, warn, redact)
- Audit logging
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from app.agentic.trust.pii import PIIDetector, PIIRedactor, PIIMatch, PIIType
from app.agentic.trust.injection import InjectionDetector, InjectionMatch, InjectionType, RiskLevel

logger = logging.getLogger(__name__)


class TrustAction(str, Enum):
    """Actions to take when issues are detected."""
    ALLOW = "allow"       # Allow through (log only)
    WARN = "warn"         # Allow but add warning
    REDACT = "redact"     # Redact sensitive content and allow
    BLOCK = "block"       # Block execution entirely


@dataclass
class TrustConfig:
    """Configuration for the trust middleware."""

    # PII settings
    pii_detection_enabled: bool = True
    pii_action: TrustAction = TrustAction.REDACT
    pii_types_to_detect: Set[PIIType] = field(default_factory=lambda: set(PIIType))
    pii_types_to_block: Set[PIIType] = field(default_factory=lambda: {
        PIIType.SSN, PIIType.CREDIT_CARD, PIIType.PASSWORD, PIIType.API_KEY
    })

    # Injection settings
    injection_detection_enabled: bool = True
    injection_action: TrustAction = TrustAction.BLOCK
    injection_types_to_detect: Set[InjectionType] = field(default_factory=lambda: set(InjectionType))
    injection_risk_threshold: RiskLevel = RiskLevel.HIGH

    # Tool output scanning
    scan_tool_outputs: bool = True
    tool_output_pii_action: TrustAction = TrustAction.REDACT

    # Audit settings
    audit_enabled: bool = True
    log_blocked_content: bool = False  # Security: don't log actual blocked content

    # Rate limiting
    rate_limit_enabled: bool = True
    max_requests_per_minute: int = 60
    max_blocked_per_hour: int = 10  # Block user after too many blocked attempts


@dataclass
class TrustResult:
    """Result of trust middleware processing."""

    # Overall result
    allowed: bool
    action_taken: TrustAction

    # Content (possibly modified)
    original_content: str
    processed_content: str

    # Findings
    pii_matches: List[PIIMatch] = field(default_factory=list)
    injection_matches: List[InjectionMatch] = field(default_factory=list)

    # Metadata
    processing_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    block_reason: Optional[str] = None

    # Audit
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "action_taken": self.action_taken.value,
            "pii_found": len(self.pii_matches),
            "injection_found": len(self.injection_matches),
            "warnings": self.warnings,
            "block_reason": self.block_reason,
            "processing_time_ms": self.processing_time_ms,
            "audit_id": self.audit_id,
            "timestamp": self.timestamp.isoformat(),
        }


class TrustMiddleware:
    """
    Unified trust and safety middleware.

    Processes content before and after agent execution
    to ensure security and compliance.
    """

    def __init__(self, config: Optional[TrustConfig] = None):
        """
        Initialize the trust middleware.

        Args:
            config: Trust configuration
        """
        self.config = config or TrustConfig()

        # Initialize detectors
        self.pii_detector = PIIDetector(
            enabled_types=self.config.pii_types_to_detect
        )
        self.pii_redactor = PIIRedactor(detector=self.pii_detector)

        self.injection_detector = InjectionDetector(
            enabled_types=self.config.injection_types_to_detect
        )

        # Rate limiting state
        self._request_counts: Dict[str, List[datetime]] = {}
        self._blocked_counts: Dict[str, List[datetime]] = {}

        # Custom hooks
        self._pre_hooks: List[Callable] = []
        self._post_hooks: List[Callable] = []

        # Audit log
        self._audit_log: List[TrustResult] = []

    def add_pre_hook(self, hook: Callable[[str], Tuple[bool, str]]) -> None:
        """
        Add a pre-processing hook.

        Args:
            hook: Function(content) -> (allow, modified_content)
        """
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: Callable[[str], str]) -> None:
        """
        Add a post-processing hook.

        Args:
            hook: Function(content) -> modified_content
        """
        self._post_hooks.append(hook)

    async def process_input(
        self,
        content: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TrustResult:
        """
        Process user input before agent execution.

        Args:
            content: User input to process
            user_id: Optional user ID for rate limiting
            context: Additional context

        Returns:
            TrustResult with processed content and findings
        """
        start_time = datetime.utcnow()
        result = TrustResult(
            allowed=True,
            action_taken=TrustAction.ALLOW,
            original_content=content,
            processed_content=content,
        )

        try:
            # Rate limiting
            if self.config.rate_limit_enabled and user_id:
                rate_limit_result = self._check_rate_limit(user_id)
                if not rate_limit_result[0]:
                    result.allowed = False
                    result.action_taken = TrustAction.BLOCK
                    result.block_reason = rate_limit_result[1]
                    return result

            # Run custom pre-hooks
            for hook in self._pre_hooks:
                try:
                    allow, modified = hook(result.processed_content)
                    if not allow:
                        result.allowed = False
                        result.action_taken = TrustAction.BLOCK
                        result.block_reason = "Blocked by custom hook"
                        return result
                    result.processed_content = modified
                except Exception as e:
                    logger.warning(f"Pre-hook error: {e}")

            # Injection detection (check first - most critical)
            if self.config.injection_detection_enabled:
                result = self._process_injection(result)
                if not result.allowed:
                    self._record_blocked(user_id)
                    return result

            # PII detection
            if self.config.pii_detection_enabled:
                result = self._process_pii(result)
                if not result.allowed:
                    self._record_blocked(user_id)
                    return result

        finally:
            # Calculate processing time
            result.processing_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Audit logging
            if self.config.audit_enabled:
                self._log_audit(result)

        return result

    async def process_output(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TrustResult:
        """
        Process agent output before returning to user.

        Args:
            content: Agent output to process
            context: Additional context

        Returns:
            TrustResult with processed content
        """
        start_time = datetime.utcnow()
        result = TrustResult(
            allowed=True,
            action_taken=TrustAction.ALLOW,
            original_content=content,
            processed_content=content,
        )

        try:
            # PII detection in output
            if self.config.pii_detection_enabled:
                pii_matches = self.pii_detector.detect(content)
                result.pii_matches = pii_matches

                if pii_matches:
                    # Redact PII from output
                    redacted, _ = self.pii_redactor.redact(content)
                    result.processed_content = redacted
                    result.action_taken = TrustAction.REDACT
                    result.warnings.append(
                        f"Redacted {len(pii_matches)} PII instances from output"
                    )

            # Run custom post-hooks
            for hook in self._post_hooks:
                try:
                    result.processed_content = hook(result.processed_content)
                except Exception as e:
                    logger.warning(f"Post-hook error: {e}")

        finally:
            result.processing_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return result

    async def process_tool_output(
        self,
        tool_name: str,
        output: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TrustResult:
        """
        Process tool output for indirect injection and PII.

        Args:
            tool_name: Name of the tool
            output: Tool output to process
            context: Additional context

        Returns:
            TrustResult with processed content
        """
        if not self.config.scan_tool_outputs:
            return TrustResult(
                allowed=True,
                action_taken=TrustAction.ALLOW,
                original_content=output,
                processed_content=output,
            )

        result = TrustResult(
            allowed=True,
            action_taken=TrustAction.ALLOW,
            original_content=output,
            processed_content=output,
        )

        # Check for indirect injection in tool output
        if self.config.injection_detection_enabled:
            injection_matches = self.injection_detector.detect(output)
            # Filter to only indirect injection patterns
            indirect_matches = [
                m for m in injection_matches
                if m.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            ]

            if indirect_matches:
                result.injection_matches = indirect_matches
                result.warnings.append(
                    f"Potential indirect injection in {tool_name} output"
                )

                # For tool outputs, we warn but typically don't block
                # (let the agent decide what to do with potentially manipulated data)
                result.action_taken = TrustAction.WARN

        # Check for PII in tool output
        if self.config.pii_detection_enabled:
            pii_matches = self.pii_detector.detect(output)
            result.pii_matches = pii_matches

            if pii_matches and self.config.tool_output_pii_action == TrustAction.REDACT:
                redacted, _ = self.pii_redactor.redact(output)
                result.processed_content = redacted
                result.action_taken = TrustAction.REDACT

        return result

    def _process_injection(self, result: TrustResult) -> TrustResult:
        """Process content for injection attacks."""
        injection_matches = self.injection_detector.detect(result.processed_content)
        result.injection_matches = injection_matches

        if not injection_matches:
            return result

        # Find highest risk
        risk_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
        highest_risk = min(injection_matches, key=lambda m: risk_order.get(m.risk_level, 99))

        # Check if we should block
        threshold_order = risk_order.get(self.config.injection_risk_threshold, 1)
        match_risk_order = risk_order.get(highest_risk.risk_level, 99)

        if match_risk_order <= threshold_order:
            if self.config.injection_action == TrustAction.BLOCK:
                result.allowed = False
                result.action_taken = TrustAction.BLOCK
                result.block_reason = f"Injection attempt detected: {highest_risk.explanation}"
                logger.warning(
                    f"Blocked injection attempt: {highest_risk.injection_type.value} "
                    f"(risk: {highest_risk.risk_level.value})"
                )
            else:
                result.action_taken = self.config.injection_action
                result.warnings.append(
                    f"Injection attempt detected: {highest_risk.explanation}"
                )

        return result

    def _process_pii(self, result: TrustResult) -> TrustResult:
        """Process content for PII."""
        pii_matches = self.pii_detector.detect(result.processed_content)
        result.pii_matches = pii_matches

        if not pii_matches:
            return result

        # Check for blocking PII types
        blocking_types = {m.pii_type for m in pii_matches} & self.config.pii_types_to_block
        if blocking_types and self.config.pii_action == TrustAction.BLOCK:
            result.allowed = False
            result.action_taken = TrustAction.BLOCK
            result.block_reason = f"Sensitive PII detected: {', '.join(t.value for t in blocking_types)}"
            return result

        # Redact PII if configured
        if self.config.pii_action == TrustAction.REDACT:
            redacted, _ = self.pii_redactor.redact(result.processed_content)
            result.processed_content = redacted
            result.action_taken = TrustAction.REDACT
            result.warnings.append(f"Redacted {len(pii_matches)} PII instances")
        elif self.config.pii_action == TrustAction.WARN:
            result.action_taken = TrustAction.WARN
            result.warnings.append(
                f"PII detected: {', '.join(set(m.pii_type.value for m in pii_matches))}"
            )

        return result

    def _check_rate_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check rate limits for a user."""
        now = datetime.utcnow()
        minute_ago = now.replace(second=0, microsecond=0)
        hour_ago = now.replace(minute=0, second=0, microsecond=0)

        # Clean old entries
        if user_id in self._request_counts:
            self._request_counts[user_id] = [
                t for t in self._request_counts[user_id]
                if t > minute_ago
            ]
        else:
            self._request_counts[user_id] = []

        if user_id in self._blocked_counts:
            self._blocked_counts[user_id] = [
                t for t in self._blocked_counts[user_id]
                if t > hour_ago
            ]
        else:
            self._blocked_counts[user_id] = []

        # Check blocked count
        if len(self._blocked_counts[user_id]) >= self.config.max_blocked_per_hour:
            return False, "Too many blocked requests - please try again later"

        # Check request rate
        if len(self._request_counts[user_id]) >= self.config.max_requests_per_minute:
            return False, "Rate limit exceeded - please slow down"

        # Record this request
        self._request_counts[user_id].append(now)

        return True, None

    def _record_blocked(self, user_id: Optional[str]) -> None:
        """Record a blocked request."""
        if user_id:
            if user_id not in self._blocked_counts:
                self._blocked_counts[user_id] = []
            self._blocked_counts[user_id].append(datetime.utcnow())

    def _log_audit(self, result: TrustResult) -> None:
        """Log result to audit trail."""
        # Keep in-memory audit (limited)
        self._audit_log.append(result)
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

        # Log summary
        if not result.allowed:
            logger.warning(
                f"Trust middleware blocked request: {result.block_reason} "
                f"(audit_id: {result.audit_id})"
            )
        elif result.warnings:
            logger.info(
                f"Trust middleware warnings: {', '.join(result.warnings)} "
                f"(audit_id: {result.audit_id})"
            )

    def get_audit_log(
        self,
        limit: int = 100,
        blocked_only: bool = False,
    ) -> List[TrustResult]:
        """Get recent audit entries."""
        logs = self._audit_log

        if blocked_only:
            logs = [r for r in logs if not r.allowed]

        return logs[-limit:]


# Global instance
_trust_middleware: Optional[TrustMiddleware] = None


def get_trust_middleware() -> TrustMiddleware:
    """Get the global trust middleware instance."""
    global _trust_middleware
    if _trust_middleware is None:
        _trust_middleware = TrustMiddleware()
    return _trust_middleware


async def init_trust_middleware(config: Optional[TrustConfig] = None) -> TrustMiddleware:
    """Initialize the global trust middleware with config."""
    global _trust_middleware
    _trust_middleware = TrustMiddleware(config)
    return _trust_middleware
