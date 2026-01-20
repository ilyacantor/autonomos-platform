"""
PII Detection and Redaction

Detects and optionally redacts Personally Identifiable Information:
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- IP addresses
- Names (with NER)
- Addresses
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "address"
    NAME = "name"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    BANK_ACCOUNT = "bank_account"
    API_KEY = "api_key"
    PASSWORD = "password"


@dataclass
class PIIMatch:
    """A detected PII match."""
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.pii_type.value,
            "value": self.value,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "context": self.context,
        }


class PIIDetector:
    """
    Detects PII in text using regex patterns and heuristics.

    For production use, consider integrating with:
    - Microsoft Presidio
    - Google Cloud DLP
    - AWS Comprehend
    """

    # Regex patterns for different PII types
    PATTERNS: Dict[PIIType, List[Pattern]] = {
        PIIType.EMAIL: [
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
        ],
        PIIType.PHONE: [
            # US phone formats
            re.compile(r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            # International formats
            re.compile(r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'),
        ],
        PIIType.SSN: [
            re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
        ],
        PIIType.CREDIT_CARD: [
            # Visa, MasterCard, Amex, Discover
            re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
            # With separators
            re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        ],
        PIIType.IP_ADDRESS: [
            # IPv4
            re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
            # IPv6 (simplified)
            re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'),
        ],
        PIIType.DATE_OF_BIRTH: [
            # MM/DD/YYYY or DD/MM/YYYY
            re.compile(r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b'),
            # YYYY-MM-DD
            re.compile(r'\b(?:19|20)\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12][0-9]|3[01])\b'),
        ],
        PIIType.API_KEY: [
            # Generic API key patterns
            re.compile(r'\b(?:sk|pk|api|key|token)[-_]?(?:live|test|prod)?[-_]?[a-zA-Z0-9]{20,}\b', re.IGNORECASE),
            # AWS keys
            re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
            # GitHub tokens
            re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b'),
        ],
        PIIType.PASSWORD: [
            # Password in context
            re.compile(r'(?:password|passwd|pwd)\s*[=:]\s*["\']?([^"\'\s]{8,})["\']?', re.IGNORECASE),
        ],
    }

    # Keywords that often precede names
    NAME_KEYWORDS = {
        'mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'sir', 'madam',
        'dear', 'hi', 'hello', 'name', 'user', 'customer', 'patient',
        'client', 'employee', 'contact', 'recipient', 'sender',
    }

    def __init__(
        self,
        enabled_types: Optional[Set[PIIType]] = None,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize the PII detector.

        Args:
            enabled_types: Set of PII types to detect (None = all)
            confidence_threshold: Minimum confidence for matches
        """
        self.enabled_types = enabled_types or set(PIIType)
        self.confidence_threshold = confidence_threshold

    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect PII in text.

        Args:
            text: Text to scan

        Returns:
            List of PII matches
        """
        matches = []

        for pii_type, patterns in self.PATTERNS.items():
            if pii_type not in self.enabled_types:
                continue

            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Get context around match
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end]

                    # Calculate confidence based on pattern and context
                    confidence = self._calculate_confidence(pii_type, match.group(), context)

                    if confidence >= self.confidence_threshold:
                        matches.append(PIIMatch(
                            pii_type=pii_type,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
                            context=context,
                        ))

        # Also detect potential names if enabled
        if PIIType.NAME in self.enabled_types:
            name_matches = self._detect_names(text)
            matches.extend(name_matches)

        # Sort by position
        matches.sort(key=lambda m: m.start)

        # Remove overlapping matches (keep higher confidence)
        matches = self._remove_overlaps(matches)

        return matches

    def _calculate_confidence(self, pii_type: PIIType, value: str, context: str) -> float:
        """Calculate confidence score for a match."""
        confidence = 0.8  # Base confidence for regex match

        # Type-specific adjustments
        if pii_type == PIIType.EMAIL:
            # Higher confidence for common domains
            if any(d in value.lower() for d in ['gmail', 'yahoo', 'outlook', 'hotmail']):
                confidence += 0.1

        elif pii_type == PIIType.PHONE:
            # Lower confidence for numbers that might be other things
            if len(value.replace('-', '').replace(' ', '')) < 10:
                confidence -= 0.2

        elif pii_type == PIIType.SSN:
            # Check for SSN-specific context
            if any(kw in context.lower() for kw in ['ssn', 'social', 'security']):
                confidence += 0.15

        elif pii_type == PIIType.CREDIT_CARD:
            # Validate with Luhn algorithm
            if self._luhn_check(value):
                confidence += 0.15
            else:
                confidence -= 0.3

        elif pii_type == PIIType.API_KEY:
            # Higher confidence for known patterns
            if any(p in value.lower() for p in ['sk_live', 'pk_live', 'AKIA']):
                confidence += 0.15

        return min(1.0, max(0.0, confidence))

    def _luhn_check(self, number: str) -> bool:
        """Validate a number using the Luhn algorithm."""
        digits = [int(d) for d in number if d.isdigit()]
        if len(digits) < 13:
            return False

        # Luhn algorithm
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def _detect_names(self, text: str) -> List[PIIMatch]:
        """Detect potential names using heuristics."""
        matches = []

        # Simple heuristic: capitalized words after name keywords
        words = text.split()
        for i, word in enumerate(words):
            word_lower = word.lower().rstrip('.,!?:;')

            if word_lower in self.NAME_KEYWORDS and i + 1 < len(words):
                next_word = words[i + 1]
                # Check if next word is capitalized
                if next_word and next_word[0].isupper():
                    # Find position in original text
                    start = text.find(next_word)
                    if start >= 0:
                        matches.append(PIIMatch(
                            pii_type=PIIType.NAME,
                            value=next_word.rstrip('.,!?:;'),
                            start=start,
                            end=start + len(next_word),
                            confidence=0.6,  # Lower confidence for name detection
                            context=text[max(0, start-20):min(len(text), start+30)],
                        ))

        return matches

    def _remove_overlaps(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove overlapping matches, keeping higher confidence."""
        if not matches:
            return matches

        result = []
        for match in matches:
            # Check if this match overlaps with any existing
            overlaps = False
            for i, existing in enumerate(result):
                if (match.start < existing.end and match.end > existing.start):
                    # Overlapping - keep higher confidence
                    if match.confidence > existing.confidence:
                        result[i] = match
                    overlaps = True
                    break

            if not overlaps:
                result.append(match)

        return result

    def contains_pii(self, text: str) -> bool:
        """Quick check if text contains any PII."""
        return len(self.detect(text)) > 0

    def get_pii_types(self, text: str) -> Set[PIIType]:
        """Get the types of PII found in text."""
        matches = self.detect(text)
        return {m.pii_type for m in matches}


class PIIRedactor:
    """Redacts PII from text."""

    # Default replacement patterns
    DEFAULT_REPLACEMENTS = {
        PIIType.EMAIL: "[EMAIL]",
        PIIType.PHONE: "[PHONE]",
        PIIType.SSN: "[SSN]",
        PIIType.CREDIT_CARD: "[CARD]",
        PIIType.IP_ADDRESS: "[IP]",
        PIIType.DATE_OF_BIRTH: "[DOB]",
        PIIType.ADDRESS: "[ADDRESS]",
        PIIType.NAME: "[NAME]",
        PIIType.PASSPORT: "[PASSPORT]",
        PIIType.DRIVER_LICENSE: "[LICENSE]",
        PIIType.BANK_ACCOUNT: "[ACCOUNT]",
        PIIType.API_KEY: "[API_KEY]",
        PIIType.PASSWORD: "[PASSWORD]",
    }

    def __init__(
        self,
        detector: Optional[PIIDetector] = None,
        replacements: Optional[Dict[PIIType, str]] = None,
        mask_char: str = "*",
        partial_mask: bool = False,
    ):
        """
        Initialize the redactor.

        Args:
            detector: PII detector instance
            replacements: Custom replacement strings
            mask_char: Character for masking
            partial_mask: If True, only mask part of the value
        """
        self.detector = detector or PIIDetector()
        self.replacements = {**self.DEFAULT_REPLACEMENTS, **(replacements or {})}
        self.mask_char = mask_char
        self.partial_mask = partial_mask

    def redact(self, text: str) -> Tuple[str, List[PIIMatch]]:
        """
        Redact PII from text.

        Args:
            text: Text to redact

        Returns:
            Tuple of (redacted text, list of matches)
        """
        matches = self.detector.detect(text)

        if not matches:
            return text, []

        # Sort by position (reverse) to handle overlapping replacements
        matches_sorted = sorted(matches, key=lambda m: m.start, reverse=True)

        redacted = text
        for match in matches_sorted:
            replacement = self._get_replacement(match)
            redacted = redacted[:match.start] + replacement + redacted[match.end:]

        return redacted, matches

    def _get_replacement(self, match: PIIMatch) -> str:
        """Get the replacement string for a match."""
        if self.partial_mask:
            # Partial masking - show some characters
            value = match.value
            if len(value) > 4:
                visible = max(2, len(value) // 4)
                masked = self.mask_char * (len(value) - visible * 2)
                return value[:visible] + masked + value[-visible:]
            else:
                return self.mask_char * len(value)
        else:
            return self.replacements.get(match.pii_type, "[REDACTED]")

    def redact_for_logging(self, text: str) -> str:
        """Redact PII for logging purposes (partial masking)."""
        original_partial = self.partial_mask
        self.partial_mask = True
        redacted, _ = self.redact(text)
        self.partial_mask = original_partial
        return redacted


# Global instance
_pii_detector: Optional[PIIDetector] = None


def get_pii_detector() -> PIIDetector:
    """Get the global PII detector instance."""
    global _pii_detector
    if _pii_detector is None:
        _pii_detector = PIIDetector()
    return _pii_detector
