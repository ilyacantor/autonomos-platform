"""
Maestra Constitution — rules that govern agent behavior.

The constitution is loaded from embedded rules and enforced at runtime.
"""

import logging
import re

logger = logging.getLogger(__name__)


class Constitution:
    """
    Maestra constitution — rules that govern agent behavior.

    The constitution is loaded from embedded rules and enforced at runtime.
    """

    REQUIRED_RULES = [
        "RACI boundaries must be respected",
        "Silent fallbacks are prohibited",
        "All data changes require audit trail",
        "Human review required for cross-entity decisions",
        "No test-only endpoints in production",
        "Errors must be surfaced, not swallowed",
        "COFA adjustments require explicit approval",
        "Pipeline runs must be idempotent",
    ]

    # Actions that always violate the constitution
    _PROHIBITED_PATTERNS = [
        r"delete\s+production",
        r"drop\s+table",
        r"bypass\s+review",
        r"skip\s+audit",
        r"disable\s+auth",
        r"silent\s+fallback",
        r"swallow\s+error",
        r"mock\s+production",
        r"remove\s+guardrail",
    ]

    # Actions that are always compliant
    _COMPLIANT_PATTERNS = [
        r"record\s+audit",
        r"log\s+entry",
        r"create\s+review",
        r"request\s+approval",
        r"validate\s+schema",
        r"check\s+compliance",
        r"surface\s+error",
    ]

    def __init__(self):
        """Load constitution from embedded rules."""
        self._rules = list(self.REQUIRED_RULES)

    def get_rules(self) -> list[str]:
        """Return all constitution rules."""
        return list(self._rules)

    def check_compliance(self, action: str) -> dict:
        """
        Check if a proposed action complies with the constitution.
        Returns: {"compliant": bool, "violations": [str], "warnings": [str]}
        """
        action_lower = action.lower()
        violations = []
        warnings = []

        # Check for prohibited patterns
        for pattern in self._PROHIBITED_PATTERNS:
            if re.search(pattern, action_lower):
                violations.append(
                    f"Action matches prohibited pattern: '{pattern}'. "
                    f"Rule: '{self._find_related_rule(pattern)}'"
                )

        # Check for compliant patterns — if matched, no further checks
        for pattern in self._COMPLIANT_PATTERNS:
            if re.search(pattern, action_lower):
                return {
                    "compliant": True,
                    "violations": [],
                    "warnings": [],
                }

        # Check against specific rules
        if "cross-entity" in action_lower and "review" not in action_lower:
            warnings.append(
                "Cross-entity actions should include human review. "
                "Rule: 'Human review required for cross-entity decisions'"
            )

        if "data" in action_lower and "audit" not in action_lower and "change" in action_lower:
            warnings.append(
                "Data changes should include audit trail. "
                "Rule: 'All data changes require audit trail'"
            )

        compliant = len(violations) == 0
        return {
            "compliant": compliant,
            "violations": violations,
            "warnings": warnings,
        }

    def get_rule_for_action(self, action_type: str) -> str | None:
        """Get the specific rule governing an action type."""
        action_lower = action_type.lower()
        rule_map = {
            "cross_entity": "Human review required for cross-entity decisions",
            "data_change": "All data changes require audit trail",
            "pipeline_run": "Pipeline runs must be idempotent",
            "error_handling": "Errors must be surfaced, not swallowed",
            "fallback": "Silent fallbacks are prohibited",
            "raci": "RACI boundaries must be respected",
            "cofa": "COFA adjustments require explicit approval",
            "test_endpoint": "No test-only endpoints in production",
        }
        return rule_map.get(action_lower)

    def _find_related_rule(self, pattern: str) -> str:
        """Find the most relevant rule for a prohibited pattern."""
        pattern_rule_map = {
            "delete": "All data changes require audit trail",
            "drop": "All data changes require audit trail",
            "bypass": "Human review required for cross-entity decisions",
            "skip": "All data changes require audit trail",
            "disable": "Errors must be surfaced, not swallowed",
            "silent": "Silent fallbacks are prohibited",
            "swallow": "Errors must be surfaced, not swallowed",
            "mock": "No test-only endpoints in production",
            "remove": "RACI boundaries must be respected",
        }
        for key, rule in pattern_rule_map.items():
            if key in pattern:
                return rule
        return self.REQUIRED_RULES[0]
