"""
AI Gateway Module

Unified LLM access with:
- Multi-provider routing (Anthropic, OpenAI fallback)
- Semantic caching
- Cost tracking
- Reasoning router for smart request planning
"""

from app.agentic.gateway.client import (
    AIGateway,
    GatewayConfig,
    LLMResponse,
    get_ai_gateway,
)
from app.agentic.gateway.router import (
    ReasoningRouter,
    RoutingPlan,
    RoutingStep,
    get_reasoning_router,
)
from app.agentic.gateway.cache import SemanticCache
from app.agentic.gateway.cost import CostTracker, ModelPricing, get_cost_tracker

__all__ = [
    'AIGateway',
    'GatewayConfig',
    'LLMResponse',
    'get_ai_gateway',
    'ReasoningRouter',
    'RoutingPlan',
    'RoutingStep',
    'get_reasoning_router',
    'SemanticCache',
    'CostTracker',
    'ModelPricing',
    'get_cost_tracker',
]
