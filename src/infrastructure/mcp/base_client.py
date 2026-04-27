"""
Base MCP Client implementation.

Provides the foundation for all MCP clients with common functionality
for tool calling and communication with MCP servers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import asyncio
import json
import logging
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Raised when MCP connection fails."""
    pass


class MCPToolError(Exception):
    """Raised when MCP tool call fails."""
    pass


class BaseMCPClient(ABC):
    """
    Base class for MCP clients.

    Provides common functionality for connecting to MCP servers
    and calling tools. Subclasses should define specific tool methods.
    """

    def __init__(self, server_name: str, transport: str = "stdio", command: Optional[str] = None):
        """
        Initialize the MCP client.

        Args:
            server_name: Name of the MCP server
            transport: Transport type ("stdio" or "sse")
            command: Command to start the server (for stdio transport)
        """
        self.server_name = server_name
        self.transport = transport
        self.command = command
        self._session: Optional[ClientSession] = None
        self._server_params: Optional[StdioServerParameters] = None
        self._stdio_client = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """
        Establish connection to the MCP server.

        Raises:
            MCPConnectionError: If connection fails
        """
        try:
            if self.transport == "stdio" and self.command:
                self._server_params = StdioServerParameters(
                    command=self.command,
                    env=None,
                )
                self._stdio_client = stdio_client(self._server_params)
                stdio_transport = await self._stdio_client.__aenter__()
                read, write = stdio_transport
                self._session = ClientSession(read, write)
                await self._session.__aenter__()
                await self._session.initialize()
                logger.info(f"Connected to MCP server: {self.server_name}")
            else:
                raise MCPConnectionError(
                    f"Unsupported transport type: {self.transport} or missing command"
                )
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_name}: {e}")
            raise MCPConnectionError(f"Failed to connect to {self.server_name}: {e}") from e

    async def close(self) -> None:
        """Close the connection to the MCP server."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing session: {e}")
        if self._stdio_client:
            try:
                await self._stdio_client.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing stdio client: {e}")
        logger.info(f"Closed connection to MCP server: {self.server_name}")

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            params: Parameters to pass to the tool

        Returns:
            The result from the tool call

        Raises:
            MCPToolError: If tool call fails
        """
        if not self._session:
            await self.connect()

        try:
            logger.info(f"Calling tool {tool_name} on {self.server_name} with params: {params}")
            result = await self._session.call_tool(tool_name, params)
            logger.info(f"Tool {tool_name} returned result: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise MCPToolError(f"Tool call failed for {tool_name}: {e}") from e

    async def list_tools(self) -> list:
        """
        List available tools on the MCP server.

        Returns:
            List of available tool descriptions
        """
        if not self._session:
            await self.connect()

        try:
            response = await self._session.list_tools()
            return response.tools
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise MCPToolError(f"Failed to list tools: {e}") from e

    @abstractmethod
    def get_server_command(self) -> str:
        """
        Get the command to start the MCP server.

        Returns:
            Command string to start the server
        """
        pass
