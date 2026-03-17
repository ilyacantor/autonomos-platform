"""
Triple formatter for Maestra context assembly.

Converts raw triple store rows into structured, human-readable text
suitable for LLM consumption. Separate module per spec requirement:
formatting logic must be adjustable without touching assembler logic.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_value(raw_value: Any) -> str:
    """Format a JSONB value from the triple store into a display string.

    The triple store stores values as JSONB. Python receives them as
    native types (float, int, str, dict, list). This function produces
    a clean human-readable representation.
    """
    if raw_value is None:
        return "null"
    if isinstance(raw_value, (dict, list)):
        return json.dumps(raw_value, default=str)
    if isinstance(raw_value, float):
        # Format currency-like values with commas; skip decimals if .0
        if raw_value == int(raw_value) and abs(raw_value) >= 1000:
            return f"{int(raw_value):,}"
        if abs(raw_value) >= 1000:
            return f"{raw_value:,.2f}"
        return str(raw_value)
    if isinstance(raw_value, int) and abs(raw_value) >= 1000:
        return f"{raw_value:,}"
    return str(raw_value)


def format_triples_for_llm(triples: list[dict]) -> str:
    """Format a list of triple store rows into structured text for LLM context.

    Each triple is rendered on its own line in a pipe-separated format
    that is easy for the LLM to parse and cite.

    Args:
        triples: List of dicts with keys: entity_id, concept, property,
                 value, period, source_system.

    Returns:
        Formatted text block. Empty string if no triples.
    """
    if not triples:
        return ""

    lines = []
    for row in triples:
        entity = row.get("entity_id", "unknown")
        concept = row.get("concept", "unknown")
        prop = row.get("property", "unknown")
        value = format_value(row.get("value"))
        period = row.get("period") or "N/A"
        source = row.get("source_system") or "unknown"

        lines.append(
            f"Entity: {entity} | Concept: {concept} | "
            f"Property: {prop} | Value: {value} | "
            f"Period: {period} | Source: {source}"
        )

    header = f"--- Data Context: {len(lines)} triples from semantic store ---"
    return header + "\n" + "\n".join(lines)
