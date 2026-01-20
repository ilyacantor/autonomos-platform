"""
Cost Tracker

Tracks and calculates LLM API costs per model and provider.
Provides cost estimation and budget enforcement.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ModelPricing:
    """Pricing for a specific model."""
    model_id: str
    input_cost_per_million: float  # USD per 1M input tokens
    output_cost_per_million: float  # USD per 1M output tokens
    provider: str


# Pricing table (as of Jan 2026, update as needed)
MODEL_PRICING: dict[str, ModelPricing] = {
    # Anthropic Claude
    "claude-3-5-haiku-20241022": ModelPricing(
        model_id="claude-3-5-haiku-20241022",
        input_cost_per_million=0.80,
        output_cost_per_million=4.00,
        provider="anthropic"
    ),
    "claude-sonnet-4-20250514": ModelPricing(
        model_id="claude-sonnet-4-20250514",
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        provider="anthropic"
    ),
    "claude-opus-4-20250514": ModelPricing(
        model_id="claude-opus-4-20250514",
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        provider="anthropic"
    ),
    # Legacy Claude models
    "claude-3-haiku-20240307": ModelPricing(
        model_id="claude-3-haiku-20240307",
        input_cost_per_million=0.25,
        output_cost_per_million=1.25,
        provider="anthropic"
    ),
    "claude-3-5-sonnet-20241022": ModelPricing(
        model_id="claude-3-5-sonnet-20241022",
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        provider="anthropic"
    ),
    # OpenAI GPT-4
    "gpt-4o": ModelPricing(
        model_id="gpt-4o",
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
        provider="openai"
    ),
    "gpt-4o-mini": ModelPricing(
        model_id="gpt-4o-mini",
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        provider="openai"
    ),
    "gpt-4-turbo": ModelPricing(
        model_id="gpt-4-turbo",
        input_cost_per_million=10.00,
        output_cost_per_million=30.00,
        provider="openai"
    ),
}


@dataclass
class UsageRecord:
    """Record of a single LLM call."""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    run_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None


class CostTracker:
    """
    Tracks LLM costs across runs and tenants.

    Features:
    - Per-call cost calculation
    - Aggregated cost tracking
    - Budget enforcement
    - Usage reporting
    """

    def __init__(self):
        self._usage_records: list[UsageRecord] = []
        self._budget_limits: dict[UUID, float] = {}  # tenant_id -> max USD

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate the cost for a single LLM call.

        Args:
            model: Model ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = MODEL_PRICING.get(model)

        if not pricing:
            # Try partial match
            for model_id, p in MODEL_PRICING.items():
                if model_id in model or model in model_id:
                    pricing = p
                    break

        if not pricing:
            logger.warning(f"Unknown model for pricing: {model}, using default")
            # Default to Sonnet pricing
            pricing = MODEL_PRICING.get("claude-sonnet-4-20250514")

        if not pricing:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_million

        return input_cost + output_cost

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Optional[float] = None,
        run_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None
    ) -> UsageRecord:
        """
        Record a usage event.

        Args:
            model: Model used
            input_tokens: Input token count
            output_tokens: Output token count
            cost_usd: Pre-calculated cost (or will calculate)
            run_id: Associated run ID
            tenant_id: Associated tenant ID

        Returns:
            UsageRecord created
        """
        if cost_usd is None:
            cost_usd = self.calculate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            timestamp=datetime.utcnow(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            run_id=run_id,
            tenant_id=tenant_id
        )

        self._usage_records.append(record)
        return record

    def set_budget_limit(self, tenant_id: UUID, max_usd: float):
        """Set a budget limit for a tenant."""
        self._budget_limits[tenant_id] = max_usd

    def get_budget_remaining(self, tenant_id: UUID) -> Optional[float]:
        """Get remaining budget for a tenant."""
        limit = self._budget_limits.get(tenant_id)
        if limit is None:
            return None

        spent = self.get_tenant_cost(tenant_id)
        return max(0, limit - spent)

    def check_budget(self, tenant_id: UUID, estimated_cost: float) -> bool:
        """
        Check if a tenant has budget for an estimated cost.

        Returns True if OK to proceed, False if would exceed budget.
        """
        remaining = self.get_budget_remaining(tenant_id)
        if remaining is None:
            return True  # No limit set

        return estimated_cost <= remaining

    def get_tenant_cost(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None
    ) -> float:
        """Get total cost for a tenant."""
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)  # Default: last 30 days

        return sum(
            r.cost_usd for r in self._usage_records
            if r.tenant_id == tenant_id and r.timestamp >= since
        )

    def get_run_cost(self, run_id: UUID) -> float:
        """Get total cost for a specific run."""
        return sum(
            r.cost_usd for r in self._usage_records
            if r.run_id == run_id
        )

    def get_usage_summary(
        self,
        tenant_id: Optional[UUID] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> dict:
        """
        Get aggregated usage summary.

        Args:
            tenant_id: Filter by tenant (None for all)
            since: Start time filter
            until: End time filter

        Returns:
            Summary dict with totals and breakdowns
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)
        if until is None:
            until = datetime.utcnow()

        # Filter records
        records = [
            r for r in self._usage_records
            if r.timestamp >= since and r.timestamp <= until
            and (tenant_id is None or r.tenant_id == tenant_id)
        ]

        # Aggregate
        total_cost = sum(r.cost_usd for r in records)
        total_input_tokens = sum(r.input_tokens for r in records)
        total_output_tokens = sum(r.output_tokens for r in records)

        # By model
        by_model: dict[str, dict] = {}
        for r in records:
            if r.model not in by_model:
                by_model[r.model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0
                }
            by_model[r.model]["calls"] += 1
            by_model[r.model]["input_tokens"] += r.input_tokens
            by_model[r.model]["output_tokens"] += r.output_tokens
            by_model[r.model]["cost_usd"] += r.cost_usd

        return {
            "period": {
                "since": since.isoformat(),
                "until": until.isoformat()
            },
            "total": {
                "calls": len(records),
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost
            },
            "by_model": by_model
        }

    def estimate_cost(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> float:
        """
        Estimate cost before making a call.

        Useful for budget checks and UI display.
        """
        return self.calculate_cost(model, estimated_input_tokens, estimated_output_tokens)

    def clear_records(self, older_than: Optional[datetime] = None):
        """
        Clear usage records.

        Args:
            older_than: Only clear records older than this (None = all)
        """
        if older_than:
            self._usage_records = [
                r for r in self._usage_records
                if r.timestamp >= older_than
            ]
        else:
            self._usage_records = []


# Global cost tracker
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
