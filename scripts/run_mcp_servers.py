"""
MCP Servers startup script.

This script starts all MCP servers as separate processes.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import List
import subprocess
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class MCPServerManager:
    """Manages multiple MCP server processes."""

    def __init__(self):
        """Initialize the server manager."""
        self.servers: List[subprocess.Popen] = []
        self.server_configs = [
            {
                "name": "profile_server",
                "path": PROJECT_ROOT / "mcp_servers" / "profile_server" / "main.py",
                "env_var": "HEALTH_ARCHIVE_URL"
            },
            {
                "name": "triage_server",
                "path": PROJECT_ROOT / "mcp_servers" / "triage_server" / "main.py",
                "env_var": "TRIAGE_SERVICE_URL"
            },
            {
                "name": "medication_server",
                "path": PROJECT_ROOT / "mcp_servers" / "medication_server" / "main.py",
                "env_var": "MEDICATION_SERVICE_URL"
            },
            {
                "name": "service_server",
                "path": PROJECT_ROOT / "mcp_servers" / "service_server" / "main.py",
                "env_var": "SERVICE_RECOMMENDATION_URL"
            }
        ]

    def start_server(self, config: dict) -> subprocess.Popen:
        """
        Start a single MCP server.

        Args:
            config: Server configuration dictionary

        Returns:
            Subprocess object for the server
        """
        server_path = config["path"]
        if not server_path.exists():
            logger.error(f"Server path does not exist: {server_path}")
            return None

        cmd = [sys.executable, str(server_path)]
        logger.info(f"Starting {config['name']} with command: {' '.join(cmd)}")

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)

        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"Started {config['name']} with PID: {process.pid}")
            return process
        except Exception as e:
            logger.error(f"Failed to start {config['name']}: {e}")
            return None

    def start_all(self) -> None:
        """Start all MCP servers."""
        logger.info("Starting all MCP servers...")
        for config in self.server_configs:
            process = self.start_server(config)
            if process:
                self.servers.append(process)

        logger.info(f"Started {len(self.servers)} MCP servers")

    def stop_all(self) -> None:
        """Stop all running MCP servers."""
        logger.info("Stopping all MCP servers...")
        for server in self.servers:
            try:
                server.terminate()
                server.wait(timeout=5)
                logger.info(f"Stopped server with PID: {server.pid}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Server with PID {server.pid} did not terminate, killing...")
                server.kill()
            except Exception as e:
                logger.error(f"Error stopping server: {e}")

        self.servers.clear()
        logger.info("All MCP servers stopped")

    def wait(self) -> None:
        """Wait for all servers to complete."""
        for server in self.servers:
            server.wait()

    def health_check(self) -> dict:
        """
        Perform health check on all servers.

        Returns:
            Dictionary with health status of each server
        """
        import json

        results = {}
        for config in self.server_configs:
            server_path = config["path"]
            try:
                result = subprocess.run(
                    [sys.executable, str(server_path), "--health-check"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
                )
                if result.returncode == 0:
                    results[config["name"]] = json.loads(result.stdout)
                else:
                    results[config["name"]] = {"status": "unhealthy", "error": result.stderr}
            except Exception as e:
                results[config["name"]] = {"status": "error", "error": str(e)}

        return results


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    manager.stop_all()
    sys.exit(0)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Servers Manager")
    parser.add_argument(
        "--action",
        choices=["start", "stop", "restart", "health-check"],
        default="start",
        help="Action to perform"
    )
    parser.add_argument(
        "--servers",
        nargs="+",
        choices=["profile_server", "triage_server", "medication_server", "service_server"],
        help="Specific servers to manage (default: all)"
    )

    args = parser.parse_args()

    global manager
    manager = MCPServerManager()

    # Filter servers if specified
    if args.servers:
        manager.server_configs = [
            c for c in manager.server_configs if c["name"] in args.servers
        ]

    if args.action == "health-check":
        results = manager.health_check()
        print("\n=== MCP Servers Health Check ===\n")
        for name, status in results.items():
            print(f"{name}: {status.get('status', 'unknown')}")
            if status.get('status') != 'healthy':
                print(f"  Error: {status.get('error', 'Unknown error')}")
        print()
        return

    if args.action == "start":
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        manager.start_all()
        print("\n=== MCP Servers Started ===")
        print("Press Ctrl+C to stop all servers\n")
        manager.wait()

    elif args.action == "stop":
        print("Stopping MCP servers...")
        print("Note: This script only stops servers it started")
        print("For running servers, use: pkill -f 'mcp_servers'")

    elif args.action == "restart":
        manager.stop_all()
        import time
        time.sleep(2)
        manager.start_all()


if __name__ == "__main__":
    main()
