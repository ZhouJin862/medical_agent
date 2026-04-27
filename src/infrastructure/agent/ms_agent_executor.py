"""
MS-Agent ScriptExecutor 集成 - 统一技能执行入口

支持多种执行后端：
- subprocess: 基于 subprocess 的脚本执行（默认，稳定）
- msagent: 基于 MS-Agent 库的执行（LLM规划、沙箱隔离）
- auto: 自动选择（优先 msagent，回退到 subprocess）

配置切换：
    # 通过环境变量
    export SKILL_EXECUTOR_BACKEND=msagent

    # 或通过代码
    from src.infrastructure.agent.skill_executor_factory import set_executor_config
    set_executor_config({"backend": "msagent"})

使用示例：
    from src.infrastructure.agent.ms_agent_executor import execute_skill_via_msagent

    result = await execute_skill_via_msagent(
        skill_name="chronic-disease-risk-assessment",
        user_input="评估我的健康风险",
        patient_context=patient_context
    )
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

from src.infrastructure.agent.state import PatientContext, SkillExecutionResult
from src.infrastructure.agent.skill_executor_factory import get_executor_factory, create_skill_executor

logger = logging.getLogger(__name__)

# MS-Agent 可用性检查
try:
    from ms_agent.executor import ScriptExecutor
    from ms_agent.tool_manager import ToolManager
    MSAGENT_AVAILABLE = True
    logger.info("MS-Agent library is available")
except ImportError:
    MSAGENT_AVAILABLE = False
    logger.warning("MS-Agent not installed. Install with: pip install ms-agent")
    # 创建占位符类以避免导入错误
    class ScriptExecutor:
        pass
    class ToolManager:
        pass
        pass


# ====================================================================
# 统一执行入口（使用工厂模式）
# ====================================================================

async def execute_skill_via_msagent(
    skill_name: str,
    user_input: str,
    patient_context: Optional[PatientContext] = None,
    timeout: int = 30,
    backend: Optional[str] = None
) -> Optional[SkillExecutionResult]:
    """
    执行技能（统一入口，兼容旧接口）

    使用配置的执行后端（subprocess 或 msagent）

    Args:
        skill_name: 技能名称
        user_input: 用户输入
        patient_context: 患者上下文
        timeout: 超时时间（秒）
        backend: 指定执行后端，如果为 None 则使用配置的默认值

    Returns:
        SkillExecutionResult or None
    """
    return await execute_skill_via_backend(
        skill_name=skill_name,
        user_input=user_input,
        patient_context=patient_context,
        timeout=timeout,
        backend=backend
    )


async def execute_skill_via_backend(
    skill_name: str,
    user_input: str,
    patient_context: Optional[PatientContext] = None,
    timeout: int = 30,
    backend: Optional[str] = None
) -> Optional[SkillExecutionResult]:
    """
    使用指定后端执行技能

    Args:
        skill_name: 技能名称
        user_input: 用户输入
        patient_context: 患者上下文
        timeout: 超时时间（秒）
        backend: 指定执行后端 (subprocess/msagent/auto)，None 则使用配置

    Returns:
        SkillExecutionResult or None
    """
    import asyncio

    skill_dir = Path("skills") / skill_name
    if not skill_dir.exists():
        logger.warning(f"Skill directory not found: {skill_dir}")
        return None

    # 准备输入数据
    input_data = _prepare_input_data(user_input, patient_context)

    # 创建执行器
    executor = create_skill_executor(skill_dir, backend=backend)

    # 获取后端信息
    backend_name = executor.get_backend_name()
    logger.info(f"Executing {skill_name} with backend: {backend_name}")

    start_time = time.time()

    try:
        # 执行技能
        result = await executor.execute(input_data=input_data, env=None)
        execution_time = int((time.time() - start_time) * 1000)

        # 处理结果
        if result.get("success", False):
            final_output = result.get("final_output", result)

            # Handle subprocess executor's nested final_output structure
            # Subprocess wraps skill output: result.final_output.final_output.modules
            # We need to unwrap to get the actual skill output with modules
            if "final_output" in final_output and isinstance(final_output["final_output"], dict):
                nested_output = final_output["final_output"]
                # Check if modules are in the nested final_output
                if "modules" in nested_output:
                    final_output = nested_output
                # Also handle triple-nested case (subprocess -> skill -> final_output)
                elif "final_output" in nested_output and isinstance(nested_output["final_output"], dict):
                    if "modules" in nested_output["final_output"]:
                        final_output = nested_output["final_output"]

            if "modules" in final_output:
                modules = final_output["modules"]
                formatted_result = {
                    "success": True,
                    "skill_name": skill_name,
                    "modules": modules,
                    "total_modules": final_output.get("total_modules", len(modules)),
                    "backend": backend_name
                }

                return SkillExecutionResult(
                    status_code=200,
                    skill_name=skill_name,
                    success=True,
                    result_data=formatted_result,
                    execution_time=execution_time,
                )
            else:
                return SkillExecutionResult(
                    status_code=200,
                    skill_name=skill_name,
                    success=True,
                    result_data=final_output,
                    execution_time=execution_time,
                )
        else:
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"{skill_name} execution failed with {backend_name}: {error_msg}")
            return None

    except Exception as e:
        logger.error(f"Error executing {skill_name} with {backend_name}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def _prepare_input_data(
    user_input: str,
    patient_context: Optional[PatientContext]
) -> Dict[str, Any]:
    """准备技能执行所需的输入数据"""
    patient_info = {}
    health_metrics = {}

    if patient_context:
        patient_info = patient_context.basic_info.copy() if patient_context.basic_info else {}
        # Add patient_id from top-level
        if patient_context.patient_id:
            patient_info["patient_id"] = patient_context.patient_id

        if patient_context.vital_signs:
            vital_signs = patient_context.vital_signs

            # 转换单位
            height_cm = vital_signs.get("height")
            height_m = height_cm / 100 if height_cm and height_cm > 10 else height_cm

            health_metrics = {
                "blood_pressure": {
                    "systolic": vital_signs.get("systolic_bp"),
                    "diastolic": vital_signs.get("diastolic_bp")
                },
                "basic": {
                    "height": height_m,
                    "weight": vital_signs.get("weight"),
                    "waist_circumference": vital_signs.get("waist")
                },
                "bmi": {
                    "value": vital_signs.get("bmi"),  # 使用已计算的BMI值
                    "waist_circumference": vital_signs.get("waist")
                },
                "blood_glucose": {
                    "fasting": vital_signs.get("fasting_glucose"),
                    "hba1c": vital_signs.get("hba1c")
                },
                "blood_lipid": {
                    "tc": vital_signs.get("total_cholesterol"),
                    "tg": vital_signs.get("tg"),
                    "ldl_c": vital_signs.get("ldl_c"),
                    "hdl_c": vital_signs.get("hdl_c")
                },
                "uric_acid": vital_signs.get("uric_acid")
            }

    return {
        "user_input": user_input,
        "patient_info": patient_info,
        "health_metrics": health_metrics,
        "report_date": time.strftime("%Y年%m月%d日"),
        "patient_name": patient_info.get("name", ""),
        "patient_id": patient_context.patient_id if patient_context else "",
    }


# ====================================================================
# 兼容接口（保持向后兼容）
# ====================================================================

async def execute_skill_via_skill_md(
    skill_name: str,
    user_input: str,
    patient_context: Optional[PatientContext] = None,
    timeout: int = 30
) -> Optional[SkillExecutionResult]:
    """
    使用 SKILL.md 驱动方式执行技能（兼容接口）

    现在统一使用工厂模式，此函数保持向后兼容。
    """
    return await execute_skill_via_backend(
        skill_name=skill_name,
        user_input=user_input,
        patient_context=patient_context,
        timeout=timeout
    )


# ====================================================================
# 工具函数
# ====================================================================

def get_execution_backend() -> str:
    """
    获取当前配置的执行后端

    Returns:
        "subprocess", "msagent", 或 "auto"
    """
    factory = get_executor_factory()
    return factory.get_active_backend()


def list_available_backends() -> Dict[str, bool]:
    """
    列出可用的执行后端

    Returns:
        {"subprocess": True, "msagent": bool}
    """
    factory = get_executor_factory()
    return factory.list_available_backends()


def register_skills_as_tools() -> list:
    """
    将技能包注册为 MS-Agent 工具（兼容接口）

    Returns:
        List of registered tools
    """
    if not MSAGENT_AVAILABLE:
        logger.info("MS-Agent not available, skipping tool registration")
        return []

    tool_manager = ToolManager()
    tools = []

    skills_dir = Path("skills")
    if not skills_dir.exists():
        logger.info(f"Skills directory not found: {skills_dir}")
        return []

    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_name = skill_dir.name
            try:
                tool = tool_manager.register_tool(
                    name=skill_name,
                    description=f"Execute {skill_name} skill for health assessment",
                    executor=ScriptExecutor()
                )
                tools.append(tool)
                logger.info(f"Registered skill as tool: {skill_name}")
            except Exception as e:
                logger.warning(f"Failed to register tool {skill_name}: {e}")

    logger.info(f"Total tools registered: {len(tools)}")
    return tools
