"""
Prompt Injection Detection

Detects and blocks prompt injection attacks:
- Direct injection attempts
- Indirect injection via tool outputs
- Jailbreak attempts
- Role/persona manipulation
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Pattern, Set, Tuple

logger = logging.getLogger(__name__)


class InjectionType(str, Enum):
    """Types of injection attacks."""
    DIRECT_INJECTION = "direct_injection"       # Explicit instruction override
    INDIRECT_INJECTION = "indirect_injection"   # Hidden instructions in data
    JAILBREAK = "jailbreak"                     # Attempt to bypass safety
    ROLE_MANIPULATION = "role_manipulation"     # Change assistant behavior
    PROMPT_LEAKING = "prompt_leaking"           # Attempt to extract system prompt
    CONTEXT_MANIPULATION = "context_manipulation"  # Alter conversation context
    ENCODING_ATTACK = "encoding_attack"         # Use encoding to bypass filters


class RiskLevel(str, Enum):
    """Risk level of detected injection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InjectionMatch:
    """A detected injection attempt."""
    injection_type: InjectionType
    risk_level: RiskLevel
    pattern_matched: str
    value: str
    start: int
    end: int
    confidence: float
    explanation: str

    def to_dict(self) -> dict:
        return {
            "type": self.injection_type.value,
            "risk_level": self.risk_level.value,
            "pattern": self.pattern_matched,
            "value": self.value,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


class InjectionDetector:
    """
    Detects prompt injection attacks.

    For production use, consider integrating with:
    - Lakera Guard
    - Guardrails AI
    - Rebuff
    """

    # Patterns for direct injection
    DIRECT_INJECTION_PATTERNS: List[Tuple[Pattern, str, RiskLevel]] = [
        # Ignore previous instructions
        (re.compile(r'\b(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?|context)\b', re.IGNORECASE),
         "ignore_previous", RiskLevel.CRITICAL),

        # New instruction override
        (re.compile(r'\b(?:new\s+)?(?:instruction|directive|command|order)s?\s*[:=]\s*', re.IGNORECASE),
         "instruction_override", RiskLevel.HIGH),

        # System prompt override
        (re.compile(r'\b(?:system\s+)?prompt\s*[:=]|\[\s*system\s*\]|<\s*system\s*>', re.IGNORECASE),
         "system_prompt", RiskLevel.CRITICAL),

        # Role assignment
        (re.compile(r'\byou\s+are\s+(?:now|a|an|the)\b|\bact\s+as\s+(?:if\s+you\s+were|a|an)\b|\bpretend\s+(?:to\s+be|you\'re)\b', re.IGNORECASE),
         "role_assignment", RiskLevel.HIGH),

        # Developer/debug mode
        (re.compile(r'\b(?:enter|enable|activate)\s+(?:developer|debug|admin|root|sudo)\s+mode\b', re.IGNORECASE),
         "debug_mode", RiskLevel.CRITICAL),
    ]

    # Patterns for jailbreak attempts
    JAILBREAK_PATTERNS: List[Tuple[Pattern, str, RiskLevel]] = [
        # DAN-style jailbreaks
        (re.compile(r'\bDAN\b|\bDo\s+Anything\s+Now\b', re.IGNORECASE),
         "dan_jailbreak", RiskLevel.CRITICAL),

        # Hypothetical scenarios
        (re.compile(r'\b(?:hypothetically|theoretically|in\s+a\s+fictional)\b.*(?:could\s+you|would\s+you|can\s+you)\b', re.IGNORECASE),
         "hypothetical_bypass", RiskLevel.MEDIUM),

        # Roleplaying bypass
        (re.compile(r'\b(?:let\'s\s+)?(?:roleplay|play\s+a\s+game|pretend)\b.*(?:no\s+rules?|anything|unrestricted)\b', re.IGNORECASE),
         "roleplay_bypass", RiskLevel.HIGH),

        # Opposite day
        (re.compile(r'\b(?:opposite\s+day|reverse\s+mode|opposite\s+of\s+what)\b', re.IGNORECASE),
         "opposite_bypass", RiskLevel.MEDIUM),

        # Character impersonation
        (re.compile(r'\byou\s+are\s+(?:evil|unethical|unrestricted|jailbroken)\b', re.IGNORECASE),
         "evil_persona", RiskLevel.CRITICAL),
    ]

    # Patterns for prompt leaking
    PROMPT_LEAK_PATTERNS: List[Tuple[Pattern, str, RiskLevel]] = [
        # Direct system prompt requests
        (re.compile(r'\b(?:show|reveal|display|print|output|repeat)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?|guidelines?)\b', re.IGNORECASE),
         "show_prompt", RiskLevel.HIGH),

        # Indirect extraction
        (re.compile(r'\bwhat\s+(?:are|were)\s+(?:your\s+)?(?:original|initial|first)\s+(?:instructions?|prompts?)\b', re.IGNORECASE),
         "extract_prompt", RiskLevel.HIGH),

        # Verbatim request
        (re.compile(r'\b(?:verbatim|word\s+for\s+word|exactly)\b.*(?:prompt|instructions?)\b', re.IGNORECASE),
         "verbatim_prompt", RiskLevel.HIGH),
    ]

    # Patterns for context manipulation
    CONTEXT_PATTERNS: List[Tuple[Pattern, str, RiskLevel]] = [
        # Memory manipulation
        (re.compile(r'\b(?:forget|delete|clear|reset)\s+(?:everything|all|your\s+memory|conversation)\b', re.IGNORECASE),
         "memory_clear", RiskLevel.MEDIUM),

        # Context injection markers
        (re.compile(r'```(?:system|assistant|user)\b|<\|(?:system|assistant|user)\|>', re.IGNORECASE),
         "context_markers", RiskLevel.HIGH),

        # Token manipulation
        (re.compile(r'<\|(?:im_start|im_end|endoftext)\|>|\[/?(?:INST|SYS)\]', re.IGNORECASE),
         "token_injection", RiskLevel.CRITICAL),
    ]

    # Patterns for encoding attacks
    ENCODING_PATTERNS: List[Tuple[Pattern, str, RiskLevel]] = [
        # Base64 encoded instructions
        (re.compile(r'\b(?:decode|base64)\s*[:=]?\s*[A-Za-z0-9+/=]{20,}', re.IGNORECASE),
         "base64_encoded", RiskLevel.MEDIUM),

        # Unicode escapes
        (re.compile(r'(?:\\u[0-9a-fA-F]{4}){4,}'),
         "unicode_escape", RiskLevel.MEDIUM),

        # Hex encoded
        (re.compile(r'(?:0x[0-9a-fA-F]{2}\s*){8,}'),
         "hex_encoded", RiskLevel.MEDIUM),
    ]

    # Suspicious keywords that increase risk
    SUSPICIOUS_KEYWORDS = {
        'bypass', 'override', 'hack', 'exploit', 'jailbreak', 'unrestricted',
        'unlimited', 'uncensored', 'unfiltered', 'dangerous', 'harmful',
        'illegal', 'malicious', 'evil', 'ignore safety', 'no restrictions',
    }

    def __init__(
        self,
        enabled_types: Optional[Set[InjectionType]] = None,
        confidence_threshold: float = 0.6,
        check_suspicious_keywords: bool = True,
    ):
        """
        Initialize the injection detector.

        Args:
            enabled_types: Set of injection types to detect (None = all)
            confidence_threshold: Minimum confidence for matches
            check_suspicious_keywords: Whether to flag suspicious keywords
        """
        self.enabled_types = enabled_types or set(InjectionType)
        self.confidence_threshold = confidence_threshold
        self.check_suspicious_keywords = check_suspicious_keywords

    def detect(self, text: str, context: Optional[str] = None) -> List[InjectionMatch]:
        """
        Detect injection attempts in text.

        Args:
            text: Text to scan (user input)
            context: Optional context (e.g., tool output being injected)

        Returns:
            List of injection matches
        """
        matches = []

        # Check direct injection patterns
        if InjectionType.DIRECT_INJECTION in self.enabled_types:
            for pattern, name, risk in self.DIRECT_INJECTION_PATTERNS:
                matches.extend(self._find_matches(
                    text, pattern, name, InjectionType.DIRECT_INJECTION, risk
                ))

        # Check jailbreak patterns
        if InjectionType.JAILBREAK in self.enabled_types:
            for pattern, name, risk in self.JAILBREAK_PATTERNS:
                matches.extend(self._find_matches(
                    text, pattern, name, InjectionType.JAILBREAK, risk
                ))

        # Check prompt leaking patterns
        if InjectionType.PROMPT_LEAKING in self.enabled_types:
            for pattern, name, risk in self.PROMPT_LEAK_PATTERNS:
                matches.extend(self._find_matches(
                    text, pattern, name, InjectionType.PROMPT_LEAKING, risk
                ))

        # Check context manipulation
        if InjectionType.CONTEXT_MANIPULATION in self.enabled_types:
            for pattern, name, risk in self.CONTEXT_PATTERNS:
                matches.extend(self._find_matches(
                    text, pattern, name, InjectionType.CONTEXT_MANIPULATION, risk
                ))

        # Check encoding attacks
        if InjectionType.ENCODING_ATTACK in self.enabled_types:
            for pattern, name, risk in self.ENCODING_PATTERNS:
                matches.extend(self._find_matches(
                    text, pattern, name, InjectionType.ENCODING_ATTACK, risk
                ))

        # Check suspicious keywords
        if self.check_suspicious_keywords:
            keyword_match = self._check_suspicious_keywords(text)
            if keyword_match:
                matches.append(keyword_match)

        # Filter by confidence threshold
        matches = [m for m in matches if m.confidence >= self.confidence_threshold]

        # Sort by risk level (critical first)
        risk_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
        matches.sort(key=lambda m: risk_order.get(m.risk_level, 99))

        return matches

    def _find_matches(
        self,
        text: str,
        pattern: Pattern,
        pattern_name: str,
        injection_type: InjectionType,
        risk_level: RiskLevel,
    ) -> List[InjectionMatch]:
        """Find all matches for a pattern."""
        matches = []

        for match in pattern.finditer(text):
            confidence = self._calculate_confidence(text, match, risk_level)

            matches.append(InjectionMatch(
                injection_type=injection_type,
                risk_level=risk_level,
                pattern_matched=pattern_name,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=confidence,
                explanation=self._get_explanation(injection_type, pattern_name),
            ))

        return matches

    def _calculate_confidence(
        self,
        text: str,
        match: re.Match,
        risk_level: RiskLevel,
    ) -> float:
        """Calculate confidence score for a match."""
        # Base confidence by risk level
        base_confidence = {
            RiskLevel.CRITICAL: 0.9,
            RiskLevel.HIGH: 0.8,
            RiskLevel.MEDIUM: 0.7,
            RiskLevel.LOW: 0.6,
        }.get(risk_level, 0.5)

        # Adjust based on context
        text_lower = text.lower()

        # Increase for multiple suspicious keywords
        suspicious_count = sum(1 for kw in self.SUSPICIOUS_KEYWORDS if kw in text_lower)
        base_confidence += min(0.1, suspicious_count * 0.02)

        # Increase for longer matching text (more deliberate)
        if len(match.group()) > 30:
            base_confidence += 0.05

        # Decrease if appears to be quoted/code
        context_start = max(0, match.start() - 10)
        context_end = min(len(text), match.end() + 10)
        context = text[context_start:context_end]
        if '```' in context or '"' in context or "'" in context:
            base_confidence -= 0.1

        return min(1.0, max(0.0, base_confidence))

    def _check_suspicious_keywords(self, text: str) -> Optional[InjectionMatch]:
        """Check for suspicious keyword combinations."""
        text_lower = text.lower()
        found_keywords = [kw for kw in self.SUSPICIOUS_KEYWORDS if kw in text_lower]

        if len(found_keywords) >= 2:
            # Find first keyword position
            first_kw = found_keywords[0]
            start = text_lower.find(first_kw)

            return InjectionMatch(
                injection_type=InjectionType.DIRECT_INJECTION,
                risk_level=RiskLevel.MEDIUM,
                pattern_matched="suspicious_keywords",
                value=", ".join(found_keywords),
                start=start,
                end=start + len(first_kw),
                confidence=min(0.9, 0.5 + len(found_keywords) * 0.1),
                explanation=f"Multiple suspicious keywords detected: {', '.join(found_keywords)}",
            )

        return None

    def _get_explanation(self, injection_type: InjectionType, pattern_name: str) -> str:
        """Get human-readable explanation for a match."""
        explanations = {
            ("ignore_previous", InjectionType.DIRECT_INJECTION):
                "Attempt to make the AI ignore its instructions",
            ("instruction_override", InjectionType.DIRECT_INJECTION):
                "Attempt to override AI instructions with new ones",
            ("system_prompt", InjectionType.DIRECT_INJECTION):
                "Attempt to inject system-level instructions",
            ("role_assignment", InjectionType.DIRECT_INJECTION):
                "Attempt to change the AI's role or persona",
            ("debug_mode", InjectionType.DIRECT_INJECTION):
                "Attempt to enable privileged modes",
            ("dan_jailbreak", InjectionType.JAILBREAK):
                "Known jailbreak technique (DAN)",
            ("hypothetical_bypass", InjectionType.JAILBREAK):
                "Using hypothetical framing to bypass safety",
            ("roleplay_bypass", InjectionType.JAILBREAK):
                "Using roleplay to bypass restrictions",
            ("evil_persona", InjectionType.JAILBREAK):
                "Attempting to make AI act maliciously",
            ("show_prompt", InjectionType.PROMPT_LEAKING):
                "Attempting to extract system prompt",
            ("context_markers", InjectionType.CONTEXT_MANIPULATION):
                "Injecting conversation context markers",
            ("token_injection", InjectionType.CONTEXT_MANIPULATION):
                "Injecting special tokens to manipulate context",
            ("base64_encoded", InjectionType.ENCODING_ATTACK):
                "Potentially encoded malicious content",
        }

        return explanations.get(
            (pattern_name, injection_type),
            f"Potential {injection_type.value} attempt detected"
        )

    def is_safe(self, text: str) -> Tuple[bool, List[InjectionMatch]]:
        """
        Check if text is safe (no injections detected).

        Returns:
            Tuple of (is_safe, list of matches if unsafe)
        """
        matches = self.detect(text)

        # Consider unsafe if any high/critical risk matches
        unsafe = any(m.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] for m in matches)

        return not unsafe, matches

    def get_risk_level(self, text: str) -> RiskLevel:
        """Get the highest risk level found in text."""
        matches = self.detect(text)

        if not matches:
            return RiskLevel.LOW

        risk_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
        for risk in risk_order:
            if any(m.risk_level == risk for m in matches):
                return risk

        return RiskLevel.LOW


# Global instance
_injection_detector: Optional[InjectionDetector] = None


def get_injection_detector() -> InjectionDetector:
    """Get the global injection detector instance."""
    global _injection_detector
    if _injection_detector is None:
        _injection_detector = InjectionDetector()
    return _injection_detector
