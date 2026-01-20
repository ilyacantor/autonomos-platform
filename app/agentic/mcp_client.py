"""
MCP (Model Context Protocol) Client

Manages connections to MCP servers and executes tool calls.
Implements the MCP specification for tool discovery and invocation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class MCPTransport(str, Enum):
    """Supported MCP transport types."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPAuthType(str, Enum):
    """Supported MCP authentication types."""
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH = "oauth"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    url: str
    transport: MCPTransport = MCPTransport.STDIO
    auth_type: MCPAuthType = MCPAuthType.NONE
    auth_token: Optional[str] = None
    timeout_ms: int = 30000
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class MCPTool:
    """Tool discovered from an MCP server."""
    name: str
    description: str
    input_schema: dict
    server_name: str


@dataclass
class MCPToolResult:
    """Result from executing an MCP tool."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)


class MCPClient:
    """
    Client for connecting to and executing tools on MCP servers.

    Supports:
    - Multiple server connections
    - Tool discovery
    - Authenticated tool execution
    - On-Behalf-Of (OBO) token management (ARB Condition 1)
    """

    def __init__(self):
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPTool] = {}
        self._connections: dict[str, Any] = {}
        self._obo_tokens: dict[str, dict] = {}

    async def add_server(self, config: MCPServerConfig) -> None:
        """
        Add and connect to an MCP server.

        Args:
            config: Server configuration
        """
        if not config.enabled:
            logger.info(f"Skipping disabled MCP server: {config.name}")
            return

        logger.info(f"Adding MCP server: {config.name} ({config.url})")
        self._servers[config.name] = config

        # Connect and discover tools
        try:
            await self._connect(config)
            await self._discover_tools(config)
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {config.name}: {e}")
            raise

    async def remove_server(self, name: str) -> None:
        """
        Disconnect and remove an MCP server.

        Args:
            name: Server name
        """
        if name in self._connections:
            await self._disconnect(name)

        if name in self._servers:
            del self._servers[name]

        # Remove tools from this server
        self._tools = {
            k: v for k, v in self._tools.items()
            if v.server_name != name
        }

    def list_servers(self) -> list[MCPServerConfig]:
        """List all configured servers."""
        return list(self._servers.values())

    def list_tools(self, server_name: str = None) -> list[MCPTool]:
        """
        List available tools.

        Args:
            server_name: Optional filter by server

        Returns:
            List of available tools
        """
        if server_name:
            return [t for t in self._tools.values() if t.server_name == server_name]
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def set_obo_token(
        self,
        server_name: str,
        token: str,
        expires_at: datetime
    ) -> None:
        """
        Set an OBO (On-Behalf-Of) token for a server.

        ARB Condition 1: Token refresh on approval resume.

        Args:
            server_name: Server to set token for
            token: The OBO token
            expires_at: Token expiration time
        """
        self._obo_tokens[server_name] = {
            "token": token,
            "expires_at": expires_at
        }
        logger.debug(f"Set OBO token for {server_name}, expires at {expires_at}")

    def clear_obo_token(self, server_name: str) -> None:
        """Clear the OBO token for a server."""
        if server_name in self._obo_tokens:
            del self._obo_tokens[server_name]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        run_context: Optional[dict] = None
    ) -> MCPToolResult:
        """
        Execute a tool on its MCP server.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            run_context: Optional context including tenant_id, run_id, etc.

        Returns:
            MCPToolResult with execution outcome
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return MCPToolResult(
                success=False,
                error=f"Tool not found: {tool_name}"
            )

        server = self._servers.get(tool.server_name)
        if not server:
            return MCPToolResult(
                success=False,
                error=f"Server not found: {tool.server_name}"
            )

        logger.info(f"Executing tool: {tool_name} on {tool.server_name}")
        start_time = datetime.utcnow()

        try:
            # Get authentication headers
            headers = self._get_auth_headers(tool.server_name)

            # Execute based on transport type
            if server.transport == MCPTransport.STDIO:
                result = await self._execute_stdio(server, tool_name, arguments)
            elif server.transport == MCPTransport.HTTP:
                result = await self._execute_http(server, tool_name, arguments, headers)
            elif server.transport == MCPTransport.WEBSOCKET:
                result = await self._execute_websocket(server, tool_name, arguments)
            else:
                raise ValueError(f"Unsupported transport: {server.transport}")

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return MCPToolResult(
                success=True,
                result=result,
                duration_ms=duration_ms,
                metadata={
                    "server": tool.server_name,
                    "tool": tool_name
                }
            )

        except asyncio.TimeoutError:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return MCPToolResult(
                success=False,
                error=f"Tool execution timed out after {server.timeout_ms}ms",
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Tool execution failed: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )

    def _get_auth_headers(self, server_name: str) -> dict:
        """Get authentication headers for a server."""
        headers = {}
        server = self._servers.get(server_name)

        if not server:
            return headers

        # Check for OBO token first
        obo = self._obo_tokens.get(server_name)
        if obo and obo["expires_at"] > datetime.utcnow():
            headers["Authorization"] = f"Bearer {obo['token']}"
            headers["X-OBO-Token"] = "true"
            return headers

        # Fall back to server's configured auth
        if server.auth_type == MCPAuthType.BEARER and server.auth_token:
            headers["Authorization"] = f"Bearer {server.auth_token}"
        elif server.auth_type == MCPAuthType.API_KEY and server.auth_token:
            headers["X-API-Key"] = server.auth_token

        return headers

    async def _connect(self, config: MCPServerConfig) -> None:
        """Establish connection to an MCP server."""
        if config.transport == MCPTransport.STDIO:
            # For stdio, we spawn the process when needed
            self._connections[config.name] = {"type": "stdio", "config": config}

        elif config.transport == MCPTransport.HTTP:
            # For HTTP, we just validate the endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{config.url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(f"Health check failed: {response.status}")
            self._connections[config.name] = {"type": "http", "url": config.url}

        elif config.transport == MCPTransport.WEBSOCKET:
            # WebSocket connection placeholder
            self._connections[config.name] = {"type": "websocket", "url": config.url}

    async def _disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server."""
        conn = self._connections.get(server_name)
        if not conn:
            return

        if conn["type"] == "stdio":
            # Kill subprocess if running
            if "process" in conn and conn["process"]:
                conn["process"].terminate()

        del self._connections[server_name]

    async def _discover_tools(self, config: MCPServerConfig) -> None:
        """Discover available tools from an MCP server."""
        logger.info(f"Discovering tools from {config.name}")

        if config.transport == MCPTransport.HTTP:
            tools = await self._discover_http_tools(config)
        else:
            # For stdio/websocket, tools would be discovered via the MCP protocol
            # Placeholder implementation
            tools = []

        for tool_data in tools:
            tool = MCPTool(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_name=config.name
            )
            self._tools[tool.name] = tool

        logger.info(f"Discovered {len(tools)} tools from {config.name}")

    async def _discover_http_tools(self, config: MCPServerConfig) -> list[dict]:
        """Discover tools from an HTTP MCP server."""
        try:
            import aiohttp
            headers = self._get_auth_headers(config.name)

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{config.url}/tools",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("tools", [])
                    else:
                        logger.warning(f"Tool discovery failed: {response.status}")
                        return []
        except ImportError:
            logger.warning("aiohttp not installed, skipping HTTP tool discovery")
            return []
        except Exception as e:
            logger.error(f"Tool discovery error: {e}")
            return []

    async def _execute_stdio(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict
    ) -> Any:
        """Execute a tool via stdio transport."""
        # Placeholder for stdio MCP execution
        # Would spawn/communicate with subprocess using JSON-RPC
        logger.debug(f"Stdio execution: {tool_name}")
        return {"status": "executed", "transport": "stdio"}

    async def _execute_http(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict,
        headers: dict
    ) -> Any:
        """Execute a tool via HTTP transport."""
        try:
            import aiohttp

            payload = {
                "tool": tool_name,
                "arguments": arguments
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{server.url}/tools/execute",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=server.timeout_ms / 1000)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Tool execution failed: {response.status} - {error_text}")

        except ImportError:
            logger.warning("aiohttp not installed, returning mock result")
            return {"status": "mock", "tool": tool_name}

    async def _execute_websocket(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict
    ) -> Any:
        """Execute a tool via WebSocket transport."""
        # Placeholder for WebSocket MCP execution
        logger.debug(f"WebSocket execution: {tool_name}")
        return {"status": "executed", "transport": "websocket"}


class MCPClientPool:
    """
    Pool of MCP clients for multi-tenant usage.

    Manages client instances per tenant to ensure proper isolation.
    """

    def __init__(self):
        self._clients: dict[UUID, MCPClient] = {}

    def get_client(self, tenant_id: UUID) -> MCPClient:
        """
        Get or create an MCP client for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            MCPClient instance for the tenant
        """
        if tenant_id not in self._clients:
            self._clients[tenant_id] = MCPClient()
        return self._clients[tenant_id]

    async def configure_client(
        self,
        tenant_id: UUID,
        servers: list[MCPServerConfig]
    ) -> MCPClient:
        """
        Configure an MCP client with servers.

        Args:
            tenant_id: Tenant identifier
            servers: List of server configurations

        Returns:
            Configured MCPClient
        """
        client = self.get_client(tenant_id)

        for server in servers:
            try:
                await client.add_server(server)
            except Exception as e:
                logger.error(f"Failed to add server {server.name}: {e}")

        return client

    async def cleanup_client(self, tenant_id: UUID) -> None:
        """
        Clean up and remove a tenant's MCP client.

        Args:
            tenant_id: Tenant identifier
        """
        if tenant_id in self._clients:
            client = self._clients[tenant_id]
            for server_name in list(client._servers.keys()):
                await client.remove_server(server_name)
            del self._clients[tenant_id]


# Global client pool
_client_pool: Optional[MCPClientPool] = None


def get_mcp_client_pool() -> MCPClientPool:
    """Get the global MCP client pool."""
    global _client_pool
    if _client_pool is None:
        _client_pool = MCPClientPool()
    return _client_pool
