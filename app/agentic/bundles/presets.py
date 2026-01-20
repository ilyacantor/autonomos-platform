"""
Preset Tool Bundles

Pre-configured tool bundles for common use cases:
- Data operations
- Code execution
- Communication
- Search and analysis
"""

from typing import List

from app.agentic.bundles.registry import (
    Tool,
    ToolBundle,
    ToolCategory,
    ToolPermission,
)


def create_data_bundle(tenant_id: str = "preset") -> ToolBundle:
    """Create the data operations bundle."""
    return ToolBundle(
        bundle_id="data-ops",
        name="Data Operations",
        description="Tools for data retrieval and manipulation",
        tenant_id=tenant_id,
        category=ToolCategory.DATA,
        is_preset=True,
        allowed_agent_types={"worker", "specialist", "planner"},
        tools=[
            Tool(
                tool_id="database_query",
                name="Database Query",
                description="Execute SQL queries against connected databases",
                category=ToolCategory.DATA,
                required_permissions={ToolPermission.READ, ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "database": {"type": "string"},
                        "parameters": {"type": "object"},
                    },
                    "required": ["query"],
                },
                cost_per_invocation=0.001,
            ),
            Tool(
                tool_id="data_transform",
                name="Data Transform",
                description="Transform data between formats (JSON, CSV, etc.)",
                category=ToolCategory.DATA,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "any"},
                        "from_format": {"type": "string"},
                        "to_format": {"type": "string"},
                    },
                    "required": ["data", "to_format"],
                },
            ),
            Tool(
                tool_id="data_validate",
                name="Data Validate",
                description="Validate data against a schema",
                category=ToolCategory.DATA,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "any"},
                        "schema": {"type": "object"},
                    },
                    "required": ["data", "schema"],
                },
            ),
            Tool(
                tool_id="data_aggregate",
                name="Data Aggregate",
                description="Aggregate data with grouping and calculations",
                category=ToolCategory.DATA,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                        "group_by": {"type": "array"},
                        "aggregations": {"type": "object"},
                    },
                    "required": ["data"],
                },
            ),
        ],
    )


def create_code_bundle(tenant_id: str = "preset") -> ToolBundle:
    """Create the code execution bundle."""
    return ToolBundle(
        bundle_id="code-exec",
        name="Code Execution",
        description="Tools for code execution and analysis",
        tenant_id=tenant_id,
        category=ToolCategory.CODE,
        is_preset=True,
        allowed_agent_types={"specialist"},
        required_capabilities={"code_execution"},
        requires_approval=True,
        audit_all_invocations=True,
        tools=[
            Tool(
                tool_id="python_execute",
                name="Python Execute",
                description="Execute Python code in a sandboxed environment",
                category=ToolCategory.CODE,
                required_permissions={ToolPermission.EXECUTE},
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "timeout_seconds": {"type": "integer", "default": 30},
                        "memory_limit_mb": {"type": "integer", "default": 256},
                    },
                    "required": ["code"],
                },
                cost_per_invocation=0.01,
                max_invocations_per_minute=10,
            ),
            Tool(
                tool_id="code_analyze",
                name="Code Analyze",
                description="Static analysis of code for quality and security",
                category=ToolCategory.CODE,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"},
                        "checks": {"type": "array"},
                    },
                    "required": ["code"],
                },
            ),
            Tool(
                tool_id="code_format",
                name="Code Format",
                description="Format code according to style guidelines",
                category=ToolCategory.CODE,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"},
                        "style": {"type": "string"},
                    },
                    "required": ["code"],
                },
            ),
        ],
    )


def create_communication_bundle(tenant_id: str = "preset") -> ToolBundle:
    """Create the communication bundle."""
    return ToolBundle(
        bundle_id="comm",
        name="Communication",
        description="Tools for sending notifications and messages",
        tenant_id=tenant_id,
        category=ToolCategory.COMMUNICATION,
        is_preset=True,
        allowed_agent_types={"worker", "specialist", "reviewer"},
        required_capabilities={"notification"},
        tools=[
            Tool(
                tool_id="email",
                name="Send Email",
                description="Send email messages",
                category=ToolCategory.COMMUNICATION,
                required_permissions={ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "array"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                        "cc": {"type": "array"},
                        "attachments": {"type": "array"},
                    },
                    "required": ["to", "subject", "body"],
                },
                cost_per_invocation=0.001,
            ),
            Tool(
                tool_id="slack_message",
                name="Slack Message",
                description="Send Slack messages",
                category=ToolCategory.COMMUNICATION,
                required_permissions={ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string"},
                        "message": {"type": "string"},
                        "thread_ts": {"type": "string"},
                    },
                    "required": ["channel", "message"],
                },
            ),
            Tool(
                tool_id="webhook",
                name="Webhook Call",
                description="Call external webhooks",
                category=ToolCategory.COMMUNICATION,
                required_permissions={ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string", "default": "POST"},
                        "headers": {"type": "object"},
                        "body": {"type": "any"},
                    },
                    "required": ["url"],
                },
                cost_per_invocation=0.0001,
            ),
        ],
    )


def create_search_bundle(tenant_id: str = "preset") -> ToolBundle:
    """Create the search bundle."""
    return ToolBundle(
        bundle_id="search",
        name="Search",
        description="Tools for searching data and knowledge",
        tenant_id=tenant_id,
        category=ToolCategory.SEARCH,
        is_preset=True,
        allowed_agent_types={"worker", "specialist", "planner"},
        tools=[
            Tool(
                tool_id="vector_search",
                name="Vector Search",
                description="Semantic search over embeddings",
                category=ToolCategory.SEARCH,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "namespace": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                        "min_score": {"type": "number"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                tool_id="text_search",
                name="Text Search",
                description="Full-text search over documents",
                category=ToolCategory.SEARCH,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "index": {"type": "string"},
                        "filters": {"type": "object"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                tool_id="web_search",
                name="Web Search",
                description="Search the web for information",
                category=ToolCategory.SEARCH,
                required_permissions={ToolPermission.READ, ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "num_results": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
                cost_per_invocation=0.005,
            ),
        ],
    )


def create_analysis_bundle(tenant_id: str = "preset") -> ToolBundle:
    """Create the analysis bundle."""
    return ToolBundle(
        bundle_id="analysis",
        name="Analysis",
        description="Tools for data analysis and insights",
        tenant_id=tenant_id,
        category=ToolCategory.ANALYSIS,
        is_preset=True,
        allowed_agent_types={"specialist"},
        required_capabilities={"data_analysis"},
        tools=[
            Tool(
                tool_id="statistics",
                name="Statistics",
                description="Calculate statistical measures",
                category=ToolCategory.ANALYSIS,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                        "measures": {"type": "array"},
                    },
                    "required": ["data"],
                },
            ),
            Tool(
                tool_id="trend_analysis",
                name="Trend Analysis",
                description="Analyze trends in time series data",
                category=ToolCategory.ANALYSIS,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                        "time_column": {"type": "string"},
                        "value_column": {"type": "string"},
                    },
                    "required": ["data"],
                },
            ),
            Tool(
                tool_id="anomaly_detection",
                name="Anomaly Detection",
                description="Detect anomalies in data",
                category=ToolCategory.ANALYSIS,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                        "sensitivity": {"type": "number", "default": 0.95},
                    },
                    "required": ["data"],
                },
            ),
        ],
    )


def create_approval_bundle(tenant_id: str = "preset") -> ToolBundle:
    """Create the approval bundle."""
    return ToolBundle(
        bundle_id="approval",
        name="Approval",
        description="Tools for approval workflows and human escalation",
        tenant_id=tenant_id,
        category=ToolCategory.APPROVAL,
        is_preset=True,
        allowed_agent_types={"reviewer", "approver"},
        required_capabilities={"human_escalation", "approval_authority"},
        tools=[
            Tool(
                tool_id="request_approval",
                name="Request Approval",
                description="Request human approval for an action",
                category=ToolCategory.APPROVAL,
                required_permissions={ToolPermission.WRITE},
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "reason": {"type": "string"},
                        "priority": {"type": "string"},
                        "approvers": {"type": "array"},
                        "timeout_hours": {"type": "integer", "default": 24},
                    },
                    "required": ["action", "reason"],
                },
            ),
            Tool(
                tool_id="policy_check",
                name="Policy Check",
                description="Check if an action is allowed by policy",
                category=ToolCategory.APPROVAL,
                required_permissions={ToolPermission.READ},
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "context": {"type": "object"},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                tool_id="escalate",
                name="Escalate",
                description="Escalate to human operators",
                category=ToolCategory.APPROVAL,
                required_permissions={ToolPermission.WRITE, ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "severity": {"type": "string"},
                        "context": {"type": "object"},
                    },
                    "required": ["issue"],
                },
            ),
        ],
    )


def create_integration_bundle(tenant_id: str = "preset") -> ToolBundle:
    """Create the external integrations bundle."""
    return ToolBundle(
        bundle_id="integration",
        name="Integrations",
        description="Tools for external service integrations",
        tenant_id=tenant_id,
        category=ToolCategory.INTEGRATION,
        is_preset=True,
        allowed_agent_types={"worker", "specialist", "planner"},
        tools=[
            Tool(
                tool_id="jira",
                name="Jira",
                description="Create and manage Jira issues",
                category=ToolCategory.INTEGRATION,
                required_permissions={ToolPermission.WRITE, ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "project": {"type": "string"},
                        "issue_type": {"type": "string"},
                        "summary": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                tool_id="calendar",
                name="Calendar",
                description="Manage calendar events",
                category=ToolCategory.INTEGRATION,
                required_permissions={ToolPermission.WRITE, ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "title": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "attendees": {"type": "array"},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                tool_id="github",
                name="GitHub",
                description="GitHub operations (issues, PRs, etc.)",
                category=ToolCategory.INTEGRATION,
                required_permissions={ToolPermission.WRITE, ToolPermission.EXTERNAL},
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["action", "repo"],
                },
            ),
        ],
    )


def get_preset_bundles() -> List[ToolBundle]:
    """Get all preset bundles."""
    return [
        create_data_bundle(),
        create_code_bundle(),
        create_communication_bundle(),
        create_search_bundle(),
        create_analysis_bundle(),
        create_approval_bundle(),
        create_integration_bundle(),
    ]
