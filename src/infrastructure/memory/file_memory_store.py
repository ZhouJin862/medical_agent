"""
File-based Memory Store - Persistent memory storage.

Uses JSON files to store conversation history on disk.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FileMemoryStore:
    """
    File-based memory store for persistent conversation history.

    Stores conversations as JSON files in the data/memories directory.
    """

    def __init__(self, storage_dir: str = "data/memories"):
        """Initialize the file-based memory store."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileMemoryStore initialized with directory: {self.storage_dir}")

    def _get_user_file(self, user_id: str) -> Path:
        """Get the memory file path for a user."""
        # Sanitize user_id to make it safe for filenames
        safe_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in user_id)
        return self.storage_dir / f"{safe_id}.json"

    def add(self, message: str, user_id: str, metadata: Dict = None) -> Dict:
        """Add a memory entry."""
        import uuid
        import time

        file_path = self._get_user_file(user_id)

        # Load existing memories
        memories = []
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    memories = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")

        # Add new memory
        memory_id = str(uuid.uuid4())
        entry = {
            "id": memory_id,
            "memory": message,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "timestamp": time.time(),
        }
        memories.append(entry)

        # Debug log metadata
        logger.info(f"FileMemoryStore.add() - Saving memory with metadata keys: {list((metadata or {}).keys())}")
        if metadata and metadata.get('role') == 'assistant':
            logger.info(f"  Assistant metadata: intent={metadata.get('intent')}, skill={metadata.get('suggested_skill')}, confidence={metadata.get('confidence')}")

        # Save to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

        return entry

    def get_all(self, user_id: str) -> List[Dict]:
        """Get all memories for a user."""
        file_path = self._get_user_file(user_id)

        if not file_path.exists():
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                memories = json.load(f)
                return memories
        except Exception as e:
            logger.error(f"Failed to load memories for {user_id}: {e}")
            return []

    def search(self, query: str, user_id: str = None, limit: int = 5) -> List[Dict]:
        """Search memories by query."""
        query_lower = query.lower()
        results = []

        if user_id:
            # Search specific user
            memories = self.get_all(user_id)
            for mem in memories:
                if query_lower in mem.get("memory", "").lower():
                    results.append(mem)
                    if len(results) >= limit:
                        break
        else:
            # Search all users
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        memories = json.load(f)
                        for mem in memories:
                            if query_lower in mem.get("memory", "").lower():
                                results.append(mem)
                                if len(results) >= limit:
                                    break
                                break
                except Exception as e:
                    logger.error(f"Failed to search {file_path}: {e}")

        return results

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID across all users."""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        memories = json.load(f)

                    original_count = len(memories)
                    memories = [m for m in memories if m.get("id") != memory_id]

                    if len(memories) < original_count:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(memories, f, ensure_ascii=False, indent=2)
                        return True
                except Exception as e:
                    logger.error(f"Failed to update {file_path}: {e}")

            return False
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    def get_conversation_context(self, user_id: str, max_messages: int = 20) -> str:
        """Get formatted conversation context for LLM."""
        memories = self.get_all(user_id)

        if not memories:
            return ""

        # Take the most recent messages
        recent_memories = memories[-max_messages:]

        context_parts = []
        for mem in recent_memories:
            role = mem.get("metadata", {}).get("role", "unknown")
            content = mem.get("memory", "")
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)


# Global instance
_file_store_instance = None


def get_file_memory_store() -> FileMemoryStore:
    """Get or create the global file memory store instance."""
    global _file_store_instance
    if _file_store_instance is None:
        _file_store_instance = FileMemoryStore()
    return _file_store_instance
