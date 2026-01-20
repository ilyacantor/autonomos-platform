"""
Semantic Field Explainer

LLM-augmented field explanation that combines:
- Schema metadata (types, constraints)
- Business context (descriptions, owners)
- Usage patterns (queries, dependencies)
- Lineage information (sources, transformations)

Part of "The Moat" - deep data understanding capabilities.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class FieldExplanation:
    """Comprehensive field explanation."""

    # Basic info
    field_name: str
    asset_id: str
    asset_name: str

    # Technical details
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None

    # Business context
    display_name: Optional[str] = None
    description: Optional[str] = None
    business_definition: Optional[str] = None
    calculation_logic: Optional[str] = None

    # Classification
    sensitivity: str = "low"  # low, medium, high
    pii_categories: list[str] = field(default_factory=list)
    regulations: list[str] = field(default_factory=list)

    # Source and ownership
    source_system: Optional[str] = None
    source_description: Optional[str] = None
    owner: Optional[str] = None
    steward: Optional[str] = None

    # Usage and quality
    usage_frequency: Optional[str] = None  # high, medium, low
    quality_score: Optional[float] = None
    null_percentage: Optional[float] = None
    distinct_values: Optional[int] = None
    sample_values: list[Any] = field(default_factory=list)

    # Relationships
    related_fields: list[str] = field(default_factory=list)
    used_in_calculations: list[str] = field(default_factory=list)
    dependent_assets: list[str] = field(default_factory=list)

    # LLM-generated explanation
    natural_language_explanation: Optional[str] = None
    suggested_questions: list[str] = field(default_factory=list)

    # Metadata
    last_updated: Optional[datetime] = None
    confidence_score: float = 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "field_name": self.field_name,
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "foreign_key": self.foreign_key,
            "display_name": self.display_name,
            "description": self.description,
            "business_definition": self.business_definition,
            "calculation_logic": self.calculation_logic,
            "sensitivity": self.sensitivity,
            "pii_categories": self.pii_categories,
            "regulations": self.regulations,
            "source_system": self.source_system,
            "source_description": self.source_description,
            "owner": self.owner,
            "steward": self.steward,
            "usage_frequency": self.usage_frequency,
            "quality_score": self.quality_score,
            "null_percentage": self.null_percentage,
            "distinct_values": self.distinct_values,
            "sample_values": self.sample_values,
            "related_fields": self.related_fields,
            "used_in_calculations": self.used_in_calculations,
            "dependent_assets": self.dependent_assets,
            "natural_language_explanation": self.natural_language_explanation,
            "suggested_questions": self.suggested_questions,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "confidence_score": self.confidence_score
        }


class SemanticFieldExplainer:
    """
    LLM-augmented field explanation service.

    Combines metadata from multiple sources with LLM-generated
    natural language explanations for comprehensive field understanding.
    """

    def __init__(
        self,
        ai_gateway: Optional[Any] = None,
        aod_server: Optional[Any] = None,
        dcl_server: Optional[Any] = None
    ):
        """
        Initialize the field explainer.

        Args:
            ai_gateway: AI gateway for LLM calls
            aod_server: AOD MCP server for asset metadata
            dcl_server: DCL MCP server for schema info
        """
        self.ai_gateway = ai_gateway
        self.aod_server = aod_server
        self.dcl_server = dcl_server

        # Cache for explanations
        self._cache: dict[str, FieldExplanation] = {}

    async def explain_field(
        self,
        asset_id: str,
        field_name: str,
        tenant_id: UUID,
        include_llm_explanation: bool = True,
        include_samples: bool = False
    ) -> FieldExplanation:
        """
        Generate a comprehensive field explanation.

        Args:
            asset_id: Asset containing the field
            field_name: Name of the field to explain
            tenant_id: Tenant ID for access control
            include_llm_explanation: Whether to generate LLM explanation
            include_samples: Whether to include sample values

        Returns:
            Comprehensive FieldExplanation
        """
        cache_key = f"{tenant_id}:{asset_id}:{field_name}"

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Return cached if less than 1 hour old
            if cached.last_updated:
                age = (datetime.utcnow() - cached.last_updated).total_seconds()
                if age < 3600:
                    return cached

        logger.info(f"Generating explanation for {asset_id}.{field_name}")

        # Gather metadata from multiple sources
        metadata = await self._gather_metadata(
            asset_id, field_name, tenant_id, include_samples
        )

        # Build base explanation
        explanation = self._build_explanation(asset_id, field_name, metadata)

        # Add LLM-generated explanation if requested
        if include_llm_explanation and self.ai_gateway:
            await self._add_llm_explanation(explanation, metadata)

        # Cache result
        explanation.last_updated = datetime.utcnow()
        self._cache[cache_key] = explanation

        return explanation

    async def _gather_metadata(
        self,
        asset_id: str,
        field_name: str,
        tenant_id: UUID,
        include_samples: bool
    ) -> dict:
        """Gather metadata from all available sources."""
        metadata = {
            "asset": None,
            "field_schema": None,
            "quality": None,
            "lineage": None,
            "usage": None
        }

        # Get asset details from AOD
        if self.aod_server:
            try:
                from app.agentic.mcp_servers.aod_server import AODContext
                context = AODContext(tenant_id=tenant_id)

                # Get asset details
                asset_result = await self.aod_server.execute_tool(
                    "aod_get_asset_details",
                    {"asset_id": asset_id},
                    context
                )
                if asset_result.get("success"):
                    metadata["asset"] = asset_result.get("asset")

                # Get field explanation from AOD
                field_result = await self.aod_server.execute_tool(
                    "aod_explain_field",
                    {"asset_id": asset_id, "field_name": field_name},
                    context
                )
                if field_result.get("success"):
                    metadata["field_schema"] = field_result.get("explanation")

                # Get quality metrics
                quality_result = await self.aod_server.execute_tool(
                    "aod_get_data_quality",
                    {"asset_id": asset_id},
                    context
                )
                if quality_result.get("success"):
                    metadata["quality"] = quality_result.get("quality")

                # Get lineage
                lineage_result = await self.aod_server.execute_tool(
                    "aod_get_lineage",
                    {"asset_id": asset_id, "direction": "both", "depth": 1},
                    context
                )
                if lineage_result.get("success"):
                    metadata["lineage"] = lineage_result.get("lineage")

            except Exception as e:
                logger.warning(f"Error gathering AOD metadata: {e}")

        # Get additional schema info from DCL
        if self.dcl_server:
            try:
                from app.agentic.mcp_servers.dcl_server import DCLContext
                dcl_context = DCLContext(tenant_id=tenant_id)

                # Search for field info
                search_result = await self.dcl_server.execute_tool(
                    "dcl_search_fields",
                    {"query": field_name, "limit": 5},
                    dcl_context
                )
                if search_result.get("success"):
                    metadata["usage"] = search_result.get("fields")

            except Exception as e:
                logger.warning(f"Error gathering DCL metadata: {e}")

        return metadata

    def _build_explanation(
        self,
        asset_id: str,
        field_name: str,
        metadata: dict
    ) -> FieldExplanation:
        """Build explanation from gathered metadata."""
        asset = metadata.get("asset") or {}
        field_schema = metadata.get("field_schema") or {}
        quality = metadata.get("quality") or {}
        lineage = metadata.get("lineage") or {}

        # Extract asset info
        asset_name = asset.get("name", asset_id)
        source_system = asset.get("source_system", "unknown")
        owner = asset.get("owner")

        # Extract field info
        data_type = field_schema.get("data_type", "unknown")
        description = field_schema.get("description")
        business_definition = field_schema.get("business_definition")
        calculation_logic = field_schema.get("calculation")
        sensitivity = field_schema.get("sensitivity", "low")

        # Extract quality info
        quality_score = quality.get("overall_score")

        # Extract lineage info
        dependent_assets = []
        for downstream in lineage.get("downstream", []):
            dependent_assets.append(downstream.get("name", downstream.get("id")))

        return FieldExplanation(
            field_name=field_name,
            asset_id=asset_id,
            asset_name=asset_name,
            data_type=data_type,
            display_name=field_schema.get("display_name"),
            description=description,
            business_definition=business_definition,
            calculation_logic=calculation_logic,
            sensitivity=sensitivity,
            source_system=source_system,
            source_description=field_schema.get("source"),
            owner=owner,
            quality_score=quality_score,
            related_fields=field_schema.get("related_fields", []),
            dependent_assets=dependent_assets
        )

    async def _add_llm_explanation(
        self,
        explanation: FieldExplanation,
        metadata: dict
    ) -> None:
        """Add LLM-generated natural language explanation."""
        if not self.ai_gateway:
            return

        # Build context for LLM
        context_parts = [
            f"Field: {explanation.field_name}",
            f"Asset: {explanation.asset_name}",
            f"Data Type: {explanation.data_type}",
        ]

        if explanation.description:
            context_parts.append(f"Description: {explanation.description}")
        if explanation.business_definition:
            context_parts.append(f"Business Definition: {explanation.business_definition}")
        if explanation.calculation_logic:
            context_parts.append(f"Calculation: {explanation.calculation_logic}")
        if explanation.source_system:
            context_parts.append(f"Source: {explanation.source_system}")
        if explanation.sensitivity != "low":
            context_parts.append(f"Sensitivity: {explanation.sensitivity}")
        if explanation.related_fields:
            context_parts.append(f"Related Fields: {', '.join(explanation.related_fields)}")

        context = "\n".join(context_parts)

        prompt = f"""Based on the following field metadata, provide:
1. A clear, non-technical explanation of what this field represents (2-3 sentences)
2. Three questions a business user might ask about this field

Field Context:
{context}

Format your response as:
EXPLANATION: [your explanation]
QUESTIONS:
1. [question 1]
2. [question 2]
3. [question 3]"""

        try:
            response = await self.ai_gateway.quick_complete(
                prompt=prompt,
                model_tier="fast"
            )

            # Parse response
            lines = response.strip().split("\n")
            explanation_text = ""
            questions = []
            in_questions = False

            for line in lines:
                if line.startswith("EXPLANATION:"):
                    explanation_text = line.replace("EXPLANATION:", "").strip()
                elif line.startswith("QUESTIONS:"):
                    in_questions = True
                elif in_questions and line.strip():
                    # Remove number prefix
                    q = line.strip()
                    if q[0].isdigit() and len(q) > 2:
                        q = q[2:].strip()
                    if q:
                        questions.append(q)

            explanation.natural_language_explanation = explanation_text
            explanation.suggested_questions = questions[:3]

        except Exception as e:
            logger.warning(f"Error generating LLM explanation: {e}")

    async def batch_explain(
        self,
        asset_id: str,
        field_names: list[str],
        tenant_id: UUID,
        include_llm_explanation: bool = True
    ) -> list[FieldExplanation]:
        """
        Explain multiple fields from the same asset.

        Args:
            asset_id: Asset containing the fields
            field_names: List of field names to explain
            tenant_id: Tenant ID for access control
            include_llm_explanation: Whether to generate LLM explanations

        Returns:
            List of FieldExplanation objects
        """
        explanations = []

        for field_name in field_names:
            try:
                explanation = await self.explain_field(
                    asset_id=asset_id,
                    field_name=field_name,
                    tenant_id=tenant_id,
                    include_llm_explanation=include_llm_explanation
                )
                explanations.append(explanation)
            except Exception as e:
                logger.error(f"Error explaining {field_name}: {e}")
                # Create minimal explanation on error
                explanations.append(FieldExplanation(
                    field_name=field_name,
                    asset_id=asset_id,
                    asset_name=asset_id,
                    data_type="unknown",
                    description=f"Error: {str(e)}",
                    confidence_score=0.0
                ))

        return explanations

    def clear_cache(self, tenant_id: Optional[UUID] = None) -> int:
        """
        Clear cached explanations.

        Args:
            tenant_id: Only clear cache for this tenant (None = all)

        Returns:
            Number of entries cleared
        """
        if tenant_id is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        prefix = f"{tenant_id}:"
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)


# Global instance
_field_explainer: Optional[SemanticFieldExplainer] = None


def get_field_explainer() -> SemanticFieldExplainer:
    """Get the global field explainer instance."""
    global _field_explainer
    if _field_explainer is None:
        _field_explainer = SemanticFieldExplainer()
    return _field_explainer
