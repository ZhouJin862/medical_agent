"""
MCP (Model Context Protocol) infrastructure module.

Provides clients and utilities for communicating with MCP servers.
If the 'mcp' package is not installed, this module loads gracefully
with client registration skipped.
"""
from .base_client import BaseMCPClient, MCPConnectionError, MCPToolError, is_mcp_available
from .client_factory import MCPClientFactory

__all__ = [
    "BaseMCPClient",
    "MCPConnectionError",
    "MCPToolError",
    "MCPClientFactory",
    "is_mcp_available",
]
