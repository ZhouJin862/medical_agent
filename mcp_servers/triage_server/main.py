"""
Triage MCP Server - Main entry point.

MCP server providing triage guidance including hospital,
department, and doctor recommendations.
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
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from .tools import TOOLS, TOOL_HANDLERS

# Create MCP server instance
server = Server("triage-server")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools on the triage server."""
    logger.info("Listing available tools")
    return TOOLS


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle tool call requests."""
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

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except Exception as e:
        error_msg = f"Error calling tool {name}: {str(e)}"
        logger.exception(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]


async def main():
    """Main entry point for the triage MCP server."""
    logger.info("Starting Triage MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="triage-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def health_check() -> dict[str, Any]:
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "server": "triage-server",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--health-check":
        result = health_check()
        print(json.dumps(result))
        sys.exit(0)

    asyncio.run(main())
