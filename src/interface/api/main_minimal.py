"""Minimal main.py for WebSocket testing."""
import json
import logging
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.interface.api.dto.response import HealthResponse

logger = logging.getLogger(__name__)
settings = get_settings()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.websocket("/ws/chat")
    async def websocket_chat_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time chat communication."""
        logger.info("WebSocket connection attempt")

        await websocket.accept()
        logger.info("WebSocket connection accepted")

        patient_id = "unknown"

        try:
            # Wait for first message to get patient_id
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"WebSocket received: {message}")

            patient_id = message.get("patient_id", "unknown")

            # Send connected confirmation
            await websocket.send_json({
                "type": "connected",
                "patient_id": patient_id,
                "timestamp": datetime.now().isoformat()
            })

            # Message loop
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "chat_message":
                    content = message.get("content", "")
                    response = {
                        "type": "chat_response",
                        "content": f"收到：{content}",
                    }
                    await websocket.send_json(response)
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {patient_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
