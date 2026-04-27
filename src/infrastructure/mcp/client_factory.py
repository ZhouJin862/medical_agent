"""
MCP Client Factory.

Provides factory methods for creating MCP client instances.
"""
import logging
from typing import Dict, Optional, Type
from pathlib import Path

from .base_client import BaseMCPClient

logger = logging.getLogger(__name__)


class MCPClientFactory:
    """
    Factory for creating MCP client instances.

    Manages client registration and creation based on server names.
    """

    _clients: Dict[str, Type[BaseMCPClient]] = {}

    @classmethod
    def register_client(cls, server_name: str, client_class: Type[BaseMCPClient]) -> None:
        """
        Register a client class for a specific server.

        Args:
            server_name: Name of the MCP server
            client_class: Client class to register
        """
        cls._clients[server_name] = client_class
        logger.info(f"Registered MCP client for server: {server_name}")

    @classmethod
    def unregister_client(cls, server_name: str) -> None:
        """
        Unregister a client class.

        Args:
            server_name: Name of the MCP server to unregister
        """
        if server_name in cls._clients:
            del cls._clients[server_name]
            logger.info(f"Unregistered MCP client for server: {server_name}")

    @classmethod
    def get_client(cls, server_name: str) -> Optional[BaseMCPClient]:
        """
        Get an MCP client instance for the specified server.

        Args:
            server_name: Name of the MCP server

        Returns:
            MCP client instance or None if not registered

        Raises:
            ValueError: If server_name is not registered
        """
        if server_name not in cls._clients:
            raise ValueError(
                f"No client registered for server: {server_name}. "
                f"Available servers: {list(cls._clients.keys())}"
            )

        client_class = cls._clients[server_name]
        return client_class(server_name=server_name)

    @classmethod
    def list_registered_servers(cls) -> list:
        """
        List all registered server names.

        Returns:
            List of registered server names
        """
        return list(cls._clients.keys())

    @classmethod
    def is_registered(cls, server_name: str) -> bool:
        """
        Check if a server is registered.

        Args:
            server_name: Name of the MCP server

        Returns:
            True if registered, False otherwise
        """
        return server_name in cls._clients


# Import and register client classes
def _register_default_clients():
    """Register default MCP clients."""
    from .clients.profile_client import ProfileMCPClient
    from .clients.triage_client import TriageMCPClient
    from .clients.medication_client import MedicationMCPClient
    from .clients.service_client import ServiceMCPClient

    MCPClientFactory.register_client("profile_server", ProfileMCPClient)
    MCPClientFactory.register_client("triage_server", TriageMCPClient)
    MCPClientFactory.register_client("medication_server", MedicationMCPClient)
    MCPClientFactory.register_client("service_server", ServiceMCPClient)


# Auto-register clients on import
_register_default_clients()
