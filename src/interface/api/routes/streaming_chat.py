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

from src.interface.api.routes.assessment import _extract_structured_result, transform_abnormal_indicators, _build_current_question

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
    StreamingChatPhaseChunk,
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
            # Check if response actually contains health data (not just "No data found" placeholder)
            info = health_data.get("info", "")
            if "No data found" in info or "no data" in info.lower():
                logger.info(f"Ping An API returned success but no actual data for party_id: {party_id}, info={info}")
                return None
            # Verify at least one meaningful health field exists
            health_fields = {"age", "gender", "diseaseLabels", "diseaseHistory",
                             "systolicPressure", "diastolicPressure", "height", "weight",
                             "bmi", "indicatorItems", "cycleItems"}
            has_health_data = any(f in health_data for f in health_fields)
            if not has_health_data:
                logger.info(f"Ping An API returned success but no health fields for party_id: {party_id}")
                return None
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


def _format_questionnaire_to_markdown(current_question: Dict[str, Any]) -> str:
    """Convert a current_question object into readable markdown for chat rendering.

    Handles both intro pages and data-collection questions with their options.
    """
    if not current_question:
        return ""

    q_type = current_question.get("type", "")
    title = current_question.get("title", "")
    component_type = current_question.get("componentType", "")
    options = current_question.get("options", [])
    total = current_question.get("totalQs", 0)
    current_idx = current_question.get("currentIndex", 0)

    lines = []

    # Progress indicator
    if total and current_idx:
        lines.append(f"**({current_idx}/{total})**")

    if q_type == "intro":
        # Intro page: just show title and optional description
        lines.append(f"## {title}")
        behavior = current_question.get("behavior")
        if behavior and isinstance(behavior, dict):
            desc = behavior.get("description", "")
            if desc:
                lines.append(f"\n{desc}")
    else:
        # Data question
        lines.append(f"## {title}")

        if options:
            if component_type in ("single", "radio") or (not component_type and q_type == "single"):
                # Single select
                for opt in options:
                    label = opt.get("label", opt.get("value", ""))
                    lines.append(f"- {label}")
            elif component_type in ("multipleSubchoice", "multiple", "checkbox"):
                # Multiple select
                for opt in options:
                    label = opt.get("label", opt.get("value", ""))
                    sub_options = opt.get("options", opt.get("subOptions", []))
                    if sub_options:
                        sub_labels = [s.get("label", s.get("value", "")) for s in sub_options]
                        lines.append(f"- **{label}**：{' / '.join(sub_labels)}")
                    else:
                        lines.append(f"- {label}")
            else:
                # Generic option list
                for opt in options:
                    label = opt.get("label", opt.get("value", ""))
                    lines.append(f"- {label}")
        elif component_type == "number" or q_type == "number":
            lines.append("\n> 请输入数值")
        elif component_type == "slider":
            lines.append("\n> 请选择数值")

    return "\n".join(lines)


def _build_health_report(sr: Dict[str, Any]) -> str:
    """Build a formatted health assessment report from structured_result.

    Generates a markdown report with all modules (population classification,
    abnormal indicators, disease prediction, intervention prescriptions,
    risk warnings) instead of returning raw JSON to the user.
    """
    lines = []

    # --- Population Classification ---
    pc = sr.get("population_classification", {})
    if isinstance(pc, str):
        try:
            pc = json.loads(pc)
        except (json.JSONDecodeError, TypeError):
            pc = {}
    if not isinstance(pc, dict):
        pc = {}
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
    if isinstance(abn, str):
        try:
            abn = json.loads(abn)
        except (json.JSONDecodeError, TypeError):
            abn = []

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
            if not isinstance(a, dict):
                continue
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
            if not isinstance(w, dict):
                continue
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
    if isinstance(dp, str):
        try:
            dp = json.loads(dp)
        except (json.JSONDecodeError, TypeError):
            dp = []
    if dp:
        lines.append("## 疾病风险预测")
        lines.append("")
        for p in dp:
            if not isinstance(p, dict):
                continue
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
    if isinstance(rw, str):
        try:
            rw = json.loads(rw)
        except (json.JSONDecodeError, TypeError):
            rw = []
    if rw:
        lines.append("## 风险提示")
        lines.append("")
        for w in rw:
            if not isinstance(w, dict):
                continue
            title = w.get("title", "")
            desc = w.get("description", "")
            level = w.get("level", "")
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(level, "⚠️")
            line = f"- {icon} **{title}**"
            if desc:
                line += f"：{desc}"
            lines.append(line)
            # Render prediction if present
            pred = w.get("prediction")
            if pred and isinstance(pred, dict):
                pred_parts = []
                risk_type = pred.get("risk_type", "")
                timeframe = pred.get("timeframe", "")
                risk_level = pred.get("risk_level", "")
                factors = pred.get("key_factors", [])
                follow_up = pred.get("follow_up", "")
                if risk_level:
                    pred_parts.append(f"风险等级：{risk_level}")
                if timeframe:
                    pred_parts.append(f"预测时段：{timeframe}")
                if factors:
                    pred_parts.append(f"关键因素：{'、'.join(factors)}")
                if follow_up:
                    pred_parts.append(f"随访建议：{follow_up}")
                if pred_parts:
                    lines.append(f"  - 预测信息：{'；'.join(pred_parts)}")
        lines.append("")

    # --- Intervention Prescriptions ---
    ip = sr.get("intervention_prescriptions", [])
    if isinstance(ip, str):
        try:
            ip = json.loads(ip)
        except (json.JSONDecodeError, TypeError):
            ip = []
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
            if not isinstance(p, dict):
                continue
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
    if isinstance(rdc, str):
        try:
            rdc = json.loads(rdc)
        except (json.JSONDecodeError, TypeError):
            rdc = []
    if rdc:
        lines.append("## 建议补充检查")
        lines.append("")
        for r in rdc:
            if not isinstance(r, dict):
                continue
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
        import openai

        settings = get_settings()

        if not settings.llm_api_key:
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

        # Create OpenAI client
        client = openai.OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        # Build messages with system prompt inside
        openai_messages = [{"role": "system", "content": system_prompt}] + messages

        # Generate streaming response
        response = client.chat.completions.create(
            model=settings.model,
            max_tokens=2000,
            messages=openai_messages,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

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
        """Generate SSE stream chunks with skill integration and incremental phase push."""
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
            from src.infrastructure.agent.skills_integration import set_phase_callback, clear_phase_callback
            agent = SkillsIntegratedAgent()

            # Get previous patient_context from session metadata if available
            previous_patient_context = session.metadata.get("patient_context") if session.metadata else None
            if previous_patient_context:
                logger.info(f"Restored previous patient context with {len(previous_patient_context.get('vital_signs', {}))} vital signs")

            # Restore previous skill and orchestration phase from session metadata
            # This ensures follow-up messages (e.g. answering sport_target) don't re-classify intent
            previous_skill = session.metadata.get("skill_used") if session.metadata else None
            previous_phase = session.metadata.get("_orchestration_phase") if session.metadata else None
            if previous_skill:
                logger.info(f"Restored previous skill from session: {previous_skill}, phase={previous_phase}")

            # Use LLM to extract health data from user message.
            # This replaces fragile regex-based extraction with intelligent NLU
            # that can handle sport_target, symptoms, disease severity, etc.
            try:
                from src.domain.shared.services.health_data_extractor import (
                    extract_health_data_from_message,
                    merge_extracted_into_health_data,
                )
                llm_extracted = await asyncio.wait_for(
                    extract_health_data_from_message(request.message),
                    timeout=10.0,
                )
                if llm_extracted:
                    if not health_data:
                        health_data = {}
                    health_data = merge_extracted_into_health_data(llm_extracted, health_data)
                    logger.info(f"LLM extraction merged into health_data: {list(health_data.keys())[:10]}")
            except asyncio.TimeoutError:
                logger.warning("LLM health data extraction timed out, continuing without it")
            except Exception as e:
                logger.warning(f"LLM health data extraction failed: {e}, continuing without it")

            # Merge questionnaire answers into health_data if provided
            # (these are explicit structured answers from the frontend, take precedence)
            has_questionnaire_answers = bool(request.questionnaire_answers)
            if request.questionnaire_answers:
                from src.infrastructure.agent.nodes.check_basic_questionnaire import map_questionnaire_answers_to_health_data
                if not health_data:
                    health_data = {}
                health_data.update(map_questionnaire_answers_to_health_data(request.questionnaire_answers))

            # Determine suggested_skill and _orchestration_phase
            suggested_skill = None
            if previous_skill:
                # Continuing an ongoing assessment — keep the same skill
                suggested_skill = previous_skill
                if not health_data:
                    health_data = {}

                # If sport_target was extracted by LLM or provided via questionnaire_answers,
                # bump phase to 3 for Phase 3 execution
                sport_target = health_data.get("sport_target")
                if sport_target:
                    health_data["_orchestration_phase"] = 3
                    logger.info(f"sport_target detected: '{sport_target}', bumping _orchestration_phase to 3")
                elif previous_phase:
                    health_data["_orchestration_phase"] = previous_phase
            else:
                # First message in structured assessment flow — use package@assessment
                # to prevent LLM from classifying to a single-disease skill
                # (require_basic_questionnaire is always True for streaming chat)
                suggested_skill = "package@assessment"
                logger.info("Streaming chat: setting suggested_skill=package@assessment")

            # Create phase queue for incremental SSE push
            # Each item is (phase_name, phase_label, content, structured_data)
            phase_queue = asyncio.Queue()

            # Register phase callback that pushes to the queue
            async def _phase_cb(phase_name, phase_label, content, structured_data):
                await phase_queue.put((phase_name, phase_label, content, structured_data))

            # Register callback for this session so _execute_package_assessment can use it
            set_phase_callback(session.session_id, _phase_cb)

            # Pass Ping An data to agent if available
            # Add timeout to prevent frontend from showing "thinking" forever
            logger.info(f"Passing to agent: health_data keys={list(health_data.keys())[:15] if health_data else 'None'}, "
                        f"sport_target={health_data.get('sport_target') if health_data else 'N/A'}, "
                        f"_orchestration_phase={health_data.get('_orchestration_phase') if health_data else 'N/A'}, "
                        f"suggested_skill={suggested_skill}")

            # Run agent.process() in background while consuming phase_queue
            agent_task = asyncio.create_task(
                asyncio.wait_for(
                    agent.process(
                        user_input=request.message,
                        patient_id=request.patient_id,
                        party_id=party_id,
                        ping_an_health_data=health_data if health_data else None,
                        previous_patient_context=previous_patient_context,  # Pass previous context
                        session_id=session.session_id,  # Pass session_id for memory isolation
                        suggested_skill=suggested_skill,
                        require_basic_questionnaire=True,
                        questionnaire_answers_submitted=has_questionnaire_answers,
                    ),
                    timeout=180.0  # 3 minute timeout for the entire agent pipeline
                )
            )

            # Consume phase results from queue and push as SSE phase chunks
            # Keep reading until agent_task completes and queue is drained
            phase_results = {}  # Collect all phase data for final structured_result
            while True:
                # Check if agent_task is done
                agent_done = agent_task.done()

                # Try to get from queue (with timeout if agent not done yet)
                try:
                    if agent_done:
                        # Agent done — drain remaining items with timeout
                        # Use a longer timeout to handle race where callback
                        # enqueues after agent_task completes
                        phase_item = await asyncio.wait_for(phase_queue.get(), timeout=2.0)
                    else:
                        # Agent still running — wait longer for next phase result
                        phase_item = await asyncio.wait_for(phase_queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    if agent_done:
                        # No more items and agent done — exit loop
                        break
                    # Agent still running but no phase result yet — continue waiting
                    continue

                phase_name, phase_label, content, structured_data = phase_item
                phase_results[phase_name] = structured_data
                logger.info(f"Consumed phase from queue: {phase_name} ({phase_label}), phase_results keys={list(phase_results.keys())}")

                # Push phase SSE chunk
                phase_chunk = StreamingChatPhaseChunk(
                    phase_name=phase_name,
                    phase_label=phase_label,
                    content=content,
                    structured_data=structured_data,
                )
                yield f"data: {phase_chunk.model_dump_json()}\n\n"
                logger.info(f"Pushed phase chunk: {phase_name} ({phase_label})")

            # Get agent result
            try:
                agent_state = agent_task.result()
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
                clear_phase_callback(session.session_id)
                return
            except Exception as e:
                import traceback as _tb
                tb_str = _tb.format_exc()
                logger.error(f"Agent process failed: {e}\n{tb_str}")
                error_chunk = StreamingChatErrorChunk(
                    type="error",
                    error=str(e)
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                clear_phase_callback(session.session_id)
                return

            # Clear phase callback
            clear_phase_callback(session.session_id)

            logger.info(f"Agent processing complete: intent={agent_state.intent}, skill={agent_state.suggested_skill}, confidence={agent_state.confidence}")

            # Extract structured_result from agent state (same logic as assessment.py)
            structured_result = _extract_structured_result(agent_state)

            # Merge phase_results (from incremental SSE push) into structured_result
            # Phase results contain the authoritative data from each phase execution,
            # while agent_state.structured_output may be incomplete or different.
            if phase_results:
                for key, value in phase_results.items():
                    if isinstance(value, dict) and isinstance(structured_result.get(key), dict):
                        structured_result[key].update(value)
                    else:
                        structured_result[key] = value
                logger.info(f"Merged {len(phase_results)} phase results into structured_result: {list(phase_results.keys())}")

            # Transform abnormal_indicators into indicators + warnings
            transform_abnormal_indicators(structured_result)

            # LLM risk-warning and prescription-recommendation are now executed via LangGraph pipeline (Phase 3.5)

            # Extract response and metadata from agent state
            skill_used = agent_state.suggested_skill
            intent = agent_state.intent.value if agent_state.intent else "chat"
            confidence = agent_state.confidence or 0.0

            # Handle missing_basic_info: build current_question and track seen intro pages
            so = getattr(agent_state, 'structured_output', None)
            if isinstance(so, dict) and so.get("status") == "missing_basic_info":
                # Restore _seen_intro_pages from session metadata
                seen_intro_pages = session.metadata.get("_seen_intro_pages", []) if session.metadata else []
                health_data_with_seen = dict(health_data or {})
                health_data_with_seen["_seen_intro_pages"] = seen_intro_pages

                # Build current_question (same logic as assessment.py)
                recommended = so.get("recommended_data_collection", [])
                questions = so.get("questions", [])
                questionnaire_type = so.get("questionnaire_type")
                current_q = _build_current_question(
                    questions, recommended, questionnaire_type,
                    health_data=health_data_with_seen,
                )

                # Track seen intro pages
                if current_q and current_q.get("type") == "intro":
                    intro_id = current_q.get("id")
                    if intro_id and intro_id not in seen_intro_pages:
                        seen_intro_pages.append(intro_id)
                        if not session.metadata:
                            session.metadata = {}
                        session.metadata["_seen_intro_pages"] = seen_intro_pages

                # Add current_question to structured_output for frontend
                so["current_question"] = current_q
                logger.info(f"Built current_question for missing_basic_info: id={current_q.get('id') if current_q else None}")

            # Build report: questionnaire markdown > modules markdown > structured_result report > fallback
            so = getattr(agent_state, 'structured_output', None)
            if isinstance(so, dict) and so.get("status") in ("missing_basic_info", "goal_selection"):
                # Convert questionnaire current_question to markdown for chat rendering
                current_q = so.get("current_question", {})
                if current_q:
                    full_response = _format_questionnaire_to_markdown(current_q)
                    logger.info(f"Using questionnaire markdown as response (status={so.get('status')}, q_id={current_q.get('id')})")
                else:
                    full_response = agent_state.final_response or "请提供更多信息以继续评估。"
            elif isinstance(so, dict) and so.get("modules"):
                # Use skill raw modules markdown (structured markdown for SSE)
                full_response = _format_modules_to_markdown(so["modules"])
                logger.info("Using modules-based markdown as response")
            elif structured_result and isinstance(structured_result, dict):
                pc = structured_result.get("population_classification", {})
                if isinstance(pc, str):
                    try:
                        pc = json.loads(pc)
                    except (json.JSONDecodeError, TypeError):
                        pc = {}
                category = pc.get("primary_category", "") if isinstance(pc, dict) else ""
                if category not in ("", None):
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

            # Save skill_used and _orchestration_phase to session metadata
            # so follow-up messages preserve the ongoing assessment context
            if skill_used:
                if not session.metadata:
                    session.metadata = {}
                session.metadata["skill_used"] = skill_used

            # Determine _orchestration_phase to save:
            # - If structured_output has _orchestration_phase, use that (Phase 2 case)
            # - If Phase 3 completed (structured_result has population_classification + modules), save phase=3
            so = getattr(agent_state, 'structured_output', None)
            phase_to_save = None
            if isinstance(so, dict) and "_orchestration_phase" in so:
                phase_to_save = so["_orchestration_phase"]
            elif isinstance(so, dict) and so.get("modules") and structured_result:
                # Phase 3 completed — save phase 3 so follow-up messages don't re-enter Phase 1/2
                phase_to_save = 3
                logger.info("Phase 3 completed, saving _orchestration_phase=3 to session metadata")
            if phase_to_save:
                if not session.metadata:
                    session.metadata = {}
                session.metadata["_orchestration_phase"] = phase_to_save
                logger.info(f"Saved _orchestration_phase={phase_to_save} to session metadata")

            # Stream the response word by word for better UX
            # Skip token streaming if phase chunks already pushed the full report incrementally
            if phase_results:
                logger.info("Phase results already pushed incrementally, skipping token streaming")
            else:
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

            # When phase results were pushed, send empty full_response in end chunk
            # so the frontend uses accumulatedContent (from phase chunks) instead of
            # questionnaire markdown like "(1/8)"
            # Also send empty full_response for missing_basic_info and goal_selection:
            # the questionnaire is rendered from structured_output, not from text content.
            so_status = getattr(agent_state, 'structured_output', None)
            is_questionnaire_status = isinstance(so_status, dict) and so_status.get("status") in ("missing_basic_info", "goal_selection")
            end_full_response = "" if (phase_results or is_questionnaire_status) else full_response
            logger.info(f"End chunk: phase_results={list(phase_results.keys())}, end_full_response length={len(end_full_response)}")

            # Send end chunk
            end_chunk = StreamingChatEndChunk(
                type="end",
                full_response=end_full_response,
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
                try:
                    extra_fields.append(f'"structured_output":{json.dumps(so, ensure_ascii=False, default=str)}')
                except (ValueError, TypeError):
                    extra_fields.append(f'"structured_output":{{}}')
            if structured_result:
                try:
                    extra_fields.append(f'"structured_result":{json.dumps(structured_result, ensure_ascii=False, default=str)}')
                except (ValueError, TypeError):
                    extra_fields.append(f'"structured_result":{{}}')
            if extra_fields:
                end_json = end_json[:-1] + ',' + ','.join(extra_fields) + '}'
            yield f"data: {end_json}\n\n"

        except Exception as e:
            import traceback as _tb
            tb_str = _tb.format_exc()
            logger.error(f"Error in stream generator: {e}\n{tb_str}")
            error_chunk = StreamingChatErrorChunk(
                type="error",
                error=str(e)
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            # Clean up phase callback on error
            try:
                clear_phase_callback(session.session_id)
            except Exception:
                pass

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
