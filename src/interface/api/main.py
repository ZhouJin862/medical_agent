"""
FastAPI application entry point.

Creates and configures the FastAPI application with all routes,
middleware, and error handlers.
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from src.config.settings import get_settings
from src.interface.api.middleware import setup_error_handlers, AuthenticationMiddleware
from src.interface.api.routes import chat, health, plan, consultation, skills, rules
from src.interface.api.routes import rule_enhanced_skills
from src.interface.api.routes import streaming_chat
from src.interface.api.routes import skills_v2
from src.interface.api.routes import skills_agent
from src.interface.api.routes import composite_skills
from src.interface.api.routes import skill_packages
from src.interface.api.routes import prompts
from src.interface.api.routes import assessment
from src.interface.api.routes import questionnaire
from src.interface.api.routes import insight
from src.interface.api.dto.response import HealthResponse
from src.infrastructure.database import init_database, close_database

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("Debug mode: %s", settings.debug)

    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Continue anyway - tables might already exist

    yield

    # Shutdown
    logger.info("Shutting down application")
    # Close database connections
    await close_database()


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Medical Agent API - AI-powered health consultation service",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup authentication middleware (for production)
    # app.add_middleware(AuthenticationMiddleware)

    # Setup error handlers
    # setup_error_handlers(app)

    # Include routers
    app.include_router(health.router)
    app.include_router(streaming_chat.router)
    app.include_router(chat.router)
    app.include_router(chat.v1_router)  # v1 API for backward compatibility
    app.include_router(plan.router)
    app.include_router(consultation.router)
    app.include_router(skills.router)
    app.include_router(rules.router)
    app.include_router(rule_enhanced_skills.router)
    app.include_router(skills_v2.router)
    app.include_router(skills_agent.router)
    app.include_router(composite_skills.router)
    app.include_router(skill_packages.router)
    app.include_router(prompts.router)
    app.include_router(assessment.router)
    app.include_router(questionnaire.router)
    app.include_router(insight.router)

    # Add health check route
    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            services={
                "database": "connected",  # Would check actual connection
                "redis": "connected",     # Would check actual connection
            },
        )

    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs_url": "/api/docs",
        }

    # Test agent endpoint
    @app.post("/api/test-agent")
    async def test_agent(request: dict):
        """Test the agent directly."""
        try:
            from src.infrastructure.agent.skills_integration import SkillsIntegratedAgent

            agent = SkillsIntegratedAgent()
            result = await agent.process(
                user_input=request.get("input", "test"),
                patient_id=request.get("patient_id", "test-001"),
            )

            return {
                "status": result.status.value,
                "intent": result.intent.value if result.intent else None,
                "response_length": len(result.final_response) if result.final_response else 0,
                "response_preview": result.final_response[:100] if result.final_response else None,
            }
        except Exception as e:
            return {"error": str(e)}

    # Add WebSocket endpoint for chat
    @app.websocket("/ws/chat")
    async def websocket_chat_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time chat communication.

        Message format:
        {
            "type": "connect" | "chat_message" | "ping",
            "patient_id": string,
            "message_id"?: string,
            "content"?: string
        }
        """
        logger.info("WebSocket connection attempt")

        # Accept the connection FIRST before any receive operations
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        patient_id = "unknown"

        try:
            # Wait for first message to get patient_id
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"WebSocket received: {message}")

            patient_id = message.get("patient_id", "unknown")
            logger.info(f"Patient identified: {patient_id}")

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
                    # Handle chat message
                    await handle_websocket_message(websocket, message, patient_id)
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "connect":
                    # Reconnection attempt
                    patient_id = message.get("patient_id", patient_id)
                    await websocket.send_json({
                        "type": "connected",
                        "patient_id": patient_id
                    })

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {patient_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            try:
                await websocket.close()
            except:
                pass

    logger.info("FastAPI application created")

    return app


async def handle_websocket_message(websocket: WebSocket, message: dict, patient_id: str):
    """Handle incoming WebSocket message using the agent."""
    message_id = message.get("message_id", f"msg-{datetime.now().timestamp()}")
    content = message.get("content", "")

    logger.info(f"Processing message from {patient_id}: {content}")

    try:
        # Import SkillsIntegratedAgent
        from src.infrastructure.agent.skills_integration import SkillsIntegratedAgent

        # Create agent and process the message
        agent = SkillsIntegratedAgent()
        result_state = await agent.process(
            user_input=content,
            patient_id=patient_id,
        )

        # Extract response
        response_content = result_state.final_response or "抱歉，我无法处理您的请求。"

        # Prepare structured output if available
        structured_output = None
        if result_state.structured_output:
            structured_output = result_state.structured_output

        # Send response
        response = {
            "type": "chat_response",
            "message_id": f"response-{datetime.now().timestamp()}",
            "original_message_id": message_id,
            "content": response_content,
            "timestamp": datetime.now().isoformat(),
            "intent": result_state.intent.value if result_state.intent else "general",
            "confidence": result_state.confidence,
            "structured_output": structured_output,
        }

        await websocket.send_json(response)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()

        # Send error response
        error_response = {
            "type": "chat_response",
            "message_id": f"response-{datetime.now().timestamp()}",
            "original_message_id": message_id,
            "content": f"处理您的消息时出错: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "intent": "error",
            "confidence": 0.0,
            "error": str(e),
        }
        await websocket.send_json(error_response)


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.interface.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
