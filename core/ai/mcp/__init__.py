"""
Model Context Protocol (MCP) Integration.

Provides MCP client and server implementations for tool interoperability.
"""

from core.ai.mcp.client import MCPClient, MCPTool, MCPToolRegistry
from core.ai.mcp.server import MCPServer, MCPServerConfig, ToolDefinition

__all__ = [
    "MCPClient",
    "MCPTool",
    "MCPToolRegistry",
    "MCPServer",
    "MCPServerConfig",
    "ToolDefinition",
]
