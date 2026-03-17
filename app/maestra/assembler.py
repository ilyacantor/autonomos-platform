"""
Maestra Context Assembler — WP-1

Assembles the full prompt context for Maestra general-purpose chat:
  (a) Constitution loading (all layers, in order)
  (b) Triple retrieval via SQL (domain keyword matching -> Postgres query)
  (c) Zero-result safeguard (§10.1 compliance)
  (d) Prompt assembly (system message for Claude)

This module does NOT call the NLQ query engine. It queries Postgres directly.
"""

import asyncio
import logging
import os
import re
from pathlib import Path

import yaml

from app.maestra.db import get_connection, get_tenant_id
from app.maestra.formatter import format_triples_for_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CONSTITUTION_DIR = Path(__file__).parent / "constitution"
_MODULES_DIR = _CONSTITUTION_DIR / "modules"
_KEYWORDS_PATH = Path(__file__).parent / "domain_keywords.yaml"

# Constitution files in strict layer order per §3.4.
# Every file listed here is loaded on every request.
_CONSTITUTION_FILES = [
    "LAYER_0_ACCOUNTING_AXIOMS.md",
    "LAYER_1_IDENTITY.md",
    "LAYER_1_PNL_CONSTITUTION.md",
    "LAYER_1_BS_CONSTITUTION.md",
    "LAYER_2_WORKFLOW.md",
    "LAYER_3_PLAYBOOK_TEMPLATE.md",
    "LAYER_4_QUALITY_GATES.md",
]

# Max triples to return from a single retrieval.  ~4 000 tokens budget.
# Override with MAESTRA_TRIPLE_MAX_ROWS env var.
_DEFAULT_MAX_ROWS = 300

# Known module contexts that have (or will have) a module knowledge doc.
_KNOWN_MODULES = {"aod", "aam", "farm", "dcl", "nlq", "convergence"}

# Default domain when no keyword match but module_context provides a hint.
_MODULE_DEFAULT_DOMAINS: dict[str, list[str]] = {
    "aam": ["cofa", "cofa_mapping", "cofa_conflict"],
    "farm": ["gl", "pnl", "revenue", "cogs"],
}
# dcl, nlq, aod, convergence -> no default; pull a sample across domains.


# ---------------------------------------------------------------------------
# Constitution loader
# ---------------------------------------------------------------------------

def _load_constitution_text() -> str:
    """Read all constitution layer files in order and concatenate."""
    parts: list[str] = []
    for filename in _CONSTITUTION_FILES:
        path = _CONSTITUTION_DIR / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Constitution file missing: {path} — "
                f"Maestra cannot operate without her full constitution"
            )
        parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def _load_module_doc(module_context: str | None) -> str | None:
    """Load a single module knowledge doc, if it exists.

    HARD RULE: never load more than one module doc per request.
    Returns None if module_context is invalid or file doesn't exist.
    """
    if not module_context:
        return None

    module_context = module_context.strip().lower()
    if module_context not in _KNOWN_MODULES:
        logger.debug(
            "module_context '%s' is not a known module — skipping module doc",
            module_context,
        )
        return None

    doc_path = _MODULES_DIR / f"{module_context}.md"
    if not doc_path.exists():
        logger.debug(
            "Module doc not found at %s — skipping (WP-3 may not have run yet)",
            doc_path,
        )
        return None

    content = doc_path.read_text(encoding="utf-8")
    logger.info("Loaded module knowledge doc: %s", doc_path)
    return content


# ---------------------------------------------------------------------------
# Domain keyword matching
# ---------------------------------------------------------------------------

def _load_domain_keywords() -> dict[str, list[str]]:
    """Load the domain keyword mapping from YAML config."""
    if not _KEYWORDS_PATH.exists():
        raise FileNotFoundError(
            f"Domain keywords config missing: {_KEYWORDS_PATH} — "
            f"Maestra cannot map user questions to triple store domains"
        )
    with open(_KEYWORDS_PATH, encoding="utf-8") as f:
        mapping = yaml.safe_load(f)
    if not isinstance(mapping, dict):
        raise ValueError(
            f"domain_keywords.yaml must be a dict mapping domain -> keyword list, "
            f"got {type(mapping).__name__}"
        )
    return mapping


# Module-level load (fails fast at import if config is bad).
_DOMAIN_KEYWORDS = _load_domain_keywords()


def extract_domains(
    message: str,
    module_context: str | None,
) -> tuple[list[str], bool]:
    """Extract triple store domain prefixes from a user message.

    Scans message for keywords defined in domain_keywords.yaml.
    Falls back to module_context defaults if no keyword match.

    Returns:
        (domains, from_keywords) — domains is the list of matched domain
        prefixes; from_keywords is True if they came from the user's message
        keywords, False if they came from module_context fallback defaults.
        Empty list + False if no domain is identifiable.
    """
    message_lower = message.lower()
    matched: set[str] = set()

    for domain, keywords in _DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            # Use word-boundary-aware search for short keywords,
            # simple substring for multi-word phrases.
            if " " in keyword:
                if keyword in message_lower:
                    matched.add(domain)
                    break
            else:
                if re.search(rf"\b{re.escape(keyword)}\b", message_lower):
                    matched.add(domain)
                    break

    if matched:
        return sorted(matched), True

    # No keyword match — check module_context defaults.
    if module_context and module_context.lower() in _MODULE_DEFAULT_DOMAINS:
        defaults = _MODULE_DEFAULT_DOMAINS[module_context.lower()]
        logger.debug(
            "No keyword domain match — falling back to module_context '%s' "
            "defaults: %s",
            module_context,
            defaults,
        )
        return defaults, False

    # No domain identifiable — conceptual question.
    return [], False


# ---------------------------------------------------------------------------
# Entity detection
# ---------------------------------------------------------------------------

_entity_cache: list[str] | None = None


def _get_known_entities() -> list[str]:
    """Fetch distinct entity_ids from the triple store.

    Cached after first call to avoid repeated DB hits.
    """
    global _entity_cache
    if _entity_cache is not None:
        return _entity_cache

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT entity_id FROM semantic_triples "
                "WHERE is_active = true ORDER BY entity_id"
            )
            _entity_cache = [row["entity_id"] for row in cur.fetchall()]
            logger.info("Loaded known entities from triple store: %s", _entity_cache)
            return _entity_cache
    finally:
        conn.close()


def detect_entity(message: str) -> str | None:
    """Detect an entity_id mentioned in the user's message.

    Compares against actual entity_ids in the triple store (fetched from DB,
    not hardcoded) using case-insensitive word boundary matching.
    Returns the first match, or None.
    """
    message_lower = message.lower()
    for entity_id in _get_known_entities():
        if re.search(rf"\b{re.escape(entity_id.lower())}\b", message_lower):
            return entity_id
    return None


# ---------------------------------------------------------------------------
# Triple retrieval via SQL
# ---------------------------------------------------------------------------

def _get_max_rows() -> int:
    """Get the max rows limit from env or default."""
    raw = os.environ.get("MAESTRA_TRIPLE_MAX_ROWS")
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning(
                "MAESTRA_TRIPLE_MAX_ROWS=%s is not a valid integer — "
                "using default %d",
                raw,
                _DEFAULT_MAX_ROWS,
            )
    return _DEFAULT_MAX_ROWS


def _resolve_tenant_id() -> str | None:
    """Resolve the tenant_id for triple store queries.

    The TENANT_ID env var is the Platform tenant. The triple store may use
    a different tenant_id (Farm-generated UUID). We look up the actual
    tenant_id from the store if the configured one has no triples.
    """
    import uuid as _uuid

    try:
        configured = get_tenant_id()
    except RuntimeError:
        configured = None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Only check configured tenant if it's a valid UUID
            # (tenant_id column is UUID type in Postgres).
            if configured:
                try:
                    _uuid.UUID(configured)
                    cur.execute(
                        "SELECT 1 FROM semantic_triples "
                        "WHERE tenant_id = %s AND is_active = true LIMIT 1",
                        (configured,),
                    )
                    if cur.fetchone():
                        return configured
                except ValueError:
                    logger.debug(
                        "TENANT_ID '%s' is not a valid UUID — "
                        "will resolve from triple store",
                        configured,
                    )

            # Fall back: get the tenant_id that actually has triples.
            cur.execute(
                "SELECT tenant_id FROM semantic_triples "
                "WHERE is_active = true "
                "GROUP BY tenant_id ORDER BY COUNT(*) DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                resolved = str(row["tenant_id"])
                logger.info(
                    "Resolved triple store tenant_id=%s (configured=%s)",
                    resolved,
                    configured,
                )
                return resolved
            return configured
    finally:
        conn.close()


# Cached after first resolution.
_resolved_tenant: str | None = None


def _get_tenant_for_triples() -> str | None:
    """Get the cached tenant_id for triple queries."""
    global _resolved_tenant
    if _resolved_tenant is None:
        _resolved_tenant = _resolve_tenant_id()
    return _resolved_tenant


def retrieve_triples(
    domains: list[str],
    entity_id: str | None,
) -> list[dict]:
    """Query the triple store for triples matching the given domains.

    Executes the filtering in Postgres — does NOT pull all triples into
    Python memory. Uses parameterized queries exclusively.

    Args:
        domains: Concept domain prefixes to filter on.
        entity_id: Optional entity filter (omitted if None).

    Returns:
        List of triple dicts with keys: entity_id, concept, property,
        value, period, source_system.
    """
    if not domains:
        return []

    max_rows = _get_max_rows()
    tenant_id = _get_tenant_for_triples()

    # Build WHERE clause with parameterized LIKE conditions.
    conditions = ["is_active = true"]
    params: dict = {"max_rows": max_rows}

    if tenant_id:
        conditions.append("tenant_id = %(tenant_id)s")
        params["tenant_id"] = tenant_id

    # Domain filter: OR across all matched domains.
    domain_clauses = []
    for i, domain in enumerate(domains):
        param_name = f"domain_{i}"
        domain_clauses.append(f"concept LIKE %({param_name})s")
        params[param_name] = f"{domain}.%"

    if domain_clauses:
        conditions.append(f"({' OR '.join(domain_clauses)})")

    if entity_id:
        conditions.append("entity_id = %(entity_id)s")
        params["entity_id"] = entity_id

    where = " AND ".join(conditions)
    query = (
        f"SELECT entity_id, concept, property, value, period, source_system "
        f"FROM semantic_triples "
        f"WHERE {where} "
        f"ORDER BY concept, period DESC "
        f"LIMIT %(max_rows)s"
    )

    logger.info(
        "Maestra triple retrieval — domains=%s, entity=%s, tenant=%s, "
        "max_rows=%d, SQL WHERE: %s",
        domains,
        entity_id,
        tenant_id,
        max_rows,
        where,
    )

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            logger.info(
                "Maestra triple retrieval returned %d rows for domains=%s, entity=%s",
                len(rows),
                domains,
                entity_id,
            )
            return [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Zero-result safeguard
# ---------------------------------------------------------------------------

def build_zero_result_note(
    domains: list[str],
    entity_id: str | None,
) -> str:
    """Build the zero-result safeguard note per §10.1.

    Only injected when: triples returned zero AND a valid domain WAS
    identified from the user's message. NOT injected for conceptual
    questions (no domain detected).
    """
    domain_str = ", ".join(domains)
    entity_str = entity_id or "all entities"
    return (
        f"DATA RETRIEVAL NOTE: No triples were found for domain [{domain_str}] "
        f"and entity [{entity_str}]. You must not fabricate or infer data from "
        f"your training knowledge. Tell the user this data is not yet available "
        f"in the system and briefly explain what pipeline step would produce it."
    )


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

# Load constitution once at module level.
_CONSTITUTION_TEXT = _load_constitution_text()


def assemble_prompt(
    message: str,
    module_context: str | None,
) -> tuple[str, list[str], str | None]:
    """Assemble the full system prompt for a Maestra context chat.

    Returns:
        (system_prompt, matched_domains, entity_id)
        - system_prompt: The complete system message for Claude.
        - matched_domains: Domain prefixes that were matched (for logging).
        - entity_id: The entity detected from the message (for logging).
    """
    parts: list[str] = []

    # (a) Constitution — always loaded, all layers in order.
    parts.append(_CONSTITUTION_TEXT)

    # Module knowledge doc — at most one, per module_context.
    module_doc = _load_module_doc(module_context)
    if module_doc:
        parts.append(f"\n\n# Module Context: {module_context}\n\n{module_doc}")

    # (b) Triple retrieval.
    domains, from_keywords = extract_domains(message, module_context)
    entity_id = detect_entity(message)
    triples = retrieve_triples(domains, entity_id) if domains else []

    # Format triple context.
    triple_text = format_triples_for_llm(triples)

    if triple_text:
        parts.append(f"\n\n# Live Data from Semantic Triple Store\n\n{triple_text}")
    elif domains and from_keywords:
        # (c) Zero-result safeguard — domain detected FROM USER'S MESSAGE
        # but no data found. Per §10.1, we must not let Maestra fabricate.
        # Only triggered when keywords matched (not module_context defaults).
        note = build_zero_result_note(domains, entity_id)
        parts.append(f"\n\n# {note}")
    # else: no domain from user message → conceptual question, no safeguard.

    # Engagement state stub (per spec).
    parts.append(
        "\n\n# Engagement State\n\n"
        "This is a new engagement session. No prior interaction history."
    )

    # Persona instruction — Maestra voice, not generic.
    parts.append(
        "\n\n# Response Instructions\n\n"
        "You are Maestra, the persistent AI engagement lead for the AutonomOS "
        "platform. Respond in your constitution voice: precise, knowledgeable, "
        "grounded in data. When citing data, reference the exact values, periods, "
        "and source systems from the triple store context above. Never fabricate "
        "numbers — if data is not in your context, say so. If a module context "
        "is provided, tailor your response to that module's domain."
    )

    system_prompt = "\n".join(parts)
    return system_prompt, domains, entity_id


async def assemble_prompt_async(
    message: str,
    module_context: str | None,
) -> tuple[str, list[str], str | None]:
    """Async wrapper around assemble_prompt (DB calls are sync/psycopg2)."""
    return await asyncio.to_thread(assemble_prompt, message, module_context)
