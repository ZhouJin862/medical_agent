"""
Profile MCP Server - Main entry point.

MCP server providing access to patient health profile data from the
health archive system.
"""
import asyncio
import json
import logging
from typing import Any
import sys

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolRequest,
    ListToolsRequest,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from .tools import TOOLS, TOOL_HANDLERS

# Create MCP server instance
server = Server("profile-server")

# Health check endpoint for monitoring
HEALTH_CHECK_PATH = "/health"


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List available tools on the profile server.

    Returns:
        List of available tool definitions
    """
    logger.info("Listing available tools")
    return TOOLS


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """
    Handle tool call requests.

    Args:
        name: Tool name to call
        arguments: Tool arguments

    Returns:
        Tool result as text content
    """
    logger.info(f"Calling tool: {name} with arguments: {arguments}")

    try:
        if name not in TOOL_HANDLERS:
            error_msg = f"Unknown tool: {name}"
            logger.error(error_msg)
            return [TextContent(type="text", text=json.dumps({"error": error_msg}))]

        handler = TOOL_HANDLERS[name]

        # Call the handler function
        if asyncio.iscoroutinefunction(handler):
            result = await handler(**arguments)
        else:
            result = handler(**arguments)

        # Return result as JSON
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except Exception as e:
        error_msg = f"Error calling tool {name}: {str(e)}"
        logger.exception(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]


async def main():
    """
    Main entry point for the profile MCP server.

    Starts the server with stdio transport.
    """
    logger.info("Starting Profile MCP Server...")

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="profile-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def health_check() -> dict[str, Any]:
    """
    Health check endpoint for monitoring.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "server": "profile-server",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    # Check for health check argument
    if len(sys.argv) > 1 and sys.argv[1] == "--health-check":
        result = health_check()
        print(json.dumps(result))
        sys.exit(0)

    asyncio.run(main())
