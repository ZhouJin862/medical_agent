"""
LLM-based Skill Selector.

Uses LLM to select appropriate skills based on user input and skill descriptions.
Implements progressive disclosure by providing only metadata to LLM.
"""
import logging
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.services.unified_skills_repository import UnifiedSkillsRepository, SkillInfo
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SkillSelection:
    """Result of skill selection."""
    skill_name: Optional[str]
    confidence: float
    reasoning: str
    alternative_skills: List[str]
    should_use_skill: bool


class LLMSkillSelector:
    """
    LLM-based skill selector.

    Uses LLM to intelligently select skills based on:
    1. User input
    2. Skill descriptions (from metadata only)
    3. Conversation context
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the LLM skill selector.

        Args:
            session: Database session for unified repository
        """
        self._session = session
        self._repository = UnifiedSkillsRepository(session, skills_dir="skills")
        self._anthropic_api_key = get_settings().anthropic_api_key

    async def select_skill(
        self,
        user_input: str,
        conversation_context: Optional[str] = None,
    ) -> SkillSelection:
        """
        Select the most appropriate skill for the user input.

        Args:
            user_input: User's input message
            conversation_context: Optional conversation context

        Returns:
            Skill selection result
        """
        # Get all enabled skills
        skills = await self._repository.list_skills(enabled_only=True)

        if not skills:
            return SkillSelection(
                skill_name=None,
                confidence=0.0,
                reasoning="No skills available",
                alternative_skills=[],
                should_use_skill=False,
            )

        # Build skill descriptions for LLM
        skill_descriptions = self._build_skill_descriptions(skills)

        # Use LLM to select skill
        selection = await self._llm_select(user_input, skill_descriptions, conversation_context)

        logger.info(
            f"LLM skill selection: {selection.skill_name} "
            f"(confidence: {selection.confidence})"
        )

        return selection

    def _build_skill_descriptions(self, skills: List[SkillInfo]) -> str:
        """
        Build skill descriptions for LLM consumption.

        Only includes metadata (name + description) for progressive disclosure.

        Args:
            skills: List of available skills

        Returns:
            Formatted skill descriptions
        """
        lines = ["## Available Skills\n"]

        # Group by layer
        by_layer: Dict[str, List[SkillInfo]] = {
            "basic": [],
            "domain": [],
            "composite": [],
        }

        for skill in skills:
            by_layer.setdefault(skill.layer, []).append(skill)

        for layer in ["basic", "domain", "composite"]:
            layer_skills = by_layer.get(layer, [])
            if not layer_skills:
                continue

            layer_name = layer.capitalize()
            lines.append(f"\n### {layer_name} Skills\n")

            for skill in layer_skills:
                source_tag = "" if skill.source == "file" else " [database]"
                lines.append(f"- **{skill.name}**: {skill.description}{source_tag}")

        return "\n".join(lines)

    async def _llm_select(
        self,
        user_input: str,
        skill_descriptions: str,
        conversation_context: Optional[str] = None,
    ) -> SkillSelection:
        """
        Use LLM to select appropriate skill.

        Args:
            user_input: User's input message
            skill_descriptions: Formatted skill descriptions
            conversation_context: Optional conversation context

        Returns:
            Skill selection result
        """
        if not self._anthropic_api_key:
            # Fallback to keyword matching
            return self._keyword_select(user_input, skill_descriptions)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self._anthropic_api_key)

            # Build system prompt (load from DB with fallback)
            from src.domain.shared.services.system_prompt_service import get_system_prompt_service
            prompt_service = get_system_prompt_service()
            system_prompt = await prompt_service.get_prompt_with_fallback(
                "skill_selector_single_system",
                fallback="""You are a medical skill selector. Your task is to select the most appropriate skill for handling a user request.

## Instructions

1. Analyze the user's request carefully
2. Review the available skills and their descriptions
3. Select the skill that best matches the user's intent
4. If multiple skills could apply, choose the most specific one
5. If no skill is a good match, indicate that general conversation is appropriate

## Response Format

Respond in JSON format:
```json
{
  "selected_skill": "skill-name or null",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation of why this skill was chosen",
  "alternative_skills": ["other-skill-name1", "other-skill-name2"],
  "should_use_skill": true or false
}
```

## Important Notes

- Only select a skill if the user's request clearly matches the skill's purpose
- "should_use_skill" should be true only if confidence >= 0.7
- For general chat or unclear requests, set "selected_skill" to null and "should_use_skill" to false
- Consider the specificity of the match (exact match > partial match > general match)
""",
            )

            # Build user message
            user_message = f"""## User Request
{user_input}

{skill_descriptions}

## Task
Select the most appropriate skill for this user request. Respond with JSON in the specified format."""

            if conversation_context:
                user_message = f"""## Conversation Context
{conversation_context}

{user_message}"""

            # Call LLM
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = response.content[0].text

            # Parse JSON response
            return self._parse_selection_response(response_text)

        except Exception as e:
            logger.error(f"LLM skill selection failed: {e}")
            return self._keyword_select(user_input, skill_descriptions)

    def _keyword_select(
        self,
        user_input: str,
        skill_descriptions: str,
    ) -> SkillSelection:
        """
        Fallback keyword-based skill selection.

        Args:
            user_input: User's input message
            skill_descriptions: Formatted skill descriptions

        Returns:
            Skill selection result
        """
        user_input_lower = user_input.lower()

        # Extract skill names and descriptions
        import re
        skills = []
        for match in re.finditer(r'\*\*([^*]+)\*\*:\s*([^\n]+)', skill_descriptions):
            name = match.group(1)
            description = match.group(2).lower()
            skills.append((name, description))

        # Chinese keyword to English keyword/skill name mappings
        keyword_mappings = {
            "血压": ["hypertension", "blood pressure", "bp"],
            "糖尿病": ["diabetes", "hyperglycemia", "blood sugar", "glucose"],
            "血糖": ["hyperglycemia", "blood sugar", "glucose"],
            "血脂": ["hyperlipidemia", "blood lipid", "lipid", "cholesterol"],
            "胆固醇": ["cholesterol", "hyperlipidemia"],
            "痛风": ["gout", "hyperuricemia", "uric acid"],
            "尿酸": ["hyperuricemia", "uric acid", "gout"],
            "肥胖": ["obesity", "bmi", "weight"],
            "体重": ["obesity", "bmi", "weight", "weight management"],
            "bmi": ["obesity", "bmi", "weight"],
            "体检": ["assessment", "health assessment", "checkup"],
            "健康": ["health", "wellness"],
            "用药": ["medication", "drug", "medicine", "pharmacy"],
            "药物": ["medication", "drug", "medicine", "pharmacy"],
        }

        # Score each skill
        scored_skills = []
        for name, description in skills:
            score = 0.0

            # Exact name match (rare but possible)
            if name.lower() in user_input_lower:
                score += 0.8

            # Keyword matching with Chinese-English mapping
            for chinese_keyword, english_terms in keyword_mappings.items():
                if chinese_keyword in user_input_lower:
                    # Check if any English term matches skill name or description
                    for eng_term in english_terms:
                        if eng_term in name.lower() or eng_term in description:
                            score += 0.5
                            break

            # Direct English keyword matching in description
            english_keywords = ["blood pressure", "hypertension", "diabetes",
                              "hyperglycemia", "hyperlipidemia", "gout",
                              "hyperuricemia", "obesity", "cholesterol",
                              "medication", "assessment", "cardiovascular"]
            for keyword in english_keywords:
                if keyword in user_input_lower and keyword in description:
                    score += 0.4

            scored_skills.append((name, score))

        # Sort by score
        scored_skills.sort(key=lambda x: x[1], reverse=True)

        if scored_skills and scored_skills[0][1] >= 0.5:
            best_skill, score = scored_skills[0]
            alternatives = [s[0] for s in scored_skills[1:4] if s[1] > 0.3]

            return SkillSelection(
                skill_name=best_skill,
                confidence=min(score, 1.0),
                reasoning=f"Keyword match for '{best_skill}'",
                alternative_skills=alternatives,
                should_use_skill=score >= 0.5,  # Lower threshold for keyword match
            )

        # No good match
        return SkillSelection(
            skill_name=None,
            confidence=0.0,
            reasoning="No skill matched the user input",
            alternative_skills=[s[0] for s in scored_skills[:3]],
            should_use_skill=False,
        )

    def _parse_selection_response(self, response_text: str) -> SkillSelection:
        """
        Parse LLM JSON response.

        Args:
            response_text: LLM response text

        Returns:
            Parsed skill selection
        """
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")

            data = json.loads(json_str)

            # Normalize skill name: convert underscores to hyphens (LLM often uses underscores)
            skill_name = data.get("selected_skill")
            if skill_name:
                skill_name = skill_name.replace("_", "-")

            # Normalize alternative skills too
            alternative_skills = data.get("alternative_skills", [])
            alternative_skills = [s.replace("_", "-") for s in alternative_skills]

            return SkillSelection(
                skill_name=skill_name,
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", ""),
                alternative_skills=alternative_skills,
                should_use_skill=data.get("should_use_skill", False),
            )

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return default selection
            return SkillSelection(
                skill_name=None,
                confidence=0.0,
                reasoning="Failed to parse LLM response",
                alternative_skills=[],
                should_use_skill=False,
            )


class ClaudeSkillsExecutor:
    """
    Executor for Claude Skills (file system based).

    Loads and executes Claude Skills with progressive disclosure.

    For file-based skills with SKILL.md workflow definitions, uses script executor.
    For prompt-based skills, uses LLM generation.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Claude skills executor.

        Args:
            session: Database session
        """
        self._session = session
        self._repository = UnifiedSkillsRepository(session, skills_dir="skills")

    async def execute_skill(
        self,
        skill_name: str,
        user_input: str,
        patient_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a Claude Skill.

        Args:
            skill_name: Name of the skill to execute
            user_input: User's input message
            patient_context: Optional patient context data
            conversation_context: Optional conversation context

        Returns:
            Execution result with response and metadata
        """
        # Load skill definition
        skill_def = await self._repository.get_skill(skill_name)

        if not skill_def:
            return {
                "success": False,
                "error": f"Skill not found: {skill_name}",
                "skill_name": skill_name,
            }

        # Check if this is a workflow-based skill (has scripts directory with SKILL.md workflow)
        is_workflow = self._is_workflow_skill(skill_name)

        if is_workflow:
            logger.info(f"Executing workflow-based skill: {skill_name} using script executor")
            return await self._execute_workflow_skill(
                skill_name=skill_name,
                user_input=user_input,
                patient_context=patient_context,
            )

        # For prompt-based skills, use LLM generation
        try:
            # Build enhanced prompt with skill content
            enhanced_prompt = self._build_enhanced_prompt(
                skill_def=skill_def,
                user_input=user_input,
                patient_context=patient_context,
                conversation_context=conversation_context,
            )

            # Generate response using LLM
            response = await self._generate_llm_response(enhanced_prompt)

            return {
                "success": True,
                "skill_name": skill_name,
                "response": response,
                "skill_source": "file",
                "reference_files_loaded": [],
            }

        except Exception as e:
            logger.error(f"Failed to execute skill {skill_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "skill_name": skill_name,
            }

    def _is_workflow_skill(self, skill_name: str) -> bool:
        """
        Check if a skill is workflow-based (has scripts directory with executable steps).

        Args:
            skill_name: Name of the skill

        Returns:
            True if this is a workflow-based skill that should use script executor
        """
        try:
            from pathlib import Path
            import os

            # Get the project root - check if we're in src/ or project root
            cwd = Path(os.getcwd())
            logger.info(f"Checking workflow skill: {skill_name}, cwd: {cwd}")

            # Try different possible paths
            possible_paths = [
                Path("skills") / skill_name,  # Relative from project root
                cwd / "skills" / skill_name,  # From current directory
                cwd.parent / "skills" / skill_name,  # From src/ directory
                Path("../skills") / skill_name,  # From src/ subdirectory
            ]

            skill_md = None
            for path in possible_paths:
                md_file = path / "SKILL.md"
                if md_file.exists():
                    skill_md = md_file
                    logger.info(f"Found SKILL.md at: {skill_md}")
                    break

            if not skill_md:
                logger.warning(f"SKILL.md not found for skill: {skill_name}")
                return False

            # Check if SKILL.md contains workflow steps (### 步骤N: patterns)
            # or has a tools: section with script references
            content = skill_md.read_text(encoding='utf-8')
            import re
            has_workflow = bool(re.search(r'### 步骤\d+[:：]', content))
            if not has_workflow:
                # Also treat skills with tools: - script: as workflow skills
                has_workflow = bool(re.search(r'tools:\s*\n\s+-\s+script:', content))
            logger.info(f"Skill {skill_name} has workflow: {has_workflow}")
            return has_workflow
        except Exception as e:
            logger.error(f"Error checking workflow skill {skill_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _execute_workflow_skill(
        self,
        skill_name: str,
        user_input: str,
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a workflow-based skill using the script executor.

        Args:
            skill_name: Name of the skill
            user_input: User input message
            patient_context: Patient context data

        Returns:
            Execution result with response
        """
        try:
            from pathlib import Path
            import asyncio
            import json

            # Import script executor
            from src.infrastructure.agent.skill_md_executor import execute_skill_via_skill_md

            # Build input data for skill scripts
            input_data = self._build_skill_input_data(
                user_input=user_input,
                patient_context=patient_context,
            )

            # Execute skill in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: execute_skill_via_skill_md(skill_name, input_data)
            )

            # Process result
            if result.get("success"):
                final_output = result.get("final_output", {})
                # Extract structured_result before unwrapping (script puts it
                # alongside final_output, and the unwrap below discards it).
                raw_structured_result = (
                    result.get("structured_result")
                    or (isinstance(final_output, dict) and final_output.get("structured_result"))
                    or None
                )
                if isinstance(final_output, dict):
                    # Unwrap nested final_output (skill_md_executor wraps step output)
                    if "final_output" in final_output and isinstance(final_output["final_output"], dict):
                        inner = final_output["final_output"]
                        if "modules" in inner:
                            final_output = inner

                    # Modules can be at final_output.modules (cvd-risk-assessment)
                    # or final_output.data.modules
                    data = final_output.get("data", final_output)

                    # Check for incomplete status
                    if isinstance(data, dict) and data.get("status") == "incomplete":
                        return {
                            "success": True,
                            "skill_name": skill_name,
                            "response": final_output,
                            "skill_source": "file",
                            "is_incomplete": True,
                        }

                    # Check for modules (complete assessment)
                    if isinstance(data, dict) and "modules" in data:
                        response = self._format_modules_response(data)
                        structured = dict(data)
                        if raw_structured_result:
                            structured["structured_result"] = raw_structured_result
                        return {
                            "success": True,
                            "skill_name": skill_name,
                            "response": response,
                            "skill_source": "file",
                            "structured_output": structured,
                        }

                    # If final_output itself has modules (no data wrapper)
                    if "modules" in final_output:
                        response = self._format_modules_response(final_output)
                        structured = dict(final_output)
                        if raw_structured_result:
                            structured["structured_result"] = raw_structured_result
                        return {
                            "success": True,
                            "skill_name": skill_name,
                            "response": response,
                            "skill_source": "file",
                            "structured_output": structured,
                        }

                    # If the skill returned a direct response string
                    if "response" in final_output and isinstance(final_output["response"], str):
                        return {
                            "success": True,
                            "skill_name": skill_name,
                            "response": final_output["response"],
                            "skill_source": "file",
                        }

                    # Return the final_output as-is if it's a valid dict
                    if final_output:
                        logger.info(f"Workflow skill returned unexpected format, passing through: {list(final_output.keys())}")
                        return {
                            "success": True,
                            "skill_name": skill_name,
                            "response": str(final_output),
                            "skill_source": "file",
                            "structured_output": final_output,
                        }

            # Handle error or unexpected format
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "skill_name": skill_name,
            }

        except Exception as e:
            logger.error(f"Failed to execute workflow skill {skill_name}: {e}")
            import traceback
            return {
                "success": False,
                "error": str(e),
                "skill_name": skill_name,
            }

    def _build_skill_input_data(
        self,
        user_input: str,
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build input data format expected by skill scripts.

        Args:
            user_input: User's raw input
            patient_context: Patient context from agent

        Returns:
            Input data dict for skill scripts
        """
        input_data = {
            "user_input": user_input,
            "vital_signs": {},
            "patient_data": {},
            "medical_history": {},
        }

        if patient_context:
            # Extract basic info
            if patient_context.get("basic_info"):
                basic = patient_context["basic_info"]
                input_data["patient_data"] = {
                    "name": basic.get("patient_id", "患者"),
                    "age": basic.get("age"),
                    "gender": basic.get("gender", "male"),
                    "party_id": basic.get("party_id"),
                    "source": basic.get("source"),
                }

            # Extract vital signs
            if patient_context.get("vital_signs"):
                input_data["vital_signs"] = patient_context["vital_signs"]

            # Extract medical history
            if patient_context.get("medical_history"):
                input_data["medical_history"] = patient_context["medical_history"]

        return input_data

    def _format_modules_response(self, data: Dict[str, Any]) -> str:
        """
        Format modules from skill into a readable response.

        Args:
            data: Skill result data with modules

        Returns:
            Formatted response string
        """
        import json as _json
        modules = data.get("modules", {})
        response_parts = []

        for section_name, section_content in modules.items():
            if not section_content:
                continue
            if isinstance(section_content, str):
                if section_content.strip():
                    response_parts.append(f"\n## {section_name}\n\n{section_content}")
            elif isinstance(section_content, dict):
                # Format dict content as structured text
                response_parts.append(f"\n## {section_name}\n")
                response_parts.append(self._format_dict_section(section_content))
            elif isinstance(section_content, list):
                for item in section_content:
                    if isinstance(item, str) and item.strip():
                        response_parts.append(f"- {item}")

        return "\n".join(response_parts) if response_parts else "评估完成，但未返回详细内容。"

    def _format_dict_section(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Format a dict section into readable text."""
        parts = []
        prefix = "  " * indent
        for key, value in data.items():
            display_key = key.replace("_", " ").title()
            if isinstance(value, dict):
                parts.append(f"{prefix}- **{display_key}**:")
                parts.append(self._format_dict_section(value, indent + 1))
            elif isinstance(value, list):
                parts.append(f"{prefix}- **{display_key}**: {', '.join(str(v) for v in value)}")
            else:
                parts.append(f"{prefix}- **{display_key}**: {value}")
        return "\n".join(parts)

    def _build_enhanced_prompt(
        self,
        skill_def,
        user_input: str,
        patient_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[str] = None,
    ) -> str:
        """
        Build enhanced prompt with skill content.

        Args:
            skill_def: Skill definition
            user_input: User's input
            patient_context: Patient data
            conversation_context: Conversation history

        Returns:
            Enhanced prompt for LLM
        """
        prompt_parts = []

        # User input
        prompt_parts.append(f"# User Input\n{user_input}\n")

        # Log if user_input contains retrieved data info
        if "### IMPORTANT: User health data already retrieved" in user_input:
            logger.info("User input contains retrieved health data info from Ping An")
            logger.info(f"User input starts with: {user_input[:200]}")

        # Skill content (this is the progressive disclosure part)
        prompt_parts.append(f"# Skill: {skill_def.metadata.name}\n")
        prompt_parts.append(f"{skill_def.content}\n")

        # Patient context
        if patient_context:
            prompt_parts.append("\n# Patient Context\n")
            if patient_context.get("basic_info"):
                prompt_parts.append(f"**Basic Info**: {patient_context['basic_info']}\n")
            if patient_context.get("vital_signs"):
                prompt_parts.append(f"**Vital Signs**: {patient_context['vital_signs']}\n")
            if patient_context.get("medical_history"):
                prompt_parts.append(f"**Medical History**: {patient_context['medical_history']}\n")
            # Include retrieved data info if available
            if patient_context.get("retrieved_data_info"):
                prompt_parts.append(f"\n{patient_context['retrieved_data_info']}\n")

        # Conversation context
        if conversation_context:
            prompt_parts.append(f"\n# Conversation Context\n{conversation_context}\n")

        # Instructions
        prompt_parts.append("\n# Instructions\n")
        prompt_parts.append(
            "Based on the skill instructions above, provide a helpful response "
            "to the user. Follow the skill's workflow and recommendations."
        )

        return "\n".join(prompt_parts)

    async def _generate_llm_response(self, prompt: str) -> str:
        """Generate LLM response."""
        try:
            import anthropic

            settings = get_settings()
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

            response = client.messages.create(
                model=settings.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            raise
