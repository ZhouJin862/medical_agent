"""
Session Manager - Manages conversation state and history.

Provides session-based conversation management with memory integration
and file-based persistence to work across FastAPI reloads.
"""
import logging
import uuid
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator
from pathlib import Path
from dataclasses import dataclass, field, asdict

from src.infrastructure.memory import MemoryStore

logger = logging.getLogger(__name__)

# Directory for session persistence - use absolute path from project root
# Get the project root directory (parent of src directory)
_CURRENT_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _CURRENT_FILE.parent.parent.parent.parent
_SESSIONS_DIR = _PROJECT_ROOT / "data" / "sessions"
_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Sessions directory: {_SESSIONS_DIR}")


@dataclass
class SessionMessage:
    """A message in a conversation session."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """A conversation session."""
    session_id: str
    patient_id: str
    messages: List[SessionMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the session."""
        self.messages.append(SessionMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        ))
        self.updated_at = datetime.now()

    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for LLM context."""
        recent_messages = self.messages[-limit:] if limit else self.messages
        return [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ]

    def get_context_summary(self) -> str:
        """Get a summary of the conversation context."""
        if not self.messages:
            return ""

        context_parts = []
        for msg in self.messages[-5:]:
            role_label = "用户" if msg.role == "user" else "助手"
            context_parts.append(f"{role_label}: {msg.content}")

        return "\n".join(context_parts)


class SessionManager:
    """
    Manager for conversation sessions.

    Provides session creation, retrieval, and message management
    with persistence through memory store.
    """

    def __init__(self, memory_store: Optional[MemoryStore] = None):
        """
        Initialize the session manager.

        Args:
            memory_store: Optional memory store for persistence
        """
        self._sessions: Dict[str, Session] = {}
        self._memory_store = memory_store or MemoryStore()
        logger.info("SessionManager initialized")

    def create_session(
        self,
        patient_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new conversation session.

        Args:
            patient_id: Patient identifier
            session_id: Optional session ID (auto-generated if not provided)
            metadata: Optional session metadata

        Returns:
            Created session
        """
        session_id = session_id or f"session_{uuid.uuid4().hex[:16]}"
        session = Session(
            session_id=session_id,
            patient_id=patient_id,
            metadata=metadata or {}
        )
        self._sessions[session_id] = session
        logger.info(f"Created session {session_id} for patient {patient_id}")

        # Save to disk
        self._save_session_to_disk(session)

        return session

    def update_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> None:
        """Update session metadata and persist to disk."""
        session = self.get_session(session_id)
        if session:
            session.metadata.update(metadata)
            self._save_session_to_disk(session)

    def _save_session_to_disk(self, session: Session) -> None:
        """Save session to disk for persistence."""
        try:
            session_file = _SESSIONS_DIR / f"{session.session_id}.json"
            session_data = {
                'session_id': session.session_id,
                'patient_id': session.patient_id,
                'messages': [
                    {
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'metadata': msg.metadata
                    }
                    for msg in session.messages
                ],
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'metadata': session.metadata
            }

            logger.info(f"Saving session {session.session_id} to disk")

            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id} to disk: {e}")
            import traceback
            traceback.print_exc()

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        First tries memory, then falls back to disk storage.

        Args:
            session_id: Session identifier

        Returns:
            Session if found, None otherwise
        """
        # Check memory first
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load from disk
        session_file = _SESSIONS_DIR / f"{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                # Reconstruct Session object
                session = Session(
                    session_id=session_data['session_id'],
                    patient_id=session_data['patient_id'],
                    messages=[
                        SessionMessage(
                            role=msg['role'],
                            content=msg['content'],
                            timestamp=datetime.fromisoformat(msg['timestamp']),
                            metadata=msg.get('metadata', {})
                        )
                        for msg in session_data.get('messages', [])
                    ],
                    created_at=datetime.fromisoformat(session_data['created_at']),
                    updated_at=datetime.fromisoformat(session_data['updated_at']),
                    metadata=session_data.get('metadata', {})
                )

                # Cache in memory
                self._sessions[session_id] = session
                logger.info(f"Loaded session {session_id} from disk with {len(session.messages)} messages")
                return session
            except Exception as e:
                logger.error(f"Failed to load session {session_id} from disk: {e}")

        return None

    def get_or_create_session(
        self,
        session_id: Optional[str],
        patient_id: str
    ) -> Session:
        """
        Get existing session or create new one.

        Args:
            session_id: Optional session ID
            patient_id: Patient identifier

        Returns:
            Session (existing or new)
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session

        # Pass session_id to create_session so it uses the provided ID instead of generating a new one
        return self.create_session(patient_id, session_id=session_id)

    def add_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Session]:
        """
        Add a user message to a session.

        Args:
            session_id: Session identifier
            content: Message content
            metadata: Optional metadata

        Returns:
            Updated session if found, None otherwise
        """
        session = self.get_session(session_id)
        if session:
            session.add_message("user", content, metadata)

            # Save to memory store
            try:
                import asyncio
                asyncio.create_task(self._memory_store.add(
                    user_id=session.patient_id,
                    message=content,
                    metadata={"role": "user", "session_id": session_id, **(metadata or {})}
                ))
            except Exception as e:
                logger.warning(f"Failed to save message to memory: {e}")

            # Save to disk
            self._save_session_to_disk(session)

        return session

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Session]:
        """
        Add an assistant message to a session.

        Args:
            session_id: Session identifier
            content: Message content
            metadata: Optional metadata

        Returns:
            Updated session if found, None otherwise
        """
        session = self.get_session(session_id)
        if session:
            session.add_message("assistant", content, metadata)

            # Save to memory store
            try:
                import asyncio
                asyncio.create_task(self._memory_store.add(
                    user_id=session.patient_id,
                    message=content,
                    metadata={"role": "assistant", "saved_by": "session_manager", "session_id": session_id, **(metadata or {})}
                ))
            except Exception as e:
                logger.warning(f"Failed to save message to memory: {e}")

            # Save to disk
            self._save_session_to_disk(session)

        return session

    async def load_session_from_memory(self, session_id: str, patient_id: str) -> Optional[Session]:
        """
        Load a session from memory store.

        Args:
            session_id: Session identifier
            patient_id: Patient identifier

        Returns:
            Loaded session if found, None otherwise
        """
        try:
            memories = await self._memory_store.get_all(patient_id)

            # Filter memories for this session
            session_memories = [
                mem for mem in memories
                if mem.get("metadata", {}).get("session_id") == session_id
            ]

            if not session_memories:
                return None

            # Create session from memories
            session = Session(
                session_id=session_id,
                patient_id=patient_id
            )

            for mem in sorted(session_memories, key=lambda m: m.get("created_at", "")):
                role = mem.get("metadata", {}).get("role", "user")
                content = mem.get("memory", "")
                session.add_message(role, content)

            self._sessions[session_id] = session
            logger.info(f"Loaded session {session_id} with {len(session.messages)} messages")
            return session

        except Exception as e:
            logger.error(f"Failed to load session from memory: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False

    def get_active_sessions(self, patient_id: Optional[str] = None) -> List[Session]:
        """
        Get all active sessions, optionally filtered by patient.

        Args:
            patient_id: Optional patient filter

        Returns:
            List of active sessions
        """
        sessions = list(self._sessions.values())
        if patient_id:
            sessions = [s for s in sessions if s.patient_id == patient_id]
        return sessions


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        logger.info(f"Created new SessionManager instance: {id(_session_manager)}")
    else:
        logger.info(f"Reusing existing SessionManager instance: {id(_session_manager)}, sessions: {list(_session_manager._sessions.keys())}")
    return _session_manager


def reset_session_manager():
    """Reset the global session manager instance (useful for testing)."""
    global _session_manager
    _session_manager = None
