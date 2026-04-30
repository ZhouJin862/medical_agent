"""
Skill Orchestrator - Executes multiple skills according to a plan.

Handles parallel/sequential execution and result aggregation.
"""
import logging
import time
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.models.skill_selection_models import (
    ExecutionPlan,
    ExecutionGroup,
    SkillExecutionResult,
    MultiSkillExecutionResult,
)
from src.domain.shared.services.enhanced_llm_skill_selector import (
    EnhancedLLMSkillSelector,
)
from src.domain.shared.services.unified_skills_repository import (
    UnifiedSkillsRepository,
)

logger = logging.getLogger(__name__)


class SkillOrchestrator:
    """
    Orchestrates execution of multiple skills.

    Features:
    - Executes skills according to plan (parallel/sequential/mixed)
    - Manages context passing between skills
    - Aggregates results
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the orchestrator.

        Args:
            session: Database session
        """
        self._session = session
        self._repository = UnifiedSkillsRepository(session, skills_dir="skills")
        self._executor = SkillExecutor(self._repository)

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        user_input: str,
        patient_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[str] = None,
    ) -> MultiSkillExecutionResult:
        """
        Execute skills according to the plan.

        Args:
            plan: Execution plan from EnhancedLLMSkillSelector
            user_input: User's original input
            patient_context: Patient data
            conversation_context: Conversation history

        Returns:
            Multi-skill execution result
        """
        start_time = time.time()

        logger.info(
            f"Executing {plan.total_skills} skills in {plan.execution_mode} mode"
        )

        try:
            if plan.execution_mode == "parallel":
                result = await self._execute_parallel(
                    plan=plan,
                    user_input=user_input,
                    patient_context=patient_context,
                    conversation_context=conversation_context,
                )
            elif plan.execution_mode == "sequential":
                result = await self._execute_sequential(
                    plan=plan,
                    user_input=user_input,
                    patient_context=patient_context,
                    conversation_context=conversation_context,
                )
            else:  # mixed
                result = await self._execute_mixed(
                    plan=plan,
                    user_input=user_input,
                    patient_context=patient_context,
                    conversation_context=conversation_context,
                )

            # Aggregate results
            result = await self._aggregate_results(
                result,
                plan.aggregation_strategy,
                user_input,
            )

            result.total_execution_time_ms = int((time.time() - start_time) * 1000)

            # Consider it a success if at least one skill succeeded
            # This allows partial success with aggregated response
            has_successful_skills = len(result.successful_skills) > 0
            result.success = has_successful_skills

            # Still collect errors for debugging
            if result.failed_skills:
                result.errors = [
                    f"{r.skill_name}: {r.error}"
                    for r in result.failed_skills
                ]

            return result

        except Exception as e:
            logger.error(f"Skill orchestration failed: {e}")
            import traceback
            traceback.print_exc()

            return MultiSkillExecutionResult(
                success=False,
                execution_plan=plan,
                errors=[str(e)],
                total_execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _execute_parallel(
        self,
        plan: ExecutionPlan,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
    ) -> MultiSkillExecutionResult:
        """Execute skills in parallel."""
        result = MultiSkillExecutionResult(
            success=True,
            execution_plan=plan,
        )

        # Create tasks for all skills
        async def execute_one(skill_name: str) -> SkillExecutionResult:
            return await self._executor.execute_skill(
                skill_name=skill_name,
                user_input=user_input,
                patient_context=patient_context,
                conversation_context=conversation_context,
            )

        # Execute in parallel
        tasks = [execute_one(skill) for skill in plan.skills]
        skill_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for skill_result in skill_results:
            if isinstance(skill_result, Exception):
                logger.error(f"Skill execution error: {skill_result}")
                result.skill_results.append(
                    SkillExecutionResult(
                        skill_name="unknown",
                        success=False,
                        error=str(skill_result),
                    )
                )
            else:
                result.skill_results.append(skill_result)

        return result

    async def _execute_sequential(
        self,
        plan: ExecutionPlan,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
    ) -> MultiSkillExecutionResult:
        """Execute skills sequentially, passing context between them."""
        result = MultiSkillExecutionResult(
            success=True,
            execution_plan=plan,
        )

        accumulated_context = conversation_context or ""
        accumulated_data = {}

        for skill_name in plan.skills:
            # Build enhanced context from previous results
            enhanced_conversation = accumulated_context
            enhanced_patient = patient_context or {}

            # Add accumulated data to patient context
            if accumulated_data:
                enhanced_patient = {**(enhanced_patient or {}), **accumulated_data}

            skill_result = await self._executor.execute_skill(
                skill_name=skill_name,
                user_input=user_input,
                patient_context=enhanced_patient,
                conversation_context=enhanced_conversation,
            )

            result.skill_results.append(skill_result)

            if skill_result.success:
                # Accumulate results for next skill
                if skill_result.structured_output:
                    accumulated_data.update(skill_result.structured_output)

                # Add to conversation context
                if skill_result.response:
                    accumulated_context += f"\n\n[{skill_name}]:\n{skill_result.response}\n"

        return result

    async def _execute_mixed(
        self,
        plan: ExecutionPlan,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
    ) -> MultiSkillExecutionResult:
        """Execute skills according to mixed plan."""
        result = MultiSkillExecutionResult(
            success=True,
            execution_plan=plan,
        )

        accumulated_data = {}
        accumulated_context = conversation_context or ""

        # Execute groups in order
        for group in plan.groups:
            if group.execution_mode == "parallel":
                # Execute group in parallel
                async def execute_one(skill_name: str) -> SkillExecutionResult:
                    # Build context with accumulated data
                    enhanced_patient = patient_context or {}
                    if accumulated_data:
                        enhanced_patient = {**enhanced_patient, **accumulated_data}

                    return await self._executor.execute_skill(
                        skill_name=skill_name,
                        user_input=user_input,
                        patient_context=enhanced_patient,
                        conversation_context=accumulated_context,
                    )

                tasks = [execute_one(s) for s in group.skills]
                group_results = await asyncio.gather(*tasks, return_exceptions=True)

                for skill_result in group_results:
                    if isinstance(skill_result, Exception):
                        result.skill_results.append(
                            SkillExecutionResult(
                                skill_name="unknown",
                                success=False,
                                error=str(skill_result),
                            )
                        )
                    else:
                        result.skill_results.append(skill_result)
                        # Accumulate successful results
                        if skill_result.success and skill_result.structured_output:
                            accumulated_data.update(skill_result.structured_output)

            else:  # sequential within group
                for skill_name in group.skills:
                    enhanced_patient = patient_context or {}
                    if accumulated_data:
                        enhanced_patient = {**enhanced_patient, **accumulated_data}

                    skill_result = await self._executor.execute_skill(
                        skill_name=skill_name,
                        user_input=user_input,
                        patient_context=enhanced_patient,
                        conversation_context=accumulated_context,
                    )

                    result.skill_results.append(skill_result)

                    if skill_result.success and skill_result.structured_output:
                        accumulated_data.update(skill_result.structured_output)

        return result

    async def _aggregate_results(
        self,
        result: MultiSkillExecutionResult,
        strategy: str,
        user_input: str,
    ) -> MultiSkillExecutionResult:
        """Aggregate skill results based on strategy."""
        aggregator = ResultAggregator()

        if strategy == "merge":
            result.aggregated_response = await aggregator.merge_results(
                result.skill_results, user_input
            )
            result.structured_output = aggregator.merge_structured(
                result.skill_results
            )

        elif strategy == "chain":
            result.aggregated_response = aggregator.chain_results(
                result.skill_results, user_input
            )
            result.structured_output = aggregator.chain_structured(
                result.skill_results
            )

        else:  # enhance
            result.aggregated_response = await aggregator.enhance_results(
                result.skill_results, user_input
            )
            result.structured_output = aggregator.enhance_structured(
                result.skill_results
            )

        return result


class SkillExecutor:
    """Executes a single skill."""

    def __init__(self, repository: UnifiedSkillsRepository):
        self._repository = repository

    async def execute_skill(
        self,
        skill_name: str,
        user_input: str,
        patient_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[str] = None,
    ) -> SkillExecutionResult:
        """
        Execute a single skill.

        Args:
            skill_name: Name of the skill
            user_input: User input
            patient_context: Patient data
            conversation_context: Conversation history

        Returns:
            Skill execution result
        """
        start_time = time.time()

        # Load skill definition
        skill_def = await self._repository.get_skill(skill_name)

        if not skill_def:
            return SkillExecutionResult(
                skill_name=skill_name,
                success=False,
                error=f"Skill not found: {skill_name}",
            )

        try:
            # Priority 1: frontmatter tools (has `tools` in SKILL.md YAML)
            if self._has_tools_frontmatter(skill_name):
                return await self._execute_tools_skill(
                    skill_name,
                    user_input,
                    patient_context,
                )

            # Priority 2: workflow skill (has ### 步骤 in SKILL.md)
            if self._is_workflow_skill(skill_name):
                return await self._execute_workflow_skill(
                    skill_name,
                    user_input,
                    patient_context,
                )

            # Priority 3: file-based skill (has scripts/main.py)
            script_result = await self._execute_script_skill(
                skill_name,
                user_input,
                patient_context,
            )
            if script_result is not None:
                return script_result

            # Priority 4: fallback to LLM prompt skill
            return await self._execute_prompt_skill(
                skill_def,
                user_input,
                patient_context,
                conversation_context,
            )

        except Exception as e:
            logger.error(f"Skill {skill_name} execution failed: {e}")
            return SkillExecutionResult(
                skill_name=skill_name,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _execute_script_skill(
        self,
        skill_name: str,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
    ) -> Optional[SkillExecutionResult]:
        """
        Execute a file-based skill via subprocess (scripts/main.py).

        Returns None if no script found, so caller can fall through to prompt.
        """
        from pathlib import Path

        skill_dir = Path("skills") / skill_name
        if not skill_dir.exists():
            return None

        # Check for scripts/main.py
        main_script = skill_dir / "scripts" / "main.py"
        if not main_script.exists():
            return None

        start_time = time.time()

        try:
            from src.infrastructure.agent.ms_agent_executor import execute_skill_via_backend

            # Build a minimal PatientContext-like object for the executor
            from src.infrastructure.agent.state import PatientContext
            pc = None
            if patient_context:
                pc = PatientContext(
                    patient_id=patient_context.get("basic_info", {}).get("patient_id", ""),
                    basic_info=patient_context.get("basic_info", {}),
                    vital_signs=patient_context.get("vital_signs", {}),
                    medical_history=patient_context.get("medical_history", {}),
                )

            result = await execute_skill_via_backend(
                skill_name=skill_name,
                user_input=user_input,
                patient_context=pc,
                timeout=30,
            )

            if result is None:
                logger.warning(f"Subprocess execution returned None for {skill_name}")
                return None

            # Extract structured output from result_data
            result_data = result.result_data or {}
            final_out = result_data.get("final_output", result_data)
            if isinstance(final_out, dict) and "final_output" in final_out and isinstance(final_out["final_output"], dict):
                nested = final_out["final_output"]
                if "modules" in nested:
                    final_out = nested

            response = None
            if isinstance(final_out, dict):
                response = final_out.get("message") or final_out.get("response")

            return SkillExecutionResult(
                skill_name=skill_name,
                success=result.success,
                response=response,
                structured_output=final_out if "modules" in (final_out or {}) else result_data,
                error=result.error if hasattr(result, 'error') else None,
                execution_time_ms=result.execution_time,
                metadata={"backend": "subprocess"},
            )

        except Exception as e:
            logger.warning(f"Subprocess execution failed for {skill_name}: {e}")
            return None

    def _has_tools_frontmatter(self, skill_name: str) -> bool:
        """Check if skill SKILL.md has a `tools` field in frontmatter."""
        try:
            from pathlib import Path
            import yaml

            possible_paths = [
                Path("skills") / skill_name,
                Path.cwd() / "skills" / skill_name,
            ]

            for path in possible_paths:
                skill_md = path / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text(encoding="utf-8")
                    if not content.startswith("---"):
                        continue
                    end = content.find("---", 3)
                    if end == -1:
                        continue
                    try:
                        fm = yaml.safe_load(content[3:end].strip())
                        return isinstance(fm, dict) and "tools" in fm
                    except Exception:
                        continue
            return False
        except Exception:
            return False

    async def _execute_tools_skill(
        self,
        skill_name: str,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
    ) -> SkillExecutionResult:
        """Execute skill via frontmatter `tools` declaration."""
        from src.infrastructure.agent.skill_tools_executor import execute_skill_via_tools

        input_data = self._build_skill_input_data(user_input, patient_context)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: execute_skill_via_tools(skill_name, input_data),
        )

        # Extract response / structured output (same logic as workflow skill)
        response = result.get("response")
        final_out = result.get("final_output")
        if not final_out and "modules" in result:
            final_out = result

        if not response and final_out and isinstance(final_out, dict):
            response = final_out.get("message") or final_out.get("response")

        return SkillExecutionResult(
            skill_name=skill_name,
            success=result.get("success", False),
            response=response,
            structured_output=final_out,
            error=result.get("error"),
            metadata=result.get("metadata", {}),
        )

    def _is_workflow_skill(self, skill_name: str) -> bool:
        """Check if skill is workflow type."""
        try:
            from pathlib import Path
            import os

            possible_paths = [
                Path("skills") / skill_name,
                Path.cwd() / "skills" / skill_name,
            ]

            for path in possible_paths:
                skill_md = path / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text(encoding='utf-8')
                    import re
                    return bool(re.search(r'### 步骤\d+[:：]', content))

            return False
        except Exception:
            return False

    async def _execute_workflow_skill(
        self,
        skill_name: str,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
    ) -> SkillExecutionResult:
        """Execute workflow skill using skill_md_executor."""
        from src.infrastructure.agent.skill_md_executor import execute_skill_via_skill_md
        import json

        # Build input data
        input_data = self._build_skill_input_data(
            user_input,
            patient_context,
        )

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: execute_skill_via_skill_md(skill_name, input_data)
        )

        # Extract response from result - try multiple fields
        # Different skills return data in different formats:
        # - Some return {"response": "text", ...}
        # - Some return {"final_output": {...}, ...}
        # - Some return {"success": True, "modules": {...}, ...} (top-level modules)
        response = result.get("response")

        # Get structured output from various locations
        final_out = result.get("final_output")
        if not final_out and "modules" in result:
            # Some skills put modules at top level
            final_out = result

        # If no response, try to extract text from final_output
        # Don't fall back to str(final_out) - let the aggregator's
        # _format_modules_to_markdown handle structured output properly
        if not response and final_out:
            if isinstance(final_out, dict):
                # Check for text fields only
                response = final_out.get("message") or final_out.get("response")
                # Leave as None if no text field found - aggregator will format modules

        return SkillExecutionResult(
            skill_name=skill_name,
            success=result.get("success", False),
            response=response,
            structured_output=final_out,  # Always include structured output
            error=result.get("error"),
            metadata=result.get("metadata", {}),
        )

    async def _execute_prompt_skill(
        self,
        skill_def,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
    ) -> SkillExecutionResult:
        """Execute prompt skill using LLM."""
        import anthropic
        from src.config.settings import get_settings

        settings = get_settings()
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
            timeout=30.0
        )

        # Build prompt
        prompt = self._build_prompt(
            skill_def.content,
            user_input,
            patient_context,
            conversation_context,
        )

        response = client.messages.create(
            model=settings.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        return SkillExecutionResult(
            skill_name=skill_def.metadata.name,
            success=True,
            response=response.content[0].text,
        )

    def _build_skill_input_data(
        self,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build input data for workflow skills.

        Provides multiple data formats to support different skill types:
        - patient_data/basic_info format for cvd-risk-assessment
        - patient_info/health_metrics format for similar skills
        """
        patient_context = patient_context or {}

        basic_info = patient_context.get("basic_info", {})
        vital_signs = patient_context.get("vital_signs", {})
        medical_history = patient_context.get("medical_history", {})

        # Format 1: patient_data/basic_info format (for cvd-risk-assessment)
        patient_data = {
            "basic_info": basic_info,
        }

        # Format 2: patient_info/health_metrics format
        # Build patient_info from basic_info
        patient_info = {
            "name": basic_info.get("patient_id", "患者"),  # Use patient_id as name fallback
            "age": basic_info.get("age"),
            "gender": basic_info.get("gender"),
            "height": vital_signs.get("height"),
            "weight": vital_signs.get("weight"),
            "waist": vital_signs.get("waist"),
        }

        # Build health_metrics from vital_signs
        health_metrics = {}

        # Basic measurements (height, weight, waist, BMI)
        if vital_signs.get("height") or vital_signs.get("weight"):
            health_metrics["basic"] = {}
            if vital_signs.get("height"):
                height_cm = vital_signs["height"]
                health_metrics["basic"]["height"] = height_cm / 100 if height_cm > 10 else height_cm
            if vital_signs.get("weight"):
                health_metrics["basic"]["weight"] = vital_signs["weight"]
            if vital_signs.get("waist"):
                health_metrics["basic"]["waist_circumference"] = vital_signs["waist"]

        # BMI as top-level key (validators expect health_metrics["bmi"])
        if vital_signs.get("bmi"):
            health_metrics["bmi"] = {
                "value": vital_signs["bmi"],
                "waist_circumference": vital_signs.get("waist"),
                "height": vital_signs.get("height"),
                "weight": vital_signs.get("weight"),
            }

        # Blood pressure
        if vital_signs.get("systolic_bp") or vital_signs.get("diastolic_bp"):
            health_metrics["blood_pressure"] = {}
            if vital_signs.get("systolic_bp"):
                health_metrics["blood_pressure"]["systolic"] = vital_signs["systolic_bp"]
            if vital_signs.get("diastolic_bp"):
                health_metrics["blood_pressure"]["diastolic"] = vital_signs["diastolic_bp"]

        # Blood glucose
        if vital_signs.get("fasting_glucose") or vital_signs.get("hba1c"):
            health_metrics["blood_glucose"] = {}
            if vital_signs.get("fasting_glucose"):
                health_metrics["blood_glucose"]["fasting"] = vital_signs["fasting_glucose"]
            if vital_signs.get("hba1c"):
                health_metrics["blood_glucose"]["hba1c"] = vital_signs["hba1c"]

        # Blood lipids
        if vital_signs.get("total_cholesterol") or vital_signs.get("ldl_c") or vital_signs.get("hdl_c") or vital_signs.get("tg"):
            health_metrics["blood_lipid"] = {}
            if vital_signs.get("total_cholesterol"):
                health_metrics["blood_lipid"]["tc"] = vital_signs["total_cholesterol"]
            if vital_signs.get("tg"):
                health_metrics["blood_lipid"]["tg"] = vital_signs["tg"]
            if vital_signs.get("ldl_c"):
                health_metrics["blood_lipid"]["ldl_c"] = vital_signs["ldl_c"]
            if vital_signs.get("hdl_c"):
                health_metrics["blood_lipid"]["hdl_c"] = vital_signs["hdl_c"]

        # Uric acid
        if vital_signs.get("uric_acid"):
            health_metrics["uric_acid"] = vital_signs["uric_acid"]

        return {
            "user_input": user_input,
            # Format for cvd-risk-assessment
            "vital_signs": vital_signs,
            "patient_data": patient_data,
            "medical_history": medical_history,
            # Format for skills that use patient_info/health_metrics
            "patient_info": patient_info,
            "health_metrics": health_metrics,
        }

    def _build_prompt(
        self,
        skill_content: str,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
    ) -> str:
        """Build prompt for prompt-type skills."""
        parts = [f"# User Input\n{user_input}\n"]

        if skill_content:
            parts.append(f"# Skill Instructions\n{skill_content}\n")

        if patient_context:
            parts.append("# Patient Context\n")
            if patient_context.get("basic_info"):
                parts.append(f"Basic: {patient_context['basic_info']}\n")
            if patient_context.get("vital_signs"):
                parts.append(f"Vitals: {patient_context['vital_signs']}\n")

        if conversation_context:
            parts.append(f"# Conversation Context\n{conversation_context}\n")

        return "\n".join(parts)


class ResultAggregator:
    """Aggregates results from multiple skills."""

    async def _intelligent_aggregate(
        self,
        results: List[SkillExecutionResult],
        user_input: str,
    ) -> str:
        """Use LLM to intelligently aggregate multiple skill results into a unified report."""
        import anthropic
        from src.config.settings import get_settings

        # Extract all successful skill responses
        skill_reports = []
        for r in results:
            if r.success:
                response = self._extract_response(r)
                if response:
                    skill_display = r.skill_name.replace("-", " ").replace("_", " ").title()
                    skill_reports.append(f"## 技能: {skill_display}\n\n{response}")

        if not skill_reports:
            return None

        combined_reports = "\n\n---\n\n".join(skill_reports)

        # Load prompt from DB with fallback
        from src.domain.shared.services.system_prompt_service import get_system_prompt_service
        prompt_service = get_system_prompt_service()
        prompt_template = await prompt_service.get_prompt_with_fallback(
            "aggregator_integrate",
            fallback="""你是一位专业的健康评估报告整合专家。以下用户提出了健康评估请求，多个专业评估技能分别返回了各自的报告。

**用户请求**: {{user_input}}

**各技能报告**:
{{combined_reports}}

请将以上多个技能的报告整合为一份统一、连贯的健康评估报告。要求：

1. **智能整合去重**: 不要简单拼接，要识别各报告中的重复内容并合并
2. **按主题组织**: 按健康主题组织内容（如：风险等级评估、主要危险因素、干预建议等）
3. **保留关键信息**: 保留所有专业术语和具体数值（如风险评分、指标数值）
4. **专业语气**: 使用专业但易于理解的中文医学语言
5. **Markdown格式**: 使用 Markdown 格式，包含标题层级、列表、加粗等

直接输出整合后的报告，不要包含任何解释性前言。""",
        )
        try:
            prompt = prompt_template.format(
                user_input=user_input,
                combined_reports=combined_reports,
            )
        except (KeyError, IndexError):
            prompt = prompt_template

        try:
            settings = get_settings()
            client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key,
                base_url=settings.anthropic_base_url if settings.anthropic_base_url != "https://api.anthropic.com" else None,
                timeout=60.0,
            )

            logger.info(f"Starting intelligent aggregation for {len(skill_reports)} skill reports")
            response = client.messages.create(
                model=settings.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )

            aggregated = response.content[0].text
            logger.info(f"Intelligent aggregation completed, response length: {len(aggregated)}")
            return aggregated

        except Exception as e:
            logger.warning(f"LLM intelligent aggregation failed, falling back to concatenation: {e}")
            return None

    def _extract_response(self, result: SkillExecutionResult) -> Optional[str]:
        """Extract response from a skill result, trying multiple fields."""
        if result.response:
            return result.response

        # Try to extract from structured_output
        if result.structured_output:
            if isinstance(result.structured_output, dict):
                # Check for message field
                if "message" in result.structured_output:
                    return result.structured_output["message"]
                # Check for data.message
                if "data" in result.structured_output and isinstance(result.structured_output["data"], dict):
                    data = result.structured_output["data"]
                    if "message" in data:
                        return data["message"]
                # Check for final_output.message
                if "final_output" in result.structured_output:
                    final_out = result.structured_output["final_output"]
                    if isinstance(final_out, dict) and "message" in final_out:
                        return final_out["message"]

        # Try to format modules from structured_output or metadata into readable markdown
        data_source = result.structured_output or result.metadata.get("result_data")
        if data_source and isinstance(data_source, dict):
            formatted = self._format_modules_to_markdown(result.skill_name, data_source)
            if formatted:
                return formatted

        return None

    def _format_modules_to_markdown(self, skill_name: str, data: dict) -> Optional[str]:
        """Format skill output with modules into readable markdown."""
        modules = None
        # Find modules in various nested locations
        if "modules" in data and isinstance(data["modules"], dict):
            modules = data["modules"]
        elif "final_output" in data and isinstance(data["final_output"], dict):
            fo = data["final_output"]
            if "modules" in fo and isinstance(fo["modules"], dict):
                modules = fo["modules"]
        elif "data" in data and isinstance(data["data"], dict):
            d = data["data"]
            if "modules" in d and isinstance(d["modules"], dict):
                modules = d["modules"]

        if not modules:
            return None

        # Format each module section
        parts = []
        for section_name, section_content in modules.items():
            if not section_content:
                continue
            if isinstance(section_content, str) and section_content.strip():
                if section_content.strip().startswith('#'):
                    parts.append(section_content)
                else:
                    parts.append(f"### {section_name}\n\n{section_content}")
            elif isinstance(section_content, dict):
                # For dict content (like risk_assessment, health_insight from cvd skill)
                # Format as key-value
                sub_parts = []
                for k, v in section_content.items():
                    if v is not None and str(v).strip():
                        sub_parts.append(f"- **{k}**: {v}")
                if sub_parts:
                    parts.append(f"### {section_name}\n\n" + "\n".join(sub_parts))

        return "\n\n".join(parts) if parts else None

    async def merge_results(
        self,
        results: List[SkillExecutionResult],
        user_input: str,
    ) -> str:
        """Merge independent skill results with intelligent aggregation."""
        # Get all successful skills, checking both response and structured_output
        successful_with_response = []
        successful_with_structured = []
        failed = [r for r in results if not r.success]

        for r in results:
            if r.success:
                response = self._extract_response(r)
                if response:
                    successful_with_response.append((r, response))
                elif r.structured_output:
                    successful_with_structured.append(r)

        if not successful_with_response and not successful_with_structured:
            # When all skills fail or have no output, try to generate an LLM-based response
            return await self._generate_fallback_response(user_input, failed)

        # Single skill success: return directly without aggregation
        if successful_with_response and len(successful_with_response) == 1:
            response = successful_with_response[0][1]
            if failed:
                response += f"\n\n---\n> **注意**: 部分技能执行失败 ({len(failed)}个错误)，以上结果基于成功执行的技能。"
            return response

        # Multi-skill: try intelligent aggregation first
        if len(successful_with_response) > 1:
            logger.info(f"Starting intelligent aggregation for {len(successful_with_response)} successful skills")
            aggregated = await self._intelligent_aggregate(
                [r for r, _ in successful_with_response],
                user_input,
            )
            if aggregated:
                logger.info(f"Intelligent aggregation succeeded, response length: {len(aggregated)}")
                if failed:
                    aggregated += f"\n\n---\n> **注意**: 部分技能执行失败 ({len(failed)}个错误)，以上结果基于成功执行的技能。"
                return aggregated
            # Fallback to simple concatenation if LLM fails
            logger.warning("Intelligent aggregation returned None, falling back to concatenation")
            parts = ["Based on my analysis:\n"]
            for result, response in successful_with_response:
                skill_display = result.skill_name.replace("-", " ").replace("_", " ").title()
                parts.append(f"\n**{skill_display}**\n{response}\n")
            if failed:
                parts.append(f"\n---\n> **注意**: 部分技能执行失败 ({len(failed)}个错误)，以上结果基于成功执行的技能。")
            return "\n".join(parts)

        # If we only have structured outputs, generate LLM-based summary
        if successful_with_structured:
            return await self._generate_structured_summary(successful_with_structured, failed, user_input)

        return await self._generate_fallback_response(user_input, failed)

    async def _generate_structured_summary(
        self,
        structured_results: List[SkillExecutionResult],
        failed_results: List[SkillExecutionResult],
        user_input: str,
    ) -> str:
        """Generate an LLM-based summary from structured outputs."""
        import anthropic
        from src.config.settings import get_settings

        try:
            settings = get_settings()
            client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key,
                base_url=settings.anthropic_base_url,
                timeout=30.0  # Add timeout to prevent hanging
            )

            # Build context from structured outputs
            structured_summary = []
            for r in structured_results:
                summary = f"- {r.skill_name}: "
                if r.structured_output:
                    if isinstance(r.structured_output, dict):
                        if "message" in r.structured_output:
                            summary += f"Returned message: {r.structured_output['message'][:100]}..."
                        elif "data" in r.structured_output and isinstance(r.structured_output["data"], dict):
                            data = r.structured_output["data"]
                            if "message" in data:
                                summary += f"Returned: {data['message'][:100]}..."
                            elif "current_data" in data:
                                summary += f"Current data: {data['current_data'][:100]}..."
                            else:
                                summary += f"Structured data available"
                        else:
                            summary += f"Structured data: {str(r.structured_output)[:100]}..."
                structured_summary.append(summary)

            error_summary = []
            if failed_results:
                error_summary = [
                    f"- {r.skill_name}: {r.error[:80] if r.error else 'Unknown error'}..."
                    for r in failed_results
                ]

            # Load prompt from DB with fallback
            from src.domain.shared.services.system_prompt_service import get_system_prompt_service
            prompt_service = get_system_prompt_service()
            prompt_template = await prompt_service.get_prompt_with_fallback(
                "aggregator_structured_summary",
                fallback="""The user requested a health assessment: "{{user_input}}"

I successfully executed some assessment skills and got structured results:

{{structured_summary}}

{{error_summary_section}}

Please provide a helpful response to the user that:
1. Summarizes the key findings from the successful assessments (use the information provided above)
2. Mentions any data that might be missing for a complete assessment
3. If there are failed assessments, briefly note them
4. Offers to help with additional information

Respond in a helpful, professional tone in Chinese (since the user input is in Chinese).
Keep the response concise and actionable.""",
            )
            error_summary_section = f"Some skills failed:\n{chr(10).join(error_summary)}" if failed_results else ""
            try:
                prompt = prompt_template.format(
                    user_input=user_input,
                    structured_summary=chr(10).join(structured_summary),
                    error_summary_section=error_summary_section,
                )
            except (KeyError, IndexError):
                prompt = prompt_template

            response = client.messages.create(
                model=settings.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except anthropic.APITimeoutError as e:
            logger.warning(f"LLM API timeout during structured summary: {e}")
            # Fallback: try to extract and return the first message
            for r in structured_results:
                msg = self._extract_response(r)
                if msg:
                    return msg
            return "需要补充健康数据才能进行评估。请提供年龄、血压、血脂等关键指标以完成评估。"
        except anthropic.APIError as e:
            logger.warning(f"LLM API error during structured summary: {e}")
            # Fallback: try to extract and return the first message
            for r in structured_results:
                msg = self._extract_response(r)
                if msg:
                    return msg
            return "需要补充健康数据才能进行评估。请提供年龄、血压、血脂等关键指标以完成评估。"
        except Exception as e:
            logger.error(f"Unexpected error during structured summary: {e}")
            # Fallback: try to extract and return the first message
            for r in structured_results:
                msg = self._extract_response(r)
                if msg:
                    return msg
            return "需要补充健康数据才能进行评估。请提供年龄、血压、血脂等关键指标以完成评估。"

    async def _generate_fallback_response(self, user_input: str, failed_results: List[SkillExecutionResult]) -> str:
        """Generate an LLM-based fallback response when all skills fail."""
        import anthropic
        from src.config.settings import get_settings

        try:
            settings = get_settings()
            client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key,
                base_url=settings.anthropic_base_url,
                timeout=30.0
            )

            # Build context about what failed
            error_summary = "\n".join([
                f"- {r.skill_name}: {r.error[:100] if r.error else 'Unknown error'}..."
                for r in failed_results
            ])

            # Load prompt from DB with fallback
            from src.domain.shared.services.system_prompt_service import get_system_prompt_service
            prompt_service = get_system_prompt_service()
            prompt_template = await prompt_service.get_prompt_with_fallback(
                "aggregator_fallback",
                fallback="""The user requested a health assessment: "{{user_input}}"

I attempted to run multiple assessment skills but they all failed. Here are the errors:

{{error_summary}}

Please provide a helpful response to the user that:
1. Acknowledges that the automated assessment encountered technical issues
2. Summarizes what information the user provided
3. Suggests what data might be needed for a proper assessment
4. Offers to help once the technical issues are resolved

Respond in a helpful, professional tone in Chinese (since the user input is in Chinese).""",
            )
            try:
                prompt = prompt_template.format(
                    user_input=user_input,
                    error_summary=error_summary,
                )
            except (KeyError, IndexError):
                prompt = prompt_template

            response = client.messages.create(
                model=settings.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Failed to generate fallback response: {e}")
            return "I apologize, but I encountered issues processing your request. Please try again later."

    def merge_structured(
        self,
        results: List[SkillExecutionResult],
    ) -> Dict[str, Any]:
        """Merge structured outputs."""
        merged = {}

        for result in results:
            if result.success and result.structured_output:
                # Merge top-level keys
                for key, value in result.structured_output.items():
                    if key not in merged:
                        merged[key] = value
                    elif isinstance(value, dict) and isinstance(merged[key], dict):
                        merged[key].update(value)
                    elif isinstance(value, list) and isinstance(merged[key], list):
                        merged[key].extend(value)

        return merged

    def chain_results(
        self,
        results: List[SkillExecutionResult],
        user_input: str,
    ) -> str:
        """Chain sequential skill results."""
        # Return the last successful result
        for result in reversed(results):
            if result.success and result.response:
                return result.response

        return "I apologize, but I encountered issues processing your request."

    def chain_structured(
        self,
        results: List[SkillExecutionResult],
    ) -> Dict[str, Any]:
        """Chain structured outputs."""
        # Return the last successful structured output
        for result in reversed(results):
            if result.success and result.structured_output:
                return result.structured_output

        return {}

    async def enhance_results(
        self,
        results: List[SkillExecutionResult],
        user_input: str,
    ) -> str:
        """Enhance results (complementary skills) with intelligent aggregation."""
        primary = None
        complementary = []

        for result in results:
            if result.success:
                if not primary:
                    primary = result
                else:
                    complementary.append(result)

        if not primary:
            return "I apologize, but I encountered issues processing your request."

        # Single skill: return directly
        if not complementary:
            response = self._extract_response(primary) or primary.response
            return response

        # Multi-skill: try intelligent aggregation
        aggregated = await self._intelligent_aggregate(
            [primary] + complementary,
            user_input,
        )
        if aggregated:
            return aggregated

        # Fallback to simple enhancement if LLM fails
        response = self._extract_response(primary) or primary.response
        response += "\n\n## Additional Insights\n"

        for result in complementary:
            comp_response = self._extract_response(result) or result.response
            if comp_response:
                skill_display = result.skill_name.replace("-", " ").title()
                response += f"\n**{skill_display}**: {comp_response[:200]}...\n"

        return response

    def enhance_structured(
        self,
        results: List[SkillExecutionResult],
    ) -> Dict[str, Any]:
        """Enhance structured outputs."""
        enhanced = {}

        for result in results:
            if result.success and result.structured_output:
                enhanced.update(result.structured_output)

        # Add complementary results under special key
        complementary = {}
        for result in results:
            if result.success and result.structured_output:
                complementary[result.skill_name] = result.structured_output

        if complementary:
            enhanced["complementary_results"] = complementary

        return enhanced
