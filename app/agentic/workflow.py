"""
LangGraph Workflow Builder

Compiles agent definitions into executable LangGraph workflows.
Integrates with MCP tools and handles human-in-the-loop approvals.
"""

import asyncio
import fnmatch
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypedDict
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class AgentState(TypedDict, total=False):
    """State passed through the LangGraph workflow."""
    messages: list[dict]
    input: str
    output: Optional[str]
    current_step: int
    max_steps: int
    tools_called: list[dict]
    tokens_input: int
    tokens_output: int
    cost_usd: float
    pending_approval: Optional[dict]
    error: Optional[str]
    metadata: dict


@dataclass
class ToolDefinition:
    """Definition of a tool available to an agent."""
    name: str
    description: str
    mcp_server: str
    input_schema: dict = field(default_factory=dict)
    requires_approval: bool = False
    forbidden: bool = False


@dataclass
class WorkflowConfig:
    """Configuration for building a workflow."""
    agent_id: UUID
    tenant_id: UUID
    run_id: UUID
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096
    max_steps: int = 20
    max_cost_usd: float = 1.0
    system_prompt: Optional[str] = None
    tools: list[ToolDefinition] = field(default_factory=list)
    require_approval_for: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    on_tool_call: Optional[Callable] = None
    on_approval_required: Optional[Callable] = None
    on_step_complete: Optional[Callable] = None


# =============================================================================
# Workflow Builder
# =============================================================================

class WorkflowBuilder:
    """
    Builds LangGraph workflows from agent configurations.

    This is a framework that will integrate with LangGraph when available.
    For now, it provides the structural foundation for agent execution.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize the workflow builder.

        Args:
            llm_client: Anthropic client or compatible LLM client
        """
        self.llm_client = llm_client

    def build(self, config: WorkflowConfig) -> "AgentWorkflow":
        """
        Build an executable workflow from configuration.

        Args:
            config: Workflow configuration

        Returns:
            AgentWorkflow instance ready for execution
        """
        return AgentWorkflow(config, self.llm_client)


class AgentWorkflow:
    """
    Executable agent workflow.

    Manages the agent execution loop with:
    - Tool calling via MCP
    - Human-in-the-loop approvals
    - Cost and step tracking
    - Checkpoint integration
    """

    def __init__(self, config: WorkflowConfig, llm_client: Optional[Any] = None):
        self.config = config
        self.llm_client = llm_client
        self._state: AgentState = {
            "messages": [],
            "input": "",
            "output": None,
            "current_step": 0,
            "max_steps": config.max_steps,
            "tools_called": [],
            "tokens_input": 0,
            "tokens_output": 0,
            "cost_usd": 0.0,
            "pending_approval": None,
            "error": None,
            "metadata": {}
        }

    @property
    def state(self) -> AgentState:
        """Get current workflow state."""
        return self._state.copy()

    async def run(self, input_text: str, context: Optional[dict] = None) -> AgentState:
        """
        Execute the workflow with the given input.

        Args:
            input_text: User input/query
            context: Optional additional context

        Returns:
            Final workflow state
        """
        self._state["input"] = input_text
        self._state["messages"] = [
            {"role": "user", "content": input_text}
        ]

        if context:
            self._state["metadata"]["context"] = context

        logger.info(f"Starting workflow for run {self.config.run_id}")

        try:
            while self._should_continue():
                await self._execute_step()

        except Exception as e:
            logger.error(f"Workflow error: {e}")
            self._state["error"] = str(e)

        return self.state

    def _should_continue(self) -> bool:
        """Check if the workflow should continue executing."""
        # Stop if there's an error
        if self._state["error"]:
            return False

        # Stop if we've exceeded max steps
        if self._state["current_step"] >= self._state["max_steps"]:
            self._state["error"] = f"Exceeded maximum steps ({self._state['max_steps']})"
            return False

        # Stop if we've exceeded cost limit
        if self._state["cost_usd"] >= self.config.max_cost_usd:
            self._state["error"] = f"Exceeded cost limit (${self.config.max_cost_usd})"
            return False

        # Stop if there's a pending approval
        if self._state["pending_approval"]:
            return False

        # Stop if we have a final output
        if self._state["output"] is not None:
            return False

        return True

    async def _execute_step(self) -> None:
        """Execute a single step of the workflow."""
        self._state["current_step"] += 1
        step = self._state["current_step"]

        logger.debug(f"Executing step {step} of run {self.config.run_id}")

        # Build the prompt with tools
        messages = self._build_messages()
        tools = self._build_tools_schema()

        # Call the LLM
        response = await self._call_llm(messages, tools)

        if response is None:
            self._state["error"] = "LLM call failed"
            return

        # Process the response
        if response.get("type") == "tool_use":
            await self._handle_tool_call(response)
        else:
            # Final response
            self._state["output"] = response.get("content", "")
            self._state["messages"].append({
                "role": "assistant",
                "content": self._state["output"]
            })

        # Callback for step completion
        if self.config.on_step_complete:
            await self._safe_callback(
                self.config.on_step_complete,
                step,
                self.state
            )

    def _build_messages(self) -> list[dict]:
        """Build the message list for the LLM call."""
        messages = []

        # System prompt
        if self.config.system_prompt:
            messages.append({
                "role": "system",
                "content": self.config.system_prompt
            })

        # Add conversation history
        messages.extend(self._state["messages"])

        return messages

    def _build_tools_schema(self) -> list[dict]:
        """Build the tools schema for the LLM call."""
        tools = []

        for tool in self.config.tools:
            if tool.forbidden:
                continue

            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })

        return tools

    async def _call_llm(
        self,
        messages: list[dict],
        tools: list[dict]
    ) -> Optional[dict]:
        """
        Call the LLM with messages and tools.

        This is a placeholder that will integrate with Anthropic's API.
        """
        if self.llm_client is None:
            # Mock response for testing
            return {
                "type": "text",
                "content": "This is a mock response. Configure llm_client for real execution."
            }

        try:
            # Anthropic API call (when client is configured)
            response = await self.llm_client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages,
                tools=tools if tools else None
            )

            # Track token usage
            if hasattr(response, 'usage'):
                self._state["tokens_input"] += response.usage.input_tokens
                self._state["tokens_output"] += response.usage.output_tokens
                # Estimate cost (Claude pricing)
                self._state["cost_usd"] += self._estimate_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )

            # Parse response
            if response.stop_reason == "tool_use":
                tool_use = response.content[-1]
                return {
                    "type": "tool_use",
                    "name": tool_use.name,
                    "input": tool_use.input,
                    "id": tool_use.id
                }
            else:
                return {
                    "type": "text",
                    "content": response.content[0].text
                }

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    async def _handle_tool_call(self, tool_response: dict) -> None:
        """Handle a tool call from the LLM."""
        tool_name = tool_response["name"]
        tool_input = tool_response["input"]
        tool_id = tool_response.get("id", "")

        # Find the tool definition
        tool_def = next(
            (t for t in self.config.tools if t.name == tool_name),
            None
        )

        if tool_def is None:
            self._state["error"] = f"Unknown tool: {tool_name}"
            return

        # Check if tool is forbidden
        if self._is_forbidden(tool_name):
            self._state["error"] = f"Forbidden tool: {tool_name}"
            return

        # Check if approval is required
        if self._requires_approval(tool_name):
            self._state["pending_approval"] = {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_id": tool_id,
                "step": self._state["current_step"],
                "requested_at": datetime.utcnow().isoformat()
            }

            if self.config.on_approval_required:
                await self._safe_callback(
                    self.config.on_approval_required,
                    self._state["pending_approval"]
                )
            return

        # Execute the tool
        result = await self._execute_tool(tool_name, tool_input, tool_def)

        # Record the tool call
        self._state["tools_called"].append({
            "name": tool_name,
            "input": tool_input,
            "output": result,
            "step": self._state["current_step"]
        })

        # Add to message history
        self._state["messages"].append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_id,
                "name": tool_name,
                "input": tool_input
            }]
        })
        self._state["messages"].append({
            "role": "tool",
            "tool_call_id": tool_id,
            "content": str(result)
        })

        # Callback for tool call
        if self.config.on_tool_call:
            await self._safe_callback(
                self.config.on_tool_call,
                tool_name,
                tool_input,
                result
            )

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        tool_def: ToolDefinition
    ) -> Any:
        """
        Execute a tool via MCP.

        This is a placeholder that will integrate with the MCP client.
        """
        logger.info(f"Executing tool: {tool_name} on {tool_def.mcp_server}")

        # TODO: Integrate with MCP client in Phase 2
        # For now, return a mock result
        return {
            "status": "success",
            "message": f"Mock result for {tool_name}",
            "data": {}
        }

    def _is_forbidden(self, tool_name: str) -> bool:
        """Check if a tool is forbidden."""
        for pattern in self.config.forbidden_actions:
            if fnmatch.fnmatch(tool_name, pattern):
                return True
        return False

    def _requires_approval(self, tool_name: str) -> bool:
        """Check if a tool requires approval."""
        for pattern in self.config.require_approval_for:
            if fnmatch.fnmatch(tool_name, pattern):
                return True
        return False

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token usage."""
        # Claude Sonnet pricing (approximate)
        input_cost = (input_tokens / 1_000_000) * 3.00  # $3 per 1M input tokens
        output_cost = (output_tokens / 1_000_000) * 15.00  # $15 per 1M output tokens
        return input_cost + output_cost

    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Safely execute a callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    async def resume_after_approval(self, approved: bool, notes: Optional[str] = None) -> AgentState:
        """
        Resume workflow after an approval decision.

        Args:
            approved: Whether the action was approved
            notes: Optional notes from the approver

        Returns:
            Updated workflow state
        """
        if not self._state["pending_approval"]:
            raise ValueError("No pending approval to resume from")

        approval = self._state["pending_approval"]
        self._state["pending_approval"] = None

        if approved:
            # Execute the previously blocked tool
            tool_name = approval["tool_name"]
            tool_input = approval["tool_input"]
            tool_id = approval.get("tool_id", "")

            tool_def = next(
                (t for t in self.config.tools if t.name == tool_name),
                None
            )

            if tool_def:
                result = await self._execute_tool(tool_name, tool_input, tool_def)

                self._state["tools_called"].append({
                    "name": tool_name,
                    "input": tool_input,
                    "output": result,
                    "step": self._state["current_step"],
                    "approved": True,
                    "approval_notes": notes
                })

                # Continue execution
                while self._should_continue():
                    await self._execute_step()
        else:
            self._state["error"] = f"Approval rejected: {notes or 'No reason provided'}"

        return self.state


# =============================================================================
# Utility Functions
# =============================================================================

def create_tool_from_mcp(
    mcp_tool: dict,
    mcp_server: str,
    approval_patterns: list[str] = None,
    forbidden_patterns: list[str] = None
) -> ToolDefinition:
    """
    Create a ToolDefinition from an MCP tool response.

    Args:
        mcp_tool: Tool definition from MCP server
        mcp_server: Name of the MCP server
        approval_patterns: Patterns for tools requiring approval
        forbidden_patterns: Patterns for forbidden tools

    Returns:
        ToolDefinition instance
    """
    name = mcp_tool.get("name", "")
    approval_patterns = approval_patterns or []
    forbidden_patterns = forbidden_patterns or []

    requires_approval = any(
        fnmatch.fnmatch(name, p) for p in approval_patterns
    )
    forbidden = any(
        fnmatch.fnmatch(name, p) for p in forbidden_patterns
    )

    return ToolDefinition(
        name=name,
        description=mcp_tool.get("description", ""),
        mcp_server=mcp_server,
        input_schema=mcp_tool.get("inputSchema", {}),
        requires_approval=requires_approval,
        forbidden=forbidden
    )
