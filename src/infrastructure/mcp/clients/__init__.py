"""
MCP Clients module.

Contains all MCP client implementations for various medical services.
"""
from .profile_client import ProfileMCPClient
from .triage_client import TriageMCPClient
from .medication_client import MedicationMCPClient
from .service_client import ServiceMCPClient

__all__ = [
    "ProfileMCPClient",
    "TriageMCPClient",
    "MedicationMCPClient",
    "ServiceMCPClient",
]
