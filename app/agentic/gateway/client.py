"""
AI Gateway Client

Unified LLM access layer supporting:
- Direct Anthropic API calls
- Portkey AI Gateway (optional)
- Automatic fallback to OpenAI
- Request/response logging
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    PORTKEY = "portkey"


class ModelTier(str, Enum):
    """Model tiers by capability/cost."""
    FAST = "fast"      # Haiku - routing, simple tasks
    BALANCED = "balanced"  # Sonnet - most tasks
    POWERFUL = "powerful"  # Opus - complex reasoning


# Model mappings
ANTHROPIC_MODELS = {
    ModelTier.FAST: "claude-3-5-haiku-20241022",
    ModelTier.BALANCED: "claude-sonnet-4-20250514",
    ModelTier.POWERFUL: "claude-opus-4-20250514",
}

OPENAI_MODELS = {
    ModelTier.FAST: "gpt-4o-mini",
    ModelTier.BALANCED: "gpt-4o",
    ModelTier.POWERFUL: "gpt-4o",
}


@dataclass
class GatewayConfig:
    """Configuration for the AI Gateway."""
    # Provider settings
    primary_provider: LLMProvider = LLMProvider.ANTHROPIC
    fallback_provider: Optional[LLMProvider] = LLMProvider.OPENAI

    # API keys (from env if not provided)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    portkey_api_key: Optional[str] = None

    # Portkey settings
    portkey_virtual_key: Optional[str] = None

    # Defaults
    default_model_tier: ModelTier = ModelTier.BALANCED
    default_max_tokens: int = 4096
    default_temperature: float = 0.7

    # Timeouts and retries
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Caching
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600

    def __post_init__(self):
        # Load from environment if not provided
        self.anthropic_api_key = self.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.portkey_api_key = self.portkey_api_key or os.getenv("PORTKEY_API_KEY")


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    content: str
    model: str
    provider: LLMProvider

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0

    # Cost (calculated)
    cost_usd: float = 0.0

    # Metadata
    latency_ms: int = 0
    cached: bool = False

    # Tool calls (if any)
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"

    # Raw response for debugging
    raw_response: Optional[dict] = None


class AIGateway:
    """
    Unified AI Gateway for LLM access.

    Features:
    - Multi-provider support (Anthropic, OpenAI, Portkey)
    - Automatic fallback on failure
    - Cost tracking
    - Optional semantic caching
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self._anthropic_client = None
        self._openai_client = None
        self._portkey_client = None
        self._cache = None
        self._cost_tracker = None

    async def initialize(self):
        """Initialize clients based on configuration."""
        if self.config.primary_provider == LLMProvider.ANTHROPIC or \
           self.config.fallback_provider == LLMProvider.ANTHROPIC:
            await self._init_anthropic()

        if self.config.primary_provider == LLMProvider.OPENAI or \
           self.config.fallback_provider == LLMProvider.OPENAI:
            await self._init_openai()

        if self.config.primary_provider == LLMProvider.PORTKEY:
            await self._init_portkey()

        if self.config.enable_cache:
            from app.agentic.gateway.cache import SemanticCache
            self._cache = SemanticCache(ttl_seconds=self.config.cache_ttl_seconds)

        from app.agentic.gateway.cost import CostTracker
        self._cost_tracker = CostTracker()

    async def _init_anthropic(self):
        """Initialize Anthropic client."""
        if not self.config.anthropic_api_key:
            logger.warning("Anthropic API key not configured")
            return

        try:
            import anthropic
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=self.config.anthropic_api_key
            )
            logger.info("Anthropic client initialized")
        except ImportError:
            logger.warning("anthropic package not installed")

    async def _init_openai(self):
        """Initialize OpenAI client."""
        if not self.config.openai_api_key:
            logger.warning("OpenAI API key not configured")
            return

        try:
            import openai
            self._openai_client = openai.AsyncOpenAI(
                api_key=self.config.openai_api_key
            )
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.warning("openai package not installed")

    async def _init_portkey(self):
        """Initialize Portkey client."""
        if not self.config.portkey_api_key:
            logger.warning("Portkey API key not configured")
            return

        try:
            from portkey_ai import AsyncPortkey
            self._portkey_client = AsyncPortkey(
                api_key=self.config.portkey_api_key,
                virtual_key=self.config.portkey_virtual_key
            )
            logger.info("Portkey client initialized")
        except ImportError:
            logger.warning("portkey-ai package not installed")

    async def complete(
        self,
        messages: list[dict],
        model_tier: Optional[ModelTier] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[list[dict]] = None,
        system: Optional[str] = None,
        use_cache: bool = True,
    ) -> LLMResponse:
        """
        Complete a conversation with the LLM.

        Args:
            messages: Conversation messages
            model_tier: Model tier to use (fast/balanced/powerful)
            model: Specific model override
            max_tokens: Max output tokens
            temperature: Sampling temperature
            tools: Available tools
            system: System prompt
            use_cache: Whether to use semantic cache

        Returns:
            LLMResponse with completion
        """
        model_tier = model_tier or self.config.default_model_tier
        max_tokens = max_tokens or self.config.default_max_tokens
        temperature = temperature if temperature is not None else self.config.default_temperature

        # Check cache
        if use_cache and self._cache and not tools:
            cached = await self._cache.get(messages, system)
            if cached:
                cached.cached = True
                return cached

        # Try primary provider
        start_time = datetime.utcnow()
        response = None

        try:
            response = await self._call_provider(
                self.config.primary_provider,
                messages=messages,
                model_tier=model_tier,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
                system=system,
            )
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")

            # Try fallback
            if self.config.fallback_provider:
                try:
                    response = await self._call_provider(
                        self.config.fallback_provider,
                        messages=messages,
                        model_tier=model_tier,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        tools=tools,
                        system=system,
                    )
                except Exception as e2:
                    logger.error(f"Fallback provider also failed: {e2}")
                    raise

        if response is None:
            raise RuntimeError("No LLM providers available")

        # Calculate latency
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        response.latency_ms = latency_ms

        # Track cost
        if self._cost_tracker:
            response.cost_usd = self._cost_tracker.calculate_cost(
                response.model,
                response.input_tokens,
                response.output_tokens
            )

        # Cache response
        if use_cache and self._cache and not tools and response.stop_reason != "tool_use":
            await self._cache.put(messages, system, response)

        return response

    async def _call_provider(
        self,
        provider: LLMProvider,
        messages: list[dict],
        model_tier: ModelTier,
        model: Optional[str],
        max_tokens: int,
        temperature: float,
        tools: Optional[list[dict]],
        system: Optional[str],
    ) -> LLMResponse:
        """Call a specific LLM provider."""
        if provider == LLMProvider.ANTHROPIC:
            return await self._call_anthropic(
                messages, model_tier, model, max_tokens, temperature, tools, system
            )
        elif provider == LLMProvider.OPENAI:
            return await self._call_openai(
                messages, model_tier, model, max_tokens, temperature, tools, system
            )
        elif provider == LLMProvider.PORTKEY:
            return await self._call_portkey(
                messages, model_tier, model, max_tokens, temperature, tools, system
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_anthropic(
        self,
        messages: list[dict],
        model_tier: ModelTier,
        model: Optional[str],
        max_tokens: int,
        temperature: float,
        tools: Optional[list[dict]],
        system: Optional[str],
    ) -> LLMResponse:
        """Call Anthropic API."""
        if not self._anthropic_client:
            raise RuntimeError("Anthropic client not initialized")

        model_name = model or ANTHROPIC_MODELS[model_tier]

        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        response = await self._anthropic_client.messages.create(**kwargs)

        # Parse response
        content = ""
        tool_calls = []

        for block in response.content:
            if hasattr(block, 'text'):
                content = block.text
            elif hasattr(block, 'type') and block.type == 'tool_use':
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return LLMResponse(
            content=content,
            model=model_name,
            provider=LLMProvider.ANTHROPIC,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
        )

    async def _call_openai(
        self,
        messages: list[dict],
        model_tier: ModelTier,
        model: Optional[str],
        max_tokens: int,
        temperature: float,
        tools: Optional[list[dict]],
        system: Optional[str],
    ) -> LLMResponse:
        """Call OpenAI API."""
        if not self._openai_client:
            raise RuntimeError("OpenAI client not initialized")

        model_name = model or OPENAI_MODELS[model_tier]

        # Convert messages format
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            oai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": oai_messages,
        }

        if tools:
            # Convert to OpenAI tool format
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", t.get("inputSchema", {}))
                    }
                }
                for t in tools
            ]

        response = await self._openai_client.chat.completions.create(**kwargs)

        # Parse response
        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": tc.function.arguments
                })

        return LLMResponse(
            content=content,
            model=model_name,
            provider=LLMProvider.OPENAI,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
        )

    async def _call_portkey(
        self,
        messages: list[dict],
        model_tier: ModelTier,
        model: Optional[str],
        max_tokens: int,
        temperature: float,
        tools: Optional[list[dict]],
        system: Optional[str],
    ) -> LLMResponse:
        """Call via Portkey gateway."""
        if not self._portkey_client:
            raise RuntimeError("Portkey client not initialized")

        # Portkey uses Anthropic format by default
        model_name = model or ANTHROPIC_MODELS[model_tier]

        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        response = await self._portkey_client.chat.completions.create(**kwargs)

        # Parse similar to Anthropic
        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            model=model_name,
            provider=LLMProvider.PORTKEY,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            stop_reason="end_turn",
        )

    async def quick_complete(
        self,
        prompt: str,
        model_tier: ModelTier = ModelTier.FAST,
        system: Optional[str] = None,
    ) -> str:
        """
        Quick single-turn completion (for routing, classification, etc.)

        Uses fast model tier by default for low latency.
        """
        response = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            model_tier=model_tier,
            system=system,
            use_cache=True,
        )
        return response.content


# Global gateway instance
_gateway: Optional[AIGateway] = None


async def get_ai_gateway() -> AIGateway:
    """Get or create the global AI Gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
        await _gateway.initialize()
    return _gateway
