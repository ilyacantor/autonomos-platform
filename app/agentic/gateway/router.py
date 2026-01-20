"""
Reasoning Router

LLM-based request routing that:
- Analyzes user queries
- Plans execution steps
- Selects appropriate tools
- Handles compound/multi-step tasks

Replaces brittle intent classification with dynamic reasoning.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    """Complexity level of a task."""
    SIMPLE = "simple"      # Single tool call
    MODERATE = "moderate"  # 2-3 steps
    COMPLEX = "complex"    # 4+ steps or branching


class TaskCategory(str, Enum):
    """High-level task categories."""
    QUERY_DATA = "query_data"
    MANAGE_CONNECTIONS = "manage_connections"
    ANALYZE = "analyze"
    EXPLAIN = "explain"
    ACTION = "action"
    CLARIFY = "clarify"


@dataclass
class RoutingStep:
    """A single step in the execution plan."""
    step_number: int
    description: str
    tool_name: Optional[str] = None
    tool_arguments: dict = field(default_factory=dict)
    requires_approval: bool = False
    depends_on: list[int] = field(default_factory=list)
    conditional: Optional[str] = None  # e.g., "if previous step failed"


@dataclass
class RoutingPlan:
    """Complete execution plan for a request."""
    query: str
    category: TaskCategory
    complexity: TaskComplexity
    steps: list[RoutingStep]
    clarification_needed: Optional[str] = None
    estimated_cost_usd: float = 0.0
    reasoning: str = ""


ROUTING_SYSTEM_PROMPT = """You are a routing assistant for the AOS (autonomOS) data platform.
Your job is to analyze user requests and create execution plans.

Available tools:
{tools}

Guidelines:
1. For simple queries, plan 1-2 steps
2. For complex queries, break into logical steps
3. If the request is ambiguous, ask for clarification
4. Mark steps that modify data as requiring approval
5. Estimate total cost based on tools used

Respond with a JSON execution plan:
{{
  "category": "query_data|manage_connections|analyze|explain|action|clarify",
  "complexity": "simple|moderate|complex",
  "clarification_needed": null or "question to ask user",
  "reasoning": "brief explanation of your plan",
  "steps": [
    {{
      "step_number": 1,
      "description": "what this step does",
      "tool_name": "tool to use or null",
      "tool_arguments": {{}},
      "requires_approval": false,
      "depends_on": [],
      "conditional": null
    }}
  ]
}}"""


class ReasoningRouter:
    """
    LLM-based reasoning router for intelligent request planning.

    Uses a fast model (Haiku) to analyze requests and create execution plans.
    """

    def __init__(self, gateway=None):
        """
        Initialize the router.

        Args:
            gateway: AIGateway instance (or will use global)
        """
        self._gateway = gateway
        self._tools_cache: list[dict] = []

    async def _get_gateway(self):
        """Get AI Gateway instance."""
        if self._gateway:
            return self._gateway
        from app.agentic.gateway.client import get_ai_gateway
        return await get_ai_gateway()

    def register_tools(self, tools: list[dict]):
        """
        Register available tools for routing decisions.

        Args:
            tools: List of tool definitions (name, description, inputSchema)
        """
        self._tools_cache = tools

    async def route(
        self,
        query: str,
        tools: Optional[list[dict]] = None,
        context: Optional[dict] = None
    ) -> RoutingPlan:
        """
        Analyze a query and create an execution plan.

        Args:
            query: User's natural language query
            tools: Available tools (uses cached if not provided)
            context: Optional context (previous queries, user preferences)

        Returns:
            RoutingPlan with steps to execute
        """
        tools = tools or self._tools_cache

        if not tools:
            logger.warning("No tools registered for routing")
            return RoutingPlan(
                query=query,
                category=TaskCategory.CLARIFY,
                complexity=TaskComplexity.SIMPLE,
                steps=[],
                clarification_needed="No tools available to handle this request."
            )

        # Format tools for prompt
        tools_description = self._format_tools(tools)

        # Build system prompt
        system = ROUTING_SYSTEM_PROMPT.format(tools=tools_description)

        # Build user message
        user_message = f"User request: {query}"
        if context:
            user_message += f"\n\nContext: {json.dumps(context)}"

        # Call fast model for routing
        gateway = await self._get_gateway()
        from app.agentic.gateway.client import ModelTier

        try:
            response = await gateway.complete(
                messages=[{"role": "user", "content": user_message}],
                model_tier=ModelTier.FAST,  # Use Haiku for speed
                system=system,
                temperature=0.3,  # Lower temperature for more consistent routing
                max_tokens=1024,
            )

            # Parse response
            plan = self._parse_routing_response(query, response.content)
            plan.estimated_cost_usd = response.cost_usd

            return plan

        except Exception as e:
            logger.error(f"Routing failed: {e}")
            # Return a safe fallback plan
            return RoutingPlan(
                query=query,
                category=TaskCategory.CLARIFY,
                complexity=TaskComplexity.SIMPLE,
                steps=[],
                clarification_needed=f"I encountered an error understanding your request: {str(e)}"
            )

    def _format_tools(self, tools: list[dict]) -> str:
        """Format tools for the routing prompt."""
        lines = []
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "No description")
            schema = tool.get("inputSchema", tool.get("input_schema", {}))
            props = schema.get("properties", {})

            param_str = ", ".join(
                f"{k}: {v.get('type', 'any')}"
                for k, v in props.items()
            )

            lines.append(f"- {name}({param_str}): {desc}")

        return "\n".join(lines)

    def _parse_routing_response(self, query: str, response: str) -> RoutingPlan:
        """Parse the LLM's routing response into a RoutingPlan."""
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            # Parse steps
            steps = []
            for step_data in data.get("steps", []):
                step = RoutingStep(
                    step_number=step_data.get("step_number", len(steps) + 1),
                    description=step_data.get("description", ""),
                    tool_name=step_data.get("tool_name"),
                    tool_arguments=step_data.get("tool_arguments", {}),
                    requires_approval=step_data.get("requires_approval", False),
                    depends_on=step_data.get("depends_on", []),
                    conditional=step_data.get("conditional"),
                )
                steps.append(step)

            return RoutingPlan(
                query=query,
                category=TaskCategory(data.get("category", "query_data")),
                complexity=TaskComplexity(data.get("complexity", "simple")),
                steps=steps,
                clarification_needed=data.get("clarification_needed"),
                reasoning=data.get("reasoning", ""),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse routing response: {e}")
            # Return a generic plan
            return RoutingPlan(
                query=query,
                category=TaskCategory.QUERY_DATA,
                complexity=TaskComplexity.SIMPLE,
                steps=[
                    RoutingStep(
                        step_number=1,
                        description="Process user request",
                        tool_name=None,
                    )
                ],
                reasoning=f"Parse failed, using generic plan. Original response: {response[:200]}"
            )

    async def should_clarify(self, query: str) -> Optional[str]:
        """
        Quick check if clarification is needed before routing.

        Returns clarification question or None if query is clear.
        """
        gateway = await self._get_gateway()
        from app.agentic.gateway.client import ModelTier

        prompt = f"""Is this request clear enough to execute, or does it need clarification?
Request: "{query}"

If clear, respond with: CLEAR
If clarification needed, respond with: CLARIFY: <your question>

Keep your response very short."""

        response = await gateway.quick_complete(prompt, model_tier=ModelTier.FAST)

        if response.strip().upper().startswith("CLEAR"):
            return None
        elif response.strip().upper().startswith("CLARIFY:"):
            return response.split(":", 1)[1].strip()
        else:
            return None

    async def classify_intent(self, query: str) -> TaskCategory:
        """
        Quick intent classification without full routing.

        Useful for pre-filtering or UI hints.
        """
        gateway = await self._get_gateway()
        from app.agentic.gateway.client import ModelTier

        prompt = f"""Classify this request into one category:
- query_data: Asking about data, metrics, reports
- manage_connections: Managing data sources/connections
- analyze: Deep analysis or investigation
- explain: Asking for explanations
- action: Requesting to take an action
- clarify: Request is unclear

Request: "{query}"

Respond with just the category name."""

        response = await gateway.quick_complete(prompt, model_tier=ModelTier.FAST)

        try:
            return TaskCategory(response.strip().lower())
        except ValueError:
            return TaskCategory.QUERY_DATA


# Global router instance
_router: Optional[ReasoningRouter] = None


async def get_reasoning_router() -> ReasoningRouter:
    """Get or create the global reasoning router."""
    global _router
    if _router is None:
        _router = ReasoningRouter()
    return _router
