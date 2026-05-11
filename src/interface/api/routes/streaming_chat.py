"""
Streaming Chat API Routes.

Provides Server-Sent Events (SSE) streaming chat interface
with session-based conversation management and automatic skill triggering.
"""
import asyncio
import json
import logging
import re
from typing import AsyncIterator, Optional, Dict, Any

from src.interface.api.routes.assessment import _extract_structured_result, transform_abnormal_indicators

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.interface.api.dto.request import StreamingChatRequest
from src.interface.api.dto.response import (
    StreamingChatStartChunk,
    StreamingChatTokenChunk,
    StreamingChatEndChunk,
    StreamingChatErrorChunk,
)
from src.infrastructure.session.session_manager import SessionManager, get_session_manager
from src.infrastructure.agent.state import IntentType
from src.interface.api.dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _extract_party_id(user_input: str) -> Optional[str]:
    """
    Extract party_id (客户号) from user input.

    Args:
        user_input: User's message content

    Returns:
        Extracted party_id or None
    """
    patterns = [
        r'客户号[是为:：]\s*([A-Za-z0-9]+)',
        r'partyId[是为:：]\s*([A-Za-z0-9]+)',
        r'party\s*id[是为:：]\s*([A-Za-z0-9]+)',
        r'客户编号[是为:：]\s*([A-Za-z0-9]+)',
        r'编号[是为:：]\s*([A-Za-z0-9]{8,})',
        r'客户号\s*([A-Za-z0-9]{8,})',
        r'client\s*id[是为:：]\s*([A-Za-z0-9]{8,})',  # Added for "Client ID" format
        r'客户号\s*is\s*[:：]?\s*([A-Za-z0-9]+)',  # For "客户号 is : 1246243516186829"
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            party_id = match.group(1)
            logger.info(f"Extracted party_id from user input: {party_id}")
            return party_id
    return None


async def _get_health_data_from_pingan(party_id: str) -> Optional[Dict[str, Any]]:
    """
    Get health data from Ping An health archive API.

    Args:
        party_id: Customer/patient identifier

    Returns:
        Health data dictionary or None if failed
    """
    try:
        # Import the function directly from the MCP server module
        # This bypasses the MCP stdio communication layer
        from mcp_servers.profile_server.tools import get_health_data

        health_data = await get_health_data(party_id=party_id)

        # Check if the API call was successful
        # The response may have the code at top level (error case) or in _api_response (success case)
        api_code = health_data.get("code") or health_data.get("_api_response", {}).get("code")

        if health_data and api_code == "S000000":
            logger.info(f"Successfully retrieved health data for party_id: {party_id}")
            # Log what data we got
            if "age" in health_data:
                logger.info(f"  - Age: {health_data['age']}")
            if "gender" in health_data:
                logger.info(f"  - Gender: {health_data['gender']}")
            if "diseaseHistory" in health_data:
                logger.info(f"  - Diagnoses: {health_data['diseaseHistory']}")
            if "diseaseLabels" in health_data:
                logger.info(f"  - Disease labels: {health_data['diseaseLabels']}")
            if "systolicPressure" in health_data:
                logger.info(f"  - BP: {health_data['systolicPressure']}/{health_data.get('diastolicPressure')}")
            return health_data
        else:
            logger.warning(f"Ping An API returned non-success: code={api_code}, error={health_data.get('error', health_data.get('info', 'Unknown'))}")
            return None

    except Exception as e:
        logger.error(f"Failed to get health data from Ping An: {e}")
        import traceback
        traceback.print_exc()
        return None


def _format_modules_to_markdown(modules: Dict[str, Any]) -> str:
    """Format skill modules dict into structured markdown report for SSE streaming.

    Each module value may be:
    - str: pre-formatted markdown, output directly
    - dict/list: rendered via generic recursive formatting
    """
    lines = []

    def _format_value(val: Any, indent: int = 0) -> None:
        """Recursively format a value into lines."""
        prefix = "  " * indent
        if isinstance(val, str):
            lines.append(f"{prefix}{val}")
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    lines.append(f"{prefix}- {item}")
                elif isinstance(item, dict):
                    parts = [f"{v}" for v in item.values() if isinstance(v, (str, int, float))]
                    if parts:
                        lines.append(f"{prefix}- {' | '.join(str(p) for p in parts)}")
                    else:
                        for k, v in item.items():
                            _format_value(v, indent + 1)
                else:
                    lines.append(f"{prefix}- {item}")
        elif isinstance(val, dict):
            for k, v in val.items():
                label = k.replace("_", " ").title()
                if isinstance(v, (str, int, float)):
                    lines.append(f"{prefix}- **{label}**: {v}")
                elif isinstance(v, (list, dict)):
                    lines.append(f"{prefix}**{label}:**")
                    _format_value(v, indent + 1)
                else:
                    lines.append(f"{prefix}- **{label}**: {v}")

    for section_name, section_content in modules.items():
        if not section_content:
            continue
        if isinstance(section_content, str):
            lines.append(section_content)
            lines.append("")
        else:
            _format_value(section_content)
            lines.append("")

    report = "\n".join(lines)
    return report if report.strip() else "评估完成，但未生成报告内容。"


def _build_health_report(sr: Dict[str, Any]) -> str:
    """Build a formatted health assessment report from structured_result.

    Generates a markdown report with all modules (population classification,
    abnormal indicators, disease prediction, intervention prescriptions,
    risk warnings) instead of returning raw JSON to the user.
    """
    lines = []

    # --- Population Classification ---
    pc = sr.get("population_classification", {})
    category = pc.get("primary_category", "")
    if category:
        lines.append(f"## 健康人群分组：**{category}**")
        basis_list = pc.get("grouping_basis", [])
        if basis_list:
            lines.append("")
            lines.append("**分组依据：**")
            for b in basis_list:
                if isinstance(b, dict):
                    disease = b.get("disease", "")
                    note = b.get("note", "")
                    disease_type = b.get("type", "")
                    level = b.get("level", "")
                    if note:
                        detail = f"- {disease}：{note}"
                    elif disease_type and level:
                        detail = f"- {disease}：{disease_type}{level}"
                    elif level:
                        detail = f"- {disease}：{level}"
                    else:
                        detail = f"- {disease}"
                    lines.append(detail)
        lines.append("")

    # --- Abnormal Indicators & Warnings ---
    abn = sr.get("abnormal_indicators", [])

    # Support both old flat list and new {indicators, warnings} structure
    if isinstance(abn, dict):
        indicators = abn.get("indicators", [])
        warnings = abn.get("warnings", [])
    elif isinstance(abn, list):
        indicators = abn
        warnings = []
    else:
        indicators = []
        warnings = []

    if indicators:
        lines.append("## 异常指标")
        lines.append("")
        for a in indicators:
            name = a.get("name", "")
            value = a.get("value", "")
            unit = a.get("unit", "")
            ref = a.get("reference_range", a.get("reference", ""))
            severity = a.get("severity", "")
            line = f"- **{name}**：{value} {unit}"
            if ref:
                line += f"（参考范围：{ref}）"
            if severity:
                line += f" — {severity}"
            lines.append(line)
        lines.append("")

    if warnings:
        lines.append("## 异常预警")
        lines.append("")
        for w in warnings:
            title = w.get("title", "")
            tip = w.get("tip", "")
            indices = w.get("indicator_indices", [])
            # Show which indicators this warning relates to
            related = []
            for idx in indices:
                if 0 <= idx < len(indicators):
                    related.append(indicators[idx].get("name", ""))
            line = f"- ⚠️ **{title}**"
            if related:
                line += f"（关联指标：{'、'.join(related)}）"
            lines.append(line)
            if tip:
                lines.append(f"  > {tip}")
        lines.append("")

    # --- Disease Prediction ---
    dp = sr.get("disease_prediction", [])
    if dp:
        lines.append("## 疾病风险预测")
        lines.append("")
        for p in dp:
            name = p.get("disease_name", "")
            prob = p.get("probability", "")
            level = p.get("risk_level", "")
            timeframe = p.get("timeframe", "")
            model = p.get("risk_model", "")
            factors = p.get("key_contributing_factors", [])
            line = f"- **{name}**"
            if level:
                line += f"：{level}"
            if prob:
                line += f"（发生概率 {prob}）"
            if timeframe:
                line += f"，{timeframe}风险"
            lines.append(line)
            if model:
                lines.append(f"  - 评估模型：{model}")
            if factors:
                lines.append(f"  - 主要风险因素：{'、'.join(factors)}")
        lines.append("")

    # --- Risk Warnings ---
    rw = sr.get("risk_warnings", [])
    if rw:
        lines.append("## 风险提示")
        lines.append("")
        for w in rw:
            title = w.get("title", "")
            desc = w.get("description", "")
            level = w.get("level", "")
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(level, "⚠️")
            line = f"- {icon} **{title}**"
            if desc:
                line += f"：{desc}"
            lines.append(line)
        lines.append("")

    # --- Intervention Prescriptions ---
    ip = sr.get("intervention_prescriptions", [])
    if ip:
        lines.append("## 干预建议")
        lines.append("")
        # Group by type
        type_order = ["diet", "exercise", "sleep", "monitoring", "medication"]
        type_labels = {
            "diet": "饮食处方",
            "exercise": "运动处方",
            "sleep": "睡眠处方",
            "monitoring": "监测建议",
            "medication": "药物建议",
        }
        by_type: Dict[str, list] = {}
        for p in ip:
            t = p.get("type", "other")
            by_type.setdefault(t, []).append(p)

        for t in type_order:
            items = by_type.get(t, [])
            if not items:
                continue
            label = type_labels.get(t, t)
            lines.append(f"### {label}")
            for item in items:
                contents = item.get("content", [])
                if isinstance(contents, list):
                    for c in contents:
                        lines.append(f"- {c}")
                elif isinstance(contents, str):
                    lines.append(f"- {contents}")
            lines.append("")

    # --- Recommended Data Collection ---
    rdc = sr.get("recommended_data_collection", [])
    if rdc:
        lines.append("## 建议补充检查")
        lines.append("")
        for r in rdc:
            item = r.get("item", "")
            reason = r.get("reason", "")
            priority = r.get("priority", "")
            if item:
                line = f"- {item}"
                if reason:
                    line += f"：{reason}"
                if priority:
                    line += f"（{priority}）"
                lines.append(line)

    report = "\n".join(lines)
    return report if report else "评估完成，但未生成报告内容。"


def _format_retrieved_data_info(health_data: Dict[str, Any]) -> str:
    """
    Format retrieved health data into a human-readable message.

    Args:
        health_data: Health data from Ping An API

    Returns:
        Formatted message string
    """
    api_data = health_data.get("data", health_data)
    info_parts = ["### IMPORTANT: User health data already retrieved from Ping An health archive\n\n"]

    if "age" in api_data:
        info_parts.append(f"- Age: {api_data['age']} years old")

    if "diseaseHistory" in api_data and api_data["diseaseHistory"]:
        diagnosis_codes = [code for code in api_data["diseaseHistory"] if code]
        if diagnosis_codes:
            info_parts.append(f"- Medical history codes: {', '.join(diagnosis_codes)}")

    if "diseaseLabels" in api_data and api_data["diseaseLabels"]:
        info_parts.append(f"- Current diseases: {', '.join(api_data['diseaseLabels'])}")

    if "sportRecords" in api_data and api_data["sportRecords"]:
        info_parts.append("- Exercise records: Available")

    info_parts.append("\n**CRITICAL**: Do NOT ask the user to provide this information again. Use the retrieved data above for health assessment.")

    return "\n".join(info_parts)


async def _generate_llm_response_stream(
    user_input: str,
    patient_id: str,
    conversation_history: list[dict],
    retrieved_data_info: str = "",
) -> AsyncIterator[str]:
    """
    Generate streaming LLM response using Anthropic API.

    Args:
        user_input: User's input message
        patient_id: Patient identifier
        conversation_history: Previous conversation messages

    Yields:
        Response tokens as they are generated
    """
    try:
        import anthropic

        settings = get_settings()

        if not settings.anthropic_api_key:
            # Fallback response when no API key
            yield f"抱歉，系统未配置 LLM API 密钥。您的消息：{user_input}"
            return

        # Build messages for API
        messages = []

        # Add conversation history (last 10 messages)
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current user message
        messages.append({"role": "user", "content": user_input})

        # Build system prompt (loaded from DB with fallback)
        from src.domain.shared.services.system_prompt_service import get_system_prompt_service
        prompt_service = get_system_prompt_service()
        base_system_prompt = await prompt_service.get_prompt_with_fallback(
            "medical_assistant_streaming",
            fallback="""你是一个专业的健康管理助手，帮助用户进行健康评估、风险预测和健康管理。

你的职责：
1. 回答用户的健康相关问题
2. **记住用户之前提供的信息**（姓名、年龄、症状、指标等）
3. **如果用户已经提供过基本信息，直接使用这些信息进行分析，不要再询问**
4. 提供个性化的健康建议
5. 在需要时建议用户咨询专业医生
6. 保持专业、友善的语气

**重要：请使用 Markdown 格式组织你的回答**

回答格式建议：
- 使用 ## 标题组织内容
- 使用 - 列表列出要点
- 使用 **粗体** 强调重要信息
- 使用 > 引用块给出提醒

**关于用户数据来源的优先级**：
- 系统自动从平安健康档案API获取的数据是**最权威的**，必须优先使用
- 当系统在提示中提供了"已从平安健康档案获取的数据"时，说明该用户的数据已经成功获取，**不应再当作新用户处理**
- 即使对话历史中出现过"客户号不匹配"或"新用户"的讨论，只要当前系统提示中包含了该用户的健康数据，就应以API数据为准
- 不要因为对话历史中的旧信息而质疑或忽略系统提供的API数据

请注意：
- 你不能替代专业医生的诊断
- 对于紧急医疗情况，建议用户立即就医
- 保持回答简洁明了但全面""",
        )

        # Include retrieved data info if available
        if retrieved_data_info:
            logger.info(f"Including retrieved_data_info in system prompt (length={len(retrieved_data_info)})")
            system_prompt = f"""{base_system_prompt}

{retrieved_data_info}

**特别提醒**:
1. 上面已经列出了从平安健康档案自动获取的信息。请直接使用这些信息进行分析，不要要求用户重复提供这些信息。
2. **当系统提供了平安API数据时，这些数据是最权威和最新的，必须优先于对话历史中的任何推断。** 即使对话历史中提到过"新用户"或"客户号不匹配"，只要本次系统提供了该客户号的健康数据，就说明数据获取成功，应直接使用这些数据进行评估。
3. 如果用户提供了客户号，说明他们的健康数据已经获取成功。"""
        else:
            logger.warning("No retrieved_data_info available, using base system prompt")
            system_prompt = base_system_prompt

        # Create Anthropic client
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url if settings.anthropic_base_url != "https://api.anthropic.com" else None,
        )

        # Generate streaming response
        with client.messages.stream(
            model=settings.model,
            max_tokens=2000,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        yield f"生成回复时出错：{str(e)}"


@router.post("/stream")
async def chat_stream(
    request: StreamingChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Streaming chat endpoint with session-based conversation.

    Uses Server-Sent Events (SSE) for real-time streaming response.

    Request:
    ```json
    {
        "session_id": "session_xxx",  // Optional - creates new session if not provided
        "patient_id": "patient_001",
        "message": "我今天血压有点高，150/95，需要担心吗？"
    }
    ```

    Response (SSE stream):
    ```
    data: {"type": "start", "session_id": "session_xxx", "timestamp": "2024-01-15T10:00:00"}

    data: {"type": "token", "content": "您", "timestamp": "2024-01-15T10:00:01"}
    data: {"type": "token", "content": "好", "timestamp": "2024-01-15T10:00:01"}
    data: {"type": "token", "content": "！", "timestamp": "2024-01-15T10:00:01"}
    ...

    data: {"type": "end", "full_response": "您好！...", "intent": "health_assessment", "timestamp": "2024-01-15T10:00:05"}
    ```

    Chunk types:
    - **start**: Stream started, includes session_id
    - **token**: Individual text token (streamed)
    - **end**: Stream complete, includes full response
    - **error**: Error occurred
    """
    # Get the global session manager singleton
    from src.infrastructure.session.session_manager import get_session_manager
    session_manager = get_session_manager()

    # Get or create session
    session = session_manager.get_or_create_session(
        session_id=request.session_id,
        patient_id=request.patient_id
    )

    # Add user message to session
    session_manager.add_user_message(
        session_id=session.session_id,
        content=request.message,
        metadata={"patient_id": request.patient_id}
    )

    async def stream_generator():
        """Generate SSE stream chunks with skill integration."""
        try:
            # Send start chunk
            start_chunk = StreamingChatStartChunk(
                type="start",
                session_id=session.session_id,
                timestamp=session.updated_at.isoformat()
            )
            yield f"data: {start_chunk.model_dump_json()}\n\n"

            # Extract party_id and get health data from Ping An API
            # Don't yield this yet - wait for agent response first
            retrieved_data_info = ""
            party_id = _extract_party_id(request.message)
            logger.info(f"Party ID extraction result: {party_id}")
            health_data = None
            if party_id:
                health_data = await asyncio.wait_for(
                    _get_health_data_from_pingan(party_id),
                    timeout=15.0  # 15s timeout for Ping An API
                )
                logger.info(f"Health data retrieval result: {health_data is not None}")
                if health_data:
                    retrieved_data_info = _format_retrieved_data_info(health_data)
                    logger.info(f"Formatted retrieved_data_info length: {len(retrieved_data_info)}, truthy: {bool(retrieved_data_info)}")
                    logger.info(f"Retrieved health data for party_id: {party_id}")
                    # NOTE: Don't yield yet - wait for agent to determine if we need to ask for more data

            # Get conversation history
            conversation_history = session.get_conversation_history(limit=10)
            conversation_context = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation_history[-5:]
            ])

            # Build enhanced patient context if data was retrieved
            # Note: SkillsIntegratedAgent will handle retrieved data through MCP, so we don't need to pass it manually

            logger.info(f"Using SkillsIntegratedAgent for processing request")

            # Process through SkillsIntegratedAgent (includes multi-skill orchestration)
            from src.infrastructure.agent.skills_integration import SkillsIntegratedAgent
            agent = SkillsIntegratedAgent()

            # Get previous patient_context from session metadata if available
            previous_patient_context = session.metadata.get("patient_context") if session.metadata else None
            if previous_patient_context:
                logger.info(f"Restored previous patient context with {len(previous_patient_context.get('vital_signs', {}))} vital signs")

            # Merge questionnaire answers into health_data if provided
            if request.questionnaire_answers:
                from src.infrastructure.agent.nodes.check_basic_questionnaire import map_questionnaire_answers_to_health_data
                if not health_data:
                    health_data = {}
                health_data.update(map_questionnaire_answers_to_health_data(request.questionnaire_answers))

            # Pass Ping An data to agent if available
            # Add timeout to prevent frontend from showing "thinking" forever
            try:
                agent_state = await asyncio.wait_for(
                    agent.process(
                        user_input=request.message,
                        patient_id=request.patient_id,
                        party_id=party_id,
                        ping_an_health_data=health_data if health_data else None,
                        previous_patient_context=previous_patient_context,  # Pass previous context
                        session_id=session.session_id,  # Pass session_id for memory isolation
                        require_basic_questionnaire=True,
                    ),
                    timeout=120.0  # 2 minute timeout for the entire agent pipeline
                )
            except asyncio.TimeoutError:
                logger.error(f"Agent process timed out after 120s for session {session.session_id}")
                # Send error and end events so frontend stops showing "thinking"
                error_chunk = StreamingChatErrorChunk(
                    type="error",
                    error="处理超时，请稍后重试。"
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                # Also send end event to properly close the stream
                end_chunk = StreamingChatEndChunk(
                    type="end",
                    full_response="抱歉，处理您的请求超时了，请稍后再试。",
                    intent="chat",
                    confidence=0.0,
                )
                yield f"data: {end_chunk.model_dump_json()}\n\n"
                return
            logger.info(f"Agent processing complete: intent={agent_state.intent}, skill={agent_state.suggested_skill}, confidence={agent_state.confidence}")

            # Extract structured_result from agent state (same logic as assessment.py)
            structured_result = _extract_structured_result(agent_state)

            # Transform abnormal_indicators into indicators + warnings
            transform_abnormal_indicators(structured_result)

            # LLM 生成个性化处方
            try:
                from src.domain.shared.services.prescription_generator import generate_prescriptions
                if structured_result:
                    structured_result["intervention_prescriptions"] = await generate_prescriptions(
                        structured_result, health_data or {}
                    )
            except Exception as e:
                logger.warning(f"Prescription generation failed in streaming, keeping script defaults: {e}")

            # Extract response and metadata from agent state
            skill_used = agent_state.suggested_skill
            intent = agent_state.intent.value if agent_state.intent else "chat"
            confidence = agent_state.confidence or 0.0

            # Build report: prefer modules markdown for package assessment, then structured_result report
            so = getattr(agent_state, 'structured_output', None)
            if isinstance(so, dict) and so.get("modules"):
                # Use skill raw modules markdown (structured markdown for SSE)
                full_response = _format_modules_to_markdown(so["modules"])
                logger.info("Using modules-based markdown as response")
            elif structured_result and structured_result.get("population_classification", {}).get("primary_category") not in ("", None):
                full_response = _build_health_report(structured_result)
                logger.info("Using structured report as response")
            else:
                full_response = agent_state.final_response or "抱歉，我无法生成回复。"

            # Extract skill_result if available
            skill_result = None
            if agent_state.current_skill_result:
                skill_result = {
                    "success": agent_state.current_skill_result.success,
                    "skill_name": agent_state.current_skill_result.skill_name,
                    "execution_time_ms": agent_state.current_skill_result.execution_time,
                    "data": agent_state.current_skill_result.result_data,
                    "error": agent_state.current_skill_result.error,
                }
                logger.info(f"Including skill_result in response: {skill_result['skill_name']}")

            logger.info(
                f"SkillsIntegratedAgent processing complete: "
                f"intent={intent}, "
                f"skill={skill_used}, "
                f"confidence={confidence}"
            )

            # retrieved_data_info is ONLY used in system prompt for LLM context
            # It should NOT be displayed to users in the final response
            # The LLM will naturally reference this data when generating its response

            # Save patient_context to session metadata FIRST (before adding message)
            # This ensures it's included when add_assistant_message() saves to disk
            if agent_state.patient_context:
                patient_context_dict = {
                    "basic_info": agent_state.patient_context.basic_info,
                    "vital_signs": agent_state.patient_context.vital_signs,
                    "medical_history": agent_state.patient_context.medical_history,
                }
                session.metadata["patient_context"] = patient_context_dict
                logger.info(f"Saved patient_context to session with {len(agent_state.patient_context.vital_signs)} vital signs")

            # Stream the response word by word for better UX
            words = full_response.split()
            for word in words:
                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)  # Small delay for streaming effect

            # Add assistant message to session (this will save to disk with patient_context included)
            # Include multi-skill metadata if available
            assistant_metadata = {
                "patient_id": request.patient_id,
                "skill_used": skill_used,
                "intent": intent,
                "confidence": confidence,
            }

            # Add multi-skill orchestration metadata if present
            if agent_state.multi_skill_selection:
                assistant_metadata["multi_skill_selection"] = agent_state.multi_skill_selection
            if agent_state.execution_plan:
                assistant_metadata["execution_plan"] = agent_state.execution_plan
            if agent_state.multi_skill_result:
                assistant_metadata["multi_skill_result"] = agent_state.multi_skill_result

            session_manager.add_assistant_message(
                session_id=session.session_id,
                content=full_response,
                metadata=assistant_metadata
            )

            # Send end chunk
            end_chunk = StreamingChatEndChunk(
                type="end",
                full_response=full_response,
                intent=intent,
                confidence=confidence,
                suggested_skill=skill_used,
                skill_result=skill_result,
                multi_skill_selection=agent_state.multi_skill_selection if hasattr(agent_state, 'multi_skill_selection') else None,
                multi_skill_result=agent_state.multi_skill_result if hasattr(agent_state, 'multi_skill_result') else None,
            )
            # Inject structured_output and structured_result directly into JSON
            end_json = end_chunk.model_dump_json()
            so = getattr(agent_state, 'structured_output', None)

            # Build extra fields to inject
            extra_fields = []
            if isinstance(so, dict):
                extra_fields.append(f'"structured_output":{json.dumps(so, ensure_ascii=False)}')
            if structured_result:
                extra_fields.append(f'"structured_result":{json.dumps(structured_result, ensure_ascii=False)}')
            if extra_fields:
                end_json = end_json[:-1] + ',' + ','.join(extra_fields) + '}'
            yield f"data: {end_json}\n\n"

        except Exception as e:
            logger.error(f"Error in stream generator: {e}", exc_info=True)
            error_chunk = StreamingChatErrorChunk(
                type="error",
                error=str(e)
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

# Sessions endpoints moved to chat.py v1_router to avoid conflict
# TODO: Remove these comment blocks after verification
#
# @router.get("/sessions/{patient_id}")
# async def get_patient_sessions(
#     patient_id: str,
#     session_manager: SessionManager = Depends(lambda: get_session_manager()),
# ):
#     """
#     Get all active sessions for a patient.
# 
#     Returns list of sessions with their message counts and timestamps.
#     """
#     sessions = session_manager.get_active_sessions(patient_id)
# 
#     return {
#         "patient_id": patient_id,
#         "sessions": [
#             {
#                 "session_id": s.session_id,
#                 "message_count": len(s.messages),
#                 "created_at": s.created_at.isoformat(),
#                 "updated_at": s.updated_at.isoformat(),
#                 "last_message": s.messages[-1].content if s.messages else None,
#             }
#             for s in sessions
#         ],
#         "total_count": len(sessions)
#     }
# 
# 
# @router.get("/sessions/{session_id}/messages")
# async def get_session_messages(
#     session_id: str,
#     session_manager: SessionManager = Depends(lambda: get_session_manager()),
# ):
#     """
#     Get all messages in a session.
# 
#     Returns the complete conversation history for the specified session.
#     """
#     session = session_manager.get_session(session_id)
# 
#     if not session:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Session {session_id} not found"
#         )
# 
#     return {
#         "session_id": session.session_id,
#         "patient_id": session.patient_id,
#         "created_at": session.created_at.isoformat(),
#         "updated_at": session.updated_at.isoformat(),
#         "messages": [
#             {
#                 "role": msg.role,
#                 "content": msg.content,
#                 "timestamp": msg.timestamp.isoformat(),
#             }
#             for msg in session.messages
#         ]
#     }
# 
# 
# @router.delete("/sessions/{session_id}")
# async def delete_session(
#     session_id: str,
#     session_manager: SessionManager = Depends(lambda: get_session_manager()),
# ):
#     """
#     Delete a session and its conversation history.
# 
#     This will remove the session from memory. Note: Messages in the
#     persistent memory store are not deleted.
#     """
#     success = session_manager.delete_session(session_id)
# 
#     if not success:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Session {session_id} not found"
#         )
# 
#     return {
#         "message": f"Session {session_id} deleted successfully",
#         "session_id": session_id
#     }
