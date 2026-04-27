"""
Memory Store - Mem0 adapter for long-term memory management.

Handles:
- Storing patient context and conversations
- Retrieving relevant memories
- Searching memories by content
- Deleting memories
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """
    A memory entry.

    Attributes:
        memory_id: Unique identifier for the memory
        user_id: User/patient identifier
        memory: The memory content
        metadata: Additional metadata
        created_at: When the memory was created
        updated_at: When the memory was last updated
    """

    memory_id: str
    user_id: str
    memory: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MemoryStore:
    """
    Memory store using Mem0 for long-term memory management.

    Provides async interface for storing and retrieving patient
    conversations and health context.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the memory store.

        Args:
            api_key: Optional Mem0 API key (uses env var if not provided)
        """
        self._client = None
        self._api_key = api_key
        logger.info("MemoryStore initialized")

    @property
    def client(self):
        """Get or create the memory client."""
        if self._client is None:
            try:
                from mem0 import Memory as Mem0Client

                # Only use mem0 if API key is provided
                if not self._api_key:
                    raise ImportError("No mem0 API key provided")

                # Initialize with API key
                config = {"api_key": self._api_key}
                self._client = Mem0Client.from_config(config)
                logger.info("Mem0 client initialized")

            except (ImportError, Exception) as e:
                logger.warning(f"mem0 not available or error: {e}, using file-based fallback")
                from .file_memory_store import FileMemoryStore
                self._client = FileMemoryStore()

        return self._client

    async def add(
        self,
        user_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """
        Add a memory entry.

        Args:
            user_id: User/patient identifier
            message: Memory content
            metadata: Optional metadata

        Returns:
            Created memory entry
        """
        try:
            result = self.client.add(
                message,
                user_id=user_id,
                metadata=metadata or {},
            )

            return Memory(
                memory_id=result.get("id", ""),
                user_id=user_id,
                memory=message,
                metadata=metadata or {},
                created_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    async def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a user.

        Args:
            user_id: User/patient identifier

        Returns:
            List of memory entries
        """
        try:
            result = self.client.get_all(user_id=user_id)

            # Mem0 returns a list of memory dicts
            if isinstance(result, list):
                return result
            return []

        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []

    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by query.

        Args:
            query: Search query
            user_id: Optional user filter
            limit: Maximum results to return

        Returns:
            List of matching memory entries
        """
        try:
            result = self.client.search(
                query=query,
                user_id=user_id,
                limit=limit,
            )

            if isinstance(result, list):
                return result
            return []

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def delete(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(memory_id)
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    async def get_context(
        self,
        user_id: str,
        max_memories: int = 10,
    ) -> str:
        """
        Get conversational context for a user.

        Args:
            user_id: User/patient identifier
            max_memories: Maximum memories to include

        Returns:
            Formatted context string
        """
        memories = await self.get_all(user_id)

        if not memories:
            return ""

        # Take the most recent memories
        recent_memories = memories[-max_memories:]

        context_parts = []
        for mem in recent_memories:
            role = mem.get("metadata", {}).get("role", "unknown")
            content = mem.get("memory", "")
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)


class _InMemoryMemoryStore:
    """
    Fallback file-based store when Mem0 is not available.

    Uses JSON files for persistent storage.
    """

    def __init__(self):
        from .file_memory_store import FileMemoryStore
        self._impl = FileMemoryStore()

    def add(self, message: str, user_id: str, metadata: Dict = None) -> Dict:
        """Add a memory entry."""
        # FileMemoryStore.add() expects positional args: message, user_id, metadata
        # Call with positional arguments to match the signature
        return self._impl.add(message=message, user_id=user_id, metadata=metadata)

    def get_all(self, user_id: str) -> List[Dict]:
        """Get all memories for a user."""
        return self._impl.get_all(user_id)

    def search(self, query: str, user_id: str = None, limit: int = 5) -> List[Dict]:
        """Search memories by query."""
        return self._impl.search(query, user_id, limit)

    def delete(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        self._impl.delete(memory_id)
