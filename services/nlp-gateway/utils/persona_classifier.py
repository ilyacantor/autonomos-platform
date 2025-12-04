"""
Persona classification logic for routing queries to appropriate services.
"""
from typing import Tuple, List


# Persona domain mappings
PERSONA_DOMAINS = {
    "cto": ["AOD", "AAM", "DCL", "Agents"],
    "cro": ["RevOps"],
    "coo": ["FinOps"],
    "cfo": []
}


# Keyword mappings for each persona
COO_KEYWORDS = [
    "spend", "budget", "variance", "invoice", "vendor", "renewal", "contract",
    "cost center", "unit cost", "savings plan", "reserved instances",
    "cloud bill", "finops", "compute", "storage", "network"
]

CFO_KEYWORDS = [
    "revenue", "arr", "mrr", "bookings", "churn", "gross margin", "ebitda",
    "p&l", "cash", "burn", "runway", "dso", "dpo", "working capital",
    "gaap", "audit", "forecast accuracy"
]

CRO_KEYWORDS = [
    "pipeline", "win rate", "deal", "quota", "forecast", "sales",
    "opportunity", "lead", "conversion", "close rate", "revenue ops",
    "crm", "customer", "churn", "retention", "expansion"
]

CTO_KEYWORDS = [
    "connector", "drift", "schema", "api", "service", "dependency",
    "health", "latency", "error rate", "sla", "uptime", "incident",
    "deployment", "infrastructure", "architecture", "ontology", "entity"
]


def classify_persona(query: str) -> Tuple[str, float, List[str]]:
    """
    Classify a query into one of four personas: CTO, CRO, COO, CFO.
    
    Returns:
        Tuple of (persona, confidence, matched_keywords)
    """
    query_lower = query.lower()
    
    # Count keyword matches for each persona
    scores = {
        "cto": _count_matches(query_lower, CTO_KEYWORDS),
        "cro": _count_matches(query_lower, CRO_KEYWORDS),
        "coo": _count_matches(query_lower, COO_KEYWORDS),
        "cfo": _count_matches(query_lower, CFO_KEYWORDS)
    }
    
    # Get matched keywords for each persona
    matched = {
        "cto": _get_matches(query_lower, CTO_KEYWORDS),
        "cro": _get_matches(query_lower, CRO_KEYWORDS),
        "coo": _get_matches(query_lower, COO_KEYWORDS),
        "cfo": _get_matches(query_lower, CFO_KEYWORDS)
    }
    
    # Find max score
    max_score = max(scores.values())
    
    if max_score == 0:
        # No keywords matched - default to CTO
        return ("cto", 0.3, [])
    
    # Get personas with max score
    top_personas = [p for p, s in scores.items() if s == max_score]
    
    # Tie-breaking logic for COO vs CFO
    if set(top_personas) == {"coo", "cfo"}:
        # Check for CFO priority keywords
        cfo_priority = ["ebitda", "cash", "burn", "runway", "dso", "dpo", "working capital", "p&l"]
        coo_priority = ["vendor", "renewal", "cloud", "budget", "finops", "cost center"]
        
        has_cfo_priority = any(kw in query_lower for kw in cfo_priority)
        has_coo_priority = any(kw in query_lower for kw in coo_priority)
        
        if has_cfo_priority:
            persona = "cfo"
        elif has_coo_priority:
            persona = "coo"
        else:
            # Default to COO if tied
            persona = "coo"
    else:
        # Pick first top persona (arbitrary but deterministic)
        persona = top_personas[0]
    
    # Calculate confidence based on match strength
    total_keywords = len(COO_KEYWORDS) + len(CFO_KEYWORDS) + len(CRO_KEYWORDS) + len(CTO_KEYWORDS)
    confidence = min(0.95, 0.6 + (max_score / total_keywords) * 2)
    
    return (persona, confidence, matched[persona])


def _count_matches(query: str, keywords: List[str]) -> int:
    """Count how many keywords appear in the query."""
    return sum(1 for kw in keywords if kw in query)


def _get_matches(query: str, keywords: List[str]) -> List[str]:
    """Get list of matched keywords."""
    return [kw for kw in keywords if kw in query]
