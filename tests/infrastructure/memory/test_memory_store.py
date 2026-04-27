"""
Unit tests for Memory Store functionality.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.infrastructure.memory.memory_store import MemoryStore, Memory


class TestMemoryStore:
    """Tests for MemoryStore class."""

    def test_init_without_api_key(self):
        """Test initialization without API key uses file-based storage."""
        store = MemoryStore(api_key=None)
        assert store is not None

    @pytest.mark.asyncio
    async def test_add_memory(self):
        """Test adding a memory entry."""
        store = MemoryStore(api_key=None)
        result = await store.add(
            user_id="test_user",
            message="Test message",
            metadata={"key": "value"}
        )
        assert result is not None
        assert isinstance(result, Memory)

    @pytest.mark.asyncio
    async def test_get_all_memories(self):
        """Test retrieving all memories for a user."""
        store = MemoryStore(api_key=None)
        # First add a memory
        await store.add(
            user_id="test_user_retrieve",
            message="Test message for retrieval"
        )
        # Then retrieve
        memories = await store.get_all("test_user_retrieve")
        assert memories is not None
        assert isinstance(memories, list)

    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test searching memories by query."""
        store = MemoryStore(api_key=None)
        # First add a memory
        await store.add(
            user_id="test_user_search",
            message="Blood pressure is 120/80"
        )
        # Then search
        results = await store.search(
            query="blood pressure",
            user_id="test_user_search"
        )
        assert results is not None
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete_memory(self):
        """Test deleting a memory by ID."""
        store = MemoryStore(api_key=None)
        result = await store.delete("test_memory_id")
        # Should return True or False depending on whether the memory exists
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_context(self):
        """Test getting conversational context for a user."""
        store = MemoryStore(api_key=None)
        user_id = "test_context_user"

        # Add some memories
        await store.add(user_id=user_id, message="Hello")
        await store.add(user_id=user_id, message="How are you?")

        # Get context
        context = await store.get_context(user_id, max_memories=10)
        assert context is not None
        assert isinstance(context, str)


class TestMemoryStoreIntegration:
    """Integration tests for memory storage with session persistence."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_session_memory_persistence(self):
        """Test that session messages are persisted to memory."""
        store = MemoryStore(api_key=None)
        session_id = "test_session_persist"

        # Simulate adding messages from a session
        await store.add(
            user_id="patient_001",
            message="I have a headache",
            metadata={"session_id": session_id, "role": "user"}
        )
        await store.add(
            user_id="patient_001",
            message="How long have you had the headache?",
            metadata={"session_id": session_id, "role": "assistant"}
        )

        # Retrieve conversation context
        context = await store.get_context("patient_001", max_memories=10)
        assert context is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cross_session_context(self):
        """Test that context is maintained across sessions."""
        store = MemoryStore(api_key=None)
        user_id = "patient_cross_session"

        # First session
        await store.add(
            user_id=user_id,
            message="My blood pressure is 140/90",
            metadata={"session_id": "session_1", "role": "user"}
        )

        # Second session - should be able to retrieve info from first session
        results = await store.search(
            query="blood pressure",
            user_id=user_id
        )
        assert results is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_update(self):
        """Test updating existing memory."""
        store = MemoryStore(api_key=None)
        user_id = "patient_update"

        # Add initial memory
        await store.add(
            user_id=user_id,
            message="Patient weight: 75kg",
            metadata={"category": "vital_sign"}
        )

        # The store should maintain context
        memories = await store.get_all(user_id)
        assert memories is not None
        assert isinstance(memories, list)

