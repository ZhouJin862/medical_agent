"""
Composite Skill Executor - Executes skills that combine multiple base skills.

A composite skill references one or more base skills (file-based or database)
and applies custom configuration, business rules, and overrides.

Example:
    enterprise_skill: vip_health_plan
    base_skills:
      - hypertension-assessment
      - diabetes-assessment
    overrides:
      response_style: "vip_detailed"
      include_recommendations: true
"""
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.domain.shared.models.skill_models import (
    SkillDefinition,
    SkillMetadata,
    SkillSource,
)
from src.domain.shared.services.unified_skills_repository import (
    UnifiedSkillsRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class CompositeSkillConfig:
    """Configuration for a composite skill."""

    # Base skills to load (can reference file or database skills)
    base_skills: List[str] = field(default_factory=list)

    # Override settings to apply
    override_settings: Dict[str, Any] = field(default_factory=dict)

    # Business rules to evaluate
    business_rules: Dict[str, Any] = field(default_factory=dict)

    # Workflow configuration
    workflow_config: Dict[str, Any] = field(default_factory=dict)

    # Display configuration
    display_name: Optional[str] = None
    response_style: str = "standard"

    # Execution mode
    execution_mode: str = "sequential"  # sequential, parallel, conditional


@dataclass
class CompositeSkillResult:
    """Result from executing a composite skill."""

    success: bool
    response: str
    skill_results: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompositeSkillExecutor:
    """
    Executor for composite skills.

    A composite skill combines multiple base skills with custom configuration.
    """

    def __init__(self, repository: UnifiedSkillsRepository):
        """
        Initialize the executor.

        Args:
            repository: Unified skills repository for loading base skills
        """
        self._repository = repository
        self._cache: Dict[str, CompositeSkillConfig] = {}

    async def execute_composite_skill(
        self,
        config: CompositeSkillConfig,
        user_input: str,
        patient_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[str] = None,
    ) -> CompositeSkillResult:
        """
        Execute a composite skill.

        Args:
            config: Composite skill configuration
            user_input: User's input message
            patient_context: Patient information
            conversation_context: Conversation history

        Returns:
            Composite skill execution result
        """
        start_time = time.time()
        skill_results = []

        logger.info(
            f"Executing composite skill with {len(config.base_skills)} base skills: "
            f"{config.base_skills}"
        )

        try:
            # Load all base skills
            loaded_skills = []
            for skill_name in config.base_skills:
                skill = await self._repository.get_skill(skill_name)
                if skill:
                    loaded_skills.append(skill)
                else:
                    logger.warning(f"Base skill not found: {skill_name}")

            if not loaded_skills:
                return CompositeSkillResult(
                    success=False,
                    response="No base skills could be loaded.",
                    error=f"None of the base skills were found: {config.base_skills}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Execute based on mode
            if config.execution_mode == "parallel":
                results = await self._execute_parallel(
                    loaded_skills,
                    user_input,
                    patient_context,
                    conversation_context,
                    config,
                )
            else:
                results = await self._execute_sequential(
                    loaded_skills,
                    user_input,
                    patient_context,
                    conversation_context,
                    config,
                )

            skill_results = results

            # Aggregate responses
            aggregated_response = self._aggregate_responses(
                results,
                config.override_settings,
            )

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(
                f"Composite skill executed successfully in {execution_time}ms, "
                f"{len(results)} base skill results"
            )

            return CompositeSkillResult(
                success=True,
                response=aggregated_response,
                skill_results=results,
                execution_time_ms=execution_time,
                metadata={
                    "base_skills": config.base_skills,
                    "loaded_skills": [s.metadata.name for s in loaded_skills],
                    "execution_mode": config.execution_mode,
                },
            )

        except Exception as e:
            logger.error(f"Composite skill execution failed: {e}")
            import traceback
            traceback.print_exc()

            return CompositeSkillResult(
                success=False,
                response=f"Skill execution failed: {str(e)}",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _execute_sequential(
        self,
        skills: List[SkillDefinition],
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
        config: CompositeSkillConfig,
    ) -> List[Dict[str, Any]]:
        """Execute skills sequentially, passing context between them."""
        results = []
        accumulated_context = conversation_context or ""

        for skill in skills:
            try:
                # Build prompt with accumulated context
                prompt = self._build_skill_prompt(
                    skill,
                    user_input,
                    patient_context,
                    accumulated_context,
                    config.override_settings,
                )

                # Import LLM client for execution
                from src.infrastructure.llm.claude_client import get_claude_client

                client = get_claude_client()
                response = await client.generate(
                    system_prompt=skill.content,
                    user_prompt=prompt,
                    max_tokens=2000,
                )

                result = {
                    "skill_name": skill.metadata.name,
                    "success": True,
                    "response": response,
                    "source": skill.metadata.source.value,
                }
                results.append(result)

                # Accumulate response for next skill
                accumulated_context += f"\n\n[{skill.metadata.name}]:\n{response}\n"

            except Exception as e:
                logger.error(f"Base skill {skill.metadata.name} failed: {e}")
                results.append({
                    "skill_name": skill.metadata.name,
                    "success": False,
                    "error": str(e),
                    "source": skill.metadata.source.value,
                })

        return results

    async def _execute_parallel(
        self,
        skills: List[SkillDefinition],
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
        config: CompositeSkillConfig,
    ) -> List[Dict[str, Any]]:
        """Execute skills in parallel."""
        import asyncio

        async def execute_one(skill: SkillDefinition) -> Dict[str, Any]:
            try:
                prompt = self._build_skill_prompt(
                    skill,
                    user_input,
                    patient_context,
                    conversation_context,
                    config.override_settings,
                )

                from src.infrastructure.llm.claude_client import get_claude_client

                client = get_claude_client()
                response = await client.generate(
                    system_prompt=skill.content,
                    user_prompt=prompt,
                    max_tokens=2000,
                )

                return {
                    "skill_name": skill.metadata.name,
                    "success": True,
                    "response": response,
                    "source": skill.metadata.source.value,
                }
            except Exception as e:
                logger.error(f"Base skill {skill.metadata.name} failed: {e}")
                return {
                    "skill_name": skill.metadata.name,
                    "success": False,
                    "error": str(e),
                    "source": skill.metadata.source.value,
                }

        tasks = [execute_one(skill) for skill in skills]
        return await asyncio.gather(*tasks)

    def _build_skill_prompt(
        self,
        skill: SkillDefinition,
        user_input: str,
        patient_context: Optional[Dict[str, Any]],
        conversation_context: Optional[str],
        overrides: Dict[str, Any],
    ) -> str:
        """Build the prompt for skill execution."""
        prompt_parts = []

        # Add user input
        prompt_parts.append(f"User Input:\n{user_input}")

        # Add patient context
        if patient_context:
            prompt_parts.append("\nPatient Context:")
            if patient_context.get("basic_info"):
                prompt_parts.append(f"- Basic Info: {patient_context['basic_info']}")
            if patient_context.get("vital_signs"):
                prompt_parts.append(f"- Vital Signs: {patient_context['vital_signs']}")
            if patient_context.get("medical_history"):
                prompt_parts.append(f"- Medical History: {patient_context['medical_history']}")

        # Add conversation context
        if conversation_context:
            prompt_parts.append(f"\nConversation Context:\n{conversation_context}")

        # Add override instructions
        if overrides:
            prompt_parts.append("\nAdditional Instructions:")
            for key, value in overrides.items():
                if key not in ["response_style", "internal"]:
                    prompt_parts.append(f"- {key}: {value}")

            # Add response style
            response_style = overrides.get("response_style", "standard")
            if response_style == "vip_detailed":
                prompt_parts.append("\nPlease provide a detailed, personalized response.")

        return "\n".join(prompt_parts)

    def _aggregate_responses(
        self,
        results: List[Dict[str, Any]],
        overrides: Dict[str, Any],
    ) -> str:
        """Aggregate responses from multiple skills."""
        successful_results = [r for r in results if r.get("success")]

        if not successful_results:
            return "I apologize, but I encountered issues processing your request."

        # Single skill result
        if len(successful_results) == 1:
            return successful_results[0]["response"]

        # Multiple results - need aggregation
        response_style = overrides.get("response_style", "standard")

        if response_style == "vip_detailed":
            return self._aggregate_vip_style(successful_results)
        else:
            return self._aggregate_standard_style(successful_results)

    def _aggregate_standard_style(self, results: List[Dict[str, Any]]) -> str:
        """Standard aggregation - combine responses."""
        parts = ["Based on my analysis:\n"]

        for result in results:
            skill_name = result["skill_name"].replace("-", " ").replace("_", " ").title()
            parts.append(f"\n**{skill_name}:**\n{result['response']}")

        return "\n".join(parts)

    def _aggregate_vip_style(self, results: List[Dict[str, Any]]) -> str:
        """VIP detailed aggregation."""
        parts = ["## Personalized Health Assessment\n\n"]

        # Add executive summary
        parts.append("### Executive Summary\n\n")
        parts.append("I've conducted a comprehensive assessment across multiple health domains. ")
        parts.append("Here are your personalized results:\n\n")

        # Detailed findings
        parts.append("### Detailed Findings\n\n")

        for result in results:
            skill_name = result["skill_name"].replace("-", " ").replace("_", " ").title()
            parts.append(f"#### {skill_name}\n")
            parts.append(f"{result['response']}\n\n")

        # Add recommendations section
        parts.append("### Personalized Recommendations\n\n")
        parts.append("Based on the above assessment, I recommend:\n\n")
        parts.append("- Please review the detailed findings above\n")
        parts.append("- Consider scheduling a follow-up consultation\n")
        parts.append("- Maintain regular monitoring of your health indicators\n")

        return "".join(parts)

    async def load_composite_config_from_database(
        self,
        skill_name: str,
    ) -> Optional[CompositeSkillConfig]:
        """
        Load composite skill configuration from database.

        Args:
            skill_name: Name of the enterprise skill

        Returns:
            Composite skill configuration or None
        """
        # Check cache first
        if skill_name in self._cache:
            return self._cache[skill_name]

        try:
            from sqlalchemy import select
            from src.infrastructure.persistence.models.skill_models import SkillModel

            # Load from database
            stmt = select(SkillModel).where(
                SkillModel.skill_name == skill_name,
                SkillModel.is_enabled == True,
            )
            result = await self._repository._session.execute(stmt)
            skill = result.scalar_one_or_none()

            if not skill or not skill.skill_config:
                return None

            # Parse composite configuration
            config = self._parse_composite_config(skill.skill_config)
            if config:
                self._cache[skill_name] = config
                return config

        except Exception as e:
            logger.error(f"Failed to load composite config for {skill_name}: {e}")

        return None

    def _parse_composite_config(self, config: Dict[str, Any]) -> Optional[CompositeSkillConfig]:
        """Parse composite skill configuration from database config."""
        try:
            # Check if this is a composite skill
            base_skills = config.get("base_skills", [])
            if not base_skills:
                return None

            return CompositeSkillConfig(
                base_skills=base_skills,
                override_settings=config.get("override_settings", {}),
                business_rules=config.get("business_rules", {}),
                workflow_config=config.get("workflow_config", {}),
                display_name=config.get("display_name"),
                response_style=config.get("response_style", "standard"),
                execution_mode=config.get("execution_mode", "sequential"),
            )
        except Exception as e:
            logger.error(f"Failed to parse composite config: {e}")
            return None

    def invalidate_cache(self, skill_name: Optional[str] = None):
        """Invalidate cached configurations."""
        if skill_name:
            self._cache.pop(skill_name, None)
        else:
            self._cache.clear()
