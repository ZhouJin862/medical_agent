"""
Chat API routes.

Provides endpoints for chat and consultation operations.
"""
import logging
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse

from src.application.commands.consultation_commands import SendMessageCommand
from src.application.services.chat_service import ChatApplicationService
from src.application.services.consultation_service import ConsultationApplicationService
from src.interface.api.dto.request import ChatRequest, CloseConsultationRequest
from src.interface.api.dto.response import ChatResponse, MessageResponse, ConsultationSummary
from src.interface.api.dependencies import get_chat_service, get_consultation_service
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


@router.post("/send", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(
    request: ChatRequest,
    chat_service: ChatApplicationService = Depends(get_chat_service),
) -> ChatResponse:
    """
    Send a message and get AI response.

    Args:
        request: Chat request with patient_id, message_content, and optional consultation_id
        chat_service: Injected chat service

    Returns:
        Chat response with consultation_id, user_message, and ai_response
    """
    try:
        command = SendMessageCommand(
            patient_id=request.patient_id,
            message_content=request.message_content,
            consultation_id=request.consultation_id,
        )

        result = await chat_service.send_message(
            patient_id=command.patient_id,
            message_content=command.message_content,
            consultation_id=command.consultation_id,
        )

        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consultations/{consultation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    consultation_id: str,
    limit: int = 100,
    consultation_service: ConsultationApplicationService = Depends(get_consultation_service),
) -> list[MessageResponse]:
    """
    Get messages for a consultation.

    Args:
        consultation_id: Consultation identifier
        limit: Maximum number of messages to return
        consultation_service: Injected consultation service

    Returns:
        List of messages
    """
    messages = await consultation_service.get_consultation_messages(
        consultation_id=consultation_id,
        limit=limit,
    )

    return [MessageResponse(**msg) for msg in messages]


@router.post("/consultations/{consultation_id}/close", status_code=status.HTTP_200_OK)
async def close_consultation(
    consultation_id: str,
    consultation_service: ConsultationApplicationService = Depends(get_consultation_service),
) -> JSONResponse:
    """
    Close a consultation session.

    Args:
        consultation_id: Consultation identifier
        consultation_service: Injected consultation service

    Returns:
        Success confirmation
    """
    result = await consultation_service.close_consultation(
        consultation_id=consultation_id,
    )

    return JSONResponse(
        content={"success": result, "consultation_id": consultation_id}
    )


@router.get("/consultations/active/{patient_id}", response_model=ConsultationSummary | None)
async def get_active_consultation(
    patient_id: str,
    consultation_service: ConsultationApplicationService = Depends(get_consultation_service),
) -> ConsultationSummary | None:
    """
    Get active consultation for a patient.

    Args:
        patient_id: Patient identifier
        consultation_service: Injected consultation service

    Returns:
        Active consultation or None
    """
    consultation = await consultation_service.get_active_consultation(
        patient_id=patient_id,
    )

    return ConsultationSummary(**consultation) if consultation else None


# Create v1 router for backward compatibility
v1_router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@v1_router.get("/sessions/{patient_id}")
async def get_chat_sessions(
    patient_id: str,
) -> dict:
    """
    Get all chat sessions for a patient.

    Args:
        patient_id: Patient identifier

    Returns:
        Dictionary with sessions list and total count
    """
    # Get project root from current file location
    # chat.py is at: src/interface/api/routes/chat.py
    # Project root is 5 levels up from routes/
    current_file = Path(__file__).resolve()
    base_dir = current_file.parent.parent.parent.parent.parent
    sessions_dir = base_dir / "data" / "sessions"

    sessions = {}

    logger.info(f"DEBUG: current_file: {current_file}")
    logger.info(f"DEBUG: base_dir: {base_dir}")
    logger.info(f"DEBUG: sessions_dir: {sessions_dir}")
    logger.info(f"DEBUG: sessions_dir exists: {sessions_dir.exists()}")

    if sessions_dir.exists():
        try:
            # Read all session files for this patient
            for session_file in sessions_dir.glob("session_*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)

                    # Only include sessions for this patient
                    if session_data.get("patient_id") != patient_id:
                        continue

                    session_id = session_data.get("session_id")
                    messages = session_data.get("messages", [])

                    if not session_id:
                        continue

                    # Get last message for preview
                    last_message = ""
                    if messages:
                        last_msg = messages[-1]
                        content = last_msg.get("content", "")
                        # Truncate long messages
                        last_message = content[:50] + "..." if len(content) > 50 else content

                    sessions[session_id] = {
                        "session_id": session_id,
                        "patient_id": patient_id,
                        "message_count": len(messages),
                        "created_at": session_data.get("created_at", ""),
                        "updated_at": session_data.get("updated_at", ""),
                        "last_message": last_message,
                    }

                except Exception as e:
                    logger.warning(f"Failed to read session file {session_file}: {e}")
                    continue

            logger.info(f"Found {len(sessions)} sessions for {patient_id}")

        except Exception as e:
            logger.error(f"Failed to load sessions for {patient_id}: {e}")
            import traceback
            traceback.print_exc()

    # Sort by updated_at descending
    session_list = sorted(
        sessions.values(),
        key=lambda s: s.get("updated_at", ""),
        reverse=True
    )

    return {
        "patient_id": patient_id,
        "sessions": session_list,
        "total_count": len(session_list),
        "_debug": {
            "code_version": "v2",
            "sessions_dir": str(sessions_dir),
            "dir_existed": sessions_dir.exists(),
            "sessions_found": len(sessions),
        }
    }


@v1_router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
) -> dict:
    """
    Get all messages for a specific session.

    Args:
        session_id: Session identifier

    Returns:
        Dictionary with messages list
    """
    # Get project root from current file location (5 levels up from routes/)
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    sessions_dir = base_dir / "data" / "sessions"

    # Find the session file
    session_file = sessions_dir / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        messages = []
        for msg in session_data.get("messages", []):
            messages.append({
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp"),
            })

        return {
            "session_id": session_id,
            "patient_id": session_data.get("patient_id", ""),
            "created_at": session_data.get("created_at", ""),
            "updated_at": session_data.get("updated_at", ""),
            "messages": messages,
        }

    except Exception as e:
        logger.error(f"Failed to read session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load session: {str(e)}"
        )


@v1_router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
) -> dict:
    """
    Delete a session and all its messages.

    Args:
        session_id: Session identifier

    Returns:
        Success confirmation
    """
    # Get project root from current file location (5 levels up from routes/)
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    sessions_dir = base_dir / "data" / "sessions"

    # Find the session file
    session_file = sessions_dir / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    try:
        # Delete the session file
        session_file.unlink()
        logger.info(f"Deleted session {session_id}")

        return {
            "success": True,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )


@v1_router.get("/debug/paths")
async def debug_paths() -> dict:
    """Debug endpoint to check path resolution."""
    print("[PRINT] debug_paths called!")
    current_file = Path(__file__).resolve()
    base_dir = current_file.parent.parent.parent.parent.parent
    memories_dir = base_dir / "data" / "memories"

    return {
        "current_file": str(current_file),
        "base_dir": str(base_dir),
        "memories_dir": str(memories_dir),
        "memories_dir_exists": memories_dir.exists(),
        "parent_levels": {
            "level1": str(current_file.parent),
            "level2": str(current_file.parent.parent),
            "level3": str(current_file.parent.parent.parent),
            "level4": str(current_file.parent.parent.parent.parent),
            "level5": str(current_file.parent.parent.parent.parent.parent),
        },
        "test_code_loaded": True  # Add this to verify new code
    }


@v1_router.get("/test/new")
async def test_new_endpoint() -> dict:
    """Test endpoint to verify new code is running."""
    return {
        "test": "NEW_ENDPOINT_WORKING",
        "timestamp": "2025-03-25",
    }
