"""
Tool Bundles API Endpoints

REST API for managing tool bundles:
- List available bundles
- Get bundle details
- Create custom bundles
- Invoke tools
"""

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.agentic.bundles.registry import (
    ToolBundle,
    Tool,
    ToolCategory,
    ToolPermission,
    BundleRegistry,
    get_bundle_registry,
)

router = APIRouter(prefix="/bundles", tags=["tool-bundles"])


# Request/Response Models

class ToolResponse(BaseModel):
    """Tool response."""
    tool_id: str
    name: str
    description: str
    category: str
    required_permissions: List[str]
    version: str
    deprecated: bool
    cost_per_invocation: float
    cost_per_token: float


class BundleResponse(BaseModel):
    """Bundle response."""
    bundle_id: str
    name: str
    description: str
    category: str
    version: str
    is_preset: bool
    tool_count: int
    tools: List[ToolResponse]
    allowed_agent_types: List[str]
    required_capabilities: List[str]
    requires_approval: bool


class BundleListResponse(BaseModel):
    """Response for listing bundles."""
    bundles: List[BundleResponse]
    total: int


class ToolCreateRequest(BaseModel):
    """Request to create a tool."""
    name: str
    description: str
    category: str
    required_permissions: List[str] = []
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    cost_per_invocation: float = 0.0
    cost_per_token: float = 0.0


class BundleCreateRequest(BaseModel):
    """Request to create a bundle."""
    name: str
    description: str
    category: str = "data"
    tools: List[ToolCreateRequest] = []
    allowed_agent_types: List[str] = ["worker", "specialist"]
    required_capabilities: List[str] = []
    requires_approval: bool = False


class ToolInvokeRequest(BaseModel):
    """Request to invoke a tool."""
    tool_id: str
    agent_id: str = "default"
    parameters: dict = {}


class ToolInvokeResponse(BaseModel):
    """Response from tool invocation."""
    tool_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    cost: float = 0.0


class ToolStatsResponse(BaseModel):
    """Tool statistics response."""
    tool_id: str
    total_invocations: int
    current_hour: int
    hourly_breakdown: dict


# Helper functions

def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant ID from header."""
    return x_tenant_id or "00000000-0000-0000-0000-000000000001"


def tool_to_response(tool: Tool) -> ToolResponse:
    """Convert tool to response."""
    return ToolResponse(
        tool_id=tool.tool_id,
        name=tool.name,
        description=tool.description,
        category=tool.category.value,
        required_permissions=[p.value for p in tool.required_permissions],
        version=tool.version,
        deprecated=tool.deprecated,
        cost_per_invocation=tool.cost_per_invocation,
        cost_per_token=tool.cost_per_token,
    )


def bundle_to_response(bundle: ToolBundle) -> BundleResponse:
    """Convert bundle to response."""
    return BundleResponse(
        bundle_id=bundle.bundle_id,
        name=bundle.name,
        description=bundle.description,
        category=bundle.category.value,
        version=bundle.version,
        is_preset=bundle.is_preset,
        tool_count=len(bundle.tools),
        tools=[tool_to_response(t) for t in bundle.tools],
        allowed_agent_types=list(bundle.allowed_agent_types),
        required_capabilities=list(bundle.required_capabilities),
        requires_approval=bundle.requires_approval,
    )


# Endpoints

@router.get("", response_model=BundleListResponse)
async def list_bundles(
    category: Optional[str] = None,
    include_presets: bool = True,
    tenant_id: str = Depends(get_tenant_id),
):
    """List all available tool bundles."""
    registry = get_bundle_registry()

    cat = None
    if category:
        try:
            cat = ToolCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    bundles = registry.list_bundles(
        tenant_id=tenant_id,
        category=cat,
        include_presets=include_presets,
    )

    return BundleListResponse(
        bundles=[bundle_to_response(b) for b in bundles],
        total=len(bundles),
    )


@router.get("/{bundle_id}", response_model=BundleResponse)
async def get_bundle(
    bundle_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific bundle."""
    registry = get_bundle_registry()

    bundle = registry.get_bundle(bundle_id, tenant_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    return bundle_to_response(bundle)


@router.post("", response_model=BundleResponse, status_code=201)
async def create_bundle(
    data: BundleCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a custom tool bundle."""
    registry = get_bundle_registry()

    try:
        category = ToolCategory(data.category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {data.category}")

    # Create tools
    tools = []
    for tool_data in data.tools:
        try:
            tool_category = ToolCategory(tool_data.category)
            permissions = {ToolPermission(p) for p in tool_data.required_permissions}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        tool = Tool(
            tool_id=str(uuid4()),
            name=tool_data.name,
            description=tool_data.description,
            category=tool_category,
            required_permissions=permissions,
            input_schema=tool_data.input_schema,
            output_schema=tool_data.output_schema,
            cost_per_invocation=tool_data.cost_per_invocation,
            cost_per_token=tool_data.cost_per_token,
        )
        tools.append(tool)

    # Create bundle
    bundle = ToolBundle(
        bundle_id=str(uuid4()),
        name=data.name,
        description=data.description,
        tenant_id=tenant_id,
        category=category,
        tools=tools,
        allowed_agent_types=set(data.allowed_agent_types),
        required_capabilities=set(data.required_capabilities),
        requires_approval=data.requires_approval,
    )

    registry.register_bundle(bundle)

    return bundle_to_response(bundle)


@router.delete("/{bundle_id}", status_code=204)
async def delete_bundle(
    bundle_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a custom bundle."""
    registry = get_bundle_registry()

    # Check if bundle exists and is not a preset
    bundle = registry.get_bundle(bundle_id, tenant_id, include_presets=False)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    if bundle.is_preset:
        raise HTTPException(status_code=400, detail="Cannot delete preset bundles")

    success = registry.unregister_bundle(bundle_id, tenant_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete bundle")


@router.get("/agent/{agent_type}", response_model=BundleListResponse)
async def get_bundles_for_agent(
    agent_type: str,
    capabilities: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
):
    """Get bundles available to an agent based on type and capabilities."""
    registry = get_bundle_registry()

    caps = set(capabilities.split(",")) if capabilities else set()

    bundles = registry.get_bundles_for_agent(
        agent_type=agent_type,
        capabilities=caps,
        tenant_id=tenant_id,
    )

    return BundleListResponse(
        bundles=[bundle_to_response(b) for b in bundles],
        total=len(bundles),
    )


@router.get("/tools/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific tool."""
    registry = get_bundle_registry()

    tool = registry.get_tool(tool_id, tenant_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    return tool_to_response(tool)


@router.post("/tools/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(
    data: ToolInvokeRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    """Invoke a tool."""
    registry = get_bundle_registry()

    tool = registry.get_tool(data.tool_id, tenant_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    try:
        result = await registry.invoke_tool(
            tool_id=data.tool_id,
            tenant_id=tenant_id,
            agent_id=data.agent_id,
            **data.parameters,
        )

        return ToolInvokeResponse(
            tool_id=data.tool_id,
            status="success",
            result={"output": str(result)} if result else None,
            cost=tool.cost_per_invocation,
        )
    except NotImplementedError:
        # Tool has no handler - return mock response
        return ToolInvokeResponse(
            tool_id=data.tool_id,
            status="success",
            result={"mock": True, "message": "Tool executed (no handler)"},
            cost=tool.cost_per_invocation,
        )
    except Exception as e:
        return ToolInvokeResponse(
            tool_id=data.tool_id,
            status="error",
            error=str(e),
            cost=0.0,
        )


@router.get("/tools/{tool_id}/stats", response_model=ToolStatsResponse)
async def get_tool_stats(
    tool_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Get invocation statistics for a tool."""
    registry = get_bundle_registry()

    # Verify tool exists
    tool = registry.get_tool(tool_id, tenant_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    stats = registry.get_tool_stats(tool_id)

    return ToolStatsResponse(**stats)
