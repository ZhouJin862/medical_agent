"""
Enhanced LLM-based Skill Selector with Multi-Skill Support.

Analyzes user input to identify multiple intents and select
appropriate skills with relationship analysis.
"""
import logging
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.models.skill_selection_models import (
    MultiSkillSelection,
    SkillSelection,
    SkillRelationship,
    RelationshipType,
    ExecutionPlan,
    ExecutionGroup,
)
from src.domain.shared.services.unified_skills_repository import (
    UnifiedSkillsRepository,
    SkillInfo,
)
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class EnhancedLLMSkillSelector:
    """
    Enhanced LLM skill selector with multi-skill support.

    Features:
    - Identifies multiple intents in user input
    - Selects primary and secondary skills
    - Analyzes relationships between skills
    - Suggests execution strategy
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the enhanced LLM skill selector.

        Args:
            session: Database session for unified repository
        """
        self._session = session
        self._repository = UnifiedSkillsRepository(session, skills_dir="skills")
        self._anthropic_api_key = get_settings().anthropic_api_key

    async def select_skills(
        self,
        user_input: str,
        conversation_context: Optional[str] = None,
    ) -> MultiSkillSelection:
        """
        Select appropriate skills for the user input.

        May return multiple skills with relationships.

        Args:
            user_input: User's input message
            conversation_context: Optional conversation context

        Returns:
            Multi-skill selection result
        """
        # Get all enabled skills
        skills = await self._repository.list_skills(enabled_only=True)

        if not skills:
            return MultiSkillSelection(
                user_intent_summary="No skills available",
                execution_suggestion="sequential"
            )

        # Build skill descriptions for LLM
        skill_descriptions = self._build_skill_descriptions(skills)

        # Use LLM to analyze and select skills
        selection = await self._llm_select_multi(
            user_input=user_input,
            skill_descriptions=skill_descriptions,
            conversation_context=conversation_context,
        )

        # Analyze relationships between selected skills
        if selection.has_multiple_skills:
            selection.relationships = await self._analyze_relationships(
                selection.all_selected_skills,
                skills
            )

        logger.info(
            f"Multi-skill selection: primary={selection.primary.skill_name if selection.primary else None}, "
            f"secondary={len(selection.secondary)}, "
            f"suggestion={selection.execution_suggestion}"
        )

        return selection

    async def create_execution_plan(
        self,
        selection: MultiSkillSelection,
        user_input: str,
    ) -> ExecutionPlan:
        """
        Create execution plan from multi-skill selection.

        Args:
            selection: Multi-skill selection result
            user_input: Original user input

        Returns:
            Execution plan for the selected skills
        """
        # Filter out redundant sub-domain skills when comprehensive skill is selected
        filtered_skills = self._filter_redundant_skills(selection.all_selected_skills)

        if not selection.has_multiple_skills:
            # Single skill - simple plan
            skill_name = selection.primary.skill_name if selection.primary else None
            return ExecutionPlan(
                skills=[skill_name] if skill_name else [],
                execution_mode="sequential",
                groups=[],
                aggregation_strategy="merge",
            )

        # Determine execution mode from suggestion
        execution_mode = selection.execution_suggestion

        if execution_mode == "parallel":
            # All skills can run in parallel
            return ExecutionPlan(
                skills=filtered_skills,
                execution_mode="parallel",
                groups=[
                    ExecutionGroup(
                        group_id="parallel_all",
                        skills=filtered_skills,
                        execution_mode="parallel",
                    )
                ],
                aggregation_strategy="merge",
            )

        elif execution_mode == "sequential":
            # Skills must run in sequence
            return ExecutionPlan(
                skills=filtered_skills,
                execution_mode="sequential",
                groups=[
                    ExecutionGroup(
                        group_id=f"step_{i}",
                        skills=[skill],
                        execution_mode="sequential",
                    )
                    for i, skill in enumerate(filtered_skills)
                ],
                aggregation_strategy="chain",
            )

        else:  # mixed
            # Analyze relationships to create mixed plan
            return await self._create_mixed_execution_plan(selection)

    def _build_skill_descriptions(self, skills: List[SkillInfo]) -> str:
        """Build skill descriptions for LLM consumption."""
        lines = ["## Available Skills\n"]

        # Group by category (layer)
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
                lines.append(f"- **{skill.name}**: {skill.description}")

        return "\n".join(lines)

    async def _llm_select_multi(
        self,
        user_input: str,
        skill_descriptions: str,
        conversation_context: Optional[str] = None,
    ) -> MultiSkillSelection:
        """
        Use LLM to select multiple skills.

        Args:
            user_input: User's input
            skill_descriptions: Formatted skill descriptions
            conversation_context: Optional conversation context

        Returns:
            Multi-skill selection result
        """
        if not self._anthropic_api_key:
            return self._fallback_select(user_input, skill_descriptions)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self._anthropic_api_key)

            system_prompt = """You are a medical skill selector with expertise in analyzing user requests.

## Your Task

Analyze the user's request and:
1. Identify ALL distinct intents/needs in the request
2. Select appropriate skills for each intent
3. Determine if skills can run in parallel or need sequential execution
4. Identify relationships between selected skills

## Selection Guidelines

### CRITICAL RULE: Intent-Based Selection

1. Select skills based ONLY on the user's **explicit request/intent** (what they ASK for)
2. Health data values are INPUTS, not triggers — do NOT select a skill just because related data exists
3. If one comprehensive/broad skill already covers the user's intent, use ONLY that skill
4. If a skill name or description says it covers "四高一重" or "comprehensive" or "综合", it covers hypertension, hyperglycemia, hyperlipidemia, obesity, hyperuricemia sub-domains. Do NOT select those individual sub-domain skills alongside it. But CVD (cardiovascular disease) risk assessment is a DIFFERENT domain — it can be selected alongside the comprehensive skill.
5. Max 2-3 skills total. Each additional skill must be justified by a DISTINCT explicit user request.

### Anti-Pattern (DO NOT DO THIS)

User says "做一下健康评估和心血管评估" with BP/sugar/lipid data:
- ❌ BAD: select chronic-disease + cvd + hypertension + hyperglycemia + hyperlipidemia + obesity + hyperuricemia (7 skills based on data)
- ✅ GOOD: select chronic-disease-risk-assessment + cvd-risk-assessment (2 skills matching the 2 explicit requests. chronic-disease already covers the "四高一重" sub-domains, so no need for individual hypertension/hyperglycemia/etc. skills)

### Execution Strategy

- Parallel: skills assess independent domains
- Sequential: one skill's output informs another
- Complementary: skills enhance each other

## Response Format

Respond with JSON only:
```json
{
  "user_intent_summary": "Brief summary of what the user wants",
  "primary_skill": "main skill name or null",
  "secondary_skills": ["skill1", "skill2"],
  "alternative_skills": ["backup_skill"],
  "relationships": [
    {
      "from": "skill1",
      "to": "skill2",
      "type": "independent|sequential|complementary",
      "reasoning": "why this relationship exists"
    }
  ],
  "execution_suggestion": "parallel|sequential|mixed",
  "reasoning": "overall explanation"
}
```

## Important Notes

- Match based on user's EXPLICIT request, not on data availability
- If user asks for "健康评估" or "心血管评估", prefer comprehensive skills over narrow ones
- Do NOT select a skill just because the user provided related health data
- "primary_skill" is the most important single skill (or null if multiple equal skills)
- "secondary_skills" should include ALL skills that match distinct explicit user requests (e.g. if user asks for both "健康评估" AND "心血管评估", put one as primary and the OTHER as secondary)
- If a comprehensive skill (e.g. chronic-disease-risk-assessment) is selected, do NOT add its sub-domain skills (hypertension, hyperglycemia, etc.) as secondary
- "execution_suggestion" should be "parallel" if skills are independent
- Be specific with skill names - use exact names from the list
"""

            user_message = f"""## User Request
{user_input}

{skill_descriptions}

## Task
Analyze this request and select appropriate skills. Respond with JSON in the specified format.
"""

            if conversation_context:
                user_message = f"""## Conversation Context
{conversation_context}

{user_message}
"""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = response.content[0].text
            logger.info(f"LLM multi-skill raw response: {response_text[:2000]}")
            return self._parse_multi_skill_response(response_text)

        except Exception as e:
            logger.error(f"LLM multi-skill selection failed: {e}")
            return self._fallback_select(user_input, skill_descriptions)

    def _parse_multi_skill_response(self, response_text: str) -> MultiSkillSelection:
        """Parse LLM JSON response into MultiSkillSelection."""
        try:
            import re

            # Extract JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")

            data = json.loads(json_str)

            # Parse primary skill
            primary = None
            if data.get("primary_skill"):
                primary = SkillSelection(
                    skill_name=data["primary_skill"].replace("_", "-"),
                    confidence=0.8,
                    reasoning=f"Primary skill for {data.get('reasoning', '')}",
                    should_use_skill=True,
                    selection_type="primary",
                )

            # Parse secondary skills (with dedup against comprehensive skills)
            secondary = []
            # If a comprehensive skill is selected, its sub-domain skills are redundant
            comprehensive_skills = {
                "chronic-disease-risk-assessment",
                "chronic-disease-risk",
            }
            # Skills that are sub-domains of chronic-disease-risk-assessment
            # NOTE: cvd-risk-assessment is NOT a sub-domain — it's a separate domain
            sub_domain_skills = {
                "hypertension-risk-assessment",
                "hyperglycemia-risk-assessment",
                "hyperlipidemia-risk-assessment",
                "obesity-risk-assessment",
                "hyperuricemia-risk-assessment",
            }
            all_selected_names = set()
            if primary:
                all_selected_names.add(primary.skill_name)
            for s in data.get("secondary_skills", []):
                all_selected_names.add(s.replace("_", "-"))

            has_comprehensive = bool(all_selected_names & comprehensive_skills)

            for skill_name in data.get("secondary_skills", []):
                normalized = skill_name.replace("_", "-")
                # Skip sub-domain skills when comprehensive skill already covers them
                if has_comprehensive and normalized in sub_domain_skills:
                    logger.info(
                        f"Skipping {normalized}: already covered by comprehensive skill"
                    )
                    continue
                secondary.append(SkillSelection(
                    skill_name=normalized,
                    confidence=0.7,
                    reasoning=f"Secondary skill from {data.get('reasoning', '')}",
                    should_use_skill=True,
                    selection_type="secondary",
                ))

            # Parse alternative skills
            alternatives = []
            for skill_name in data.get("alternative_skills", []):
                alternatives.append(SkillSelection(
                    skill_name=skill_name.replace("_", "-"),
                    confidence=0.5,
                    reasoning="Alternative option",
                    should_use_skill=False,
                    selection_type="alternative",
                ))

            # Parse relationships (with flexible field name handling)
            relationships = []
            for rel in data.get("relationships", []):
                try:
                    # Handle both "from"/"to" and "source"/"target" field names
                    source_name = rel.get("from") or rel.get("source", "")
                    target_name = rel.get("to") or rel.get("target", "")
                    if not source_name or not target_name:
                        continue
                    source_name = source_name.replace("_", "-")
                    target_name = target_name.replace("_", "-")
                    # Handle both enum name and description for type
                    rel_type_str = rel.get("type", "independent")
                    try:
                        rel_type = RelationshipType(rel_type_str)
                    except ValueError:
                        rel_type = RelationshipType.INDEPENDENT
                    rel_obj = SkillRelationship(
                        source=source_name,
                        target=target_name,
                        relationship_type=rel_type,
                        confidence=0.8,
                        context_transfer=[],
                    )
                    relationships.append(rel_obj)
                except Exception as rel_err:
                    logger.warning(f"Failed to parse relationship {rel}: {rel_err}")
                    continue

            # Auto-promote: if LLM identified a target skill in relationships
            # but forgot to put it in secondary_skills, add it automatically
            existing_skill_names = set()
            if primary:
                existing_skill_names.add(primary.skill_name)
            existing_skill_names.update(s.skill_name for s in secondary)
            for rel in relationships:
                if rel.target not in existing_skill_names and rel.source in existing_skill_names:
                    logger.info(
                        f"Auto-promoting {rel.target} from relationships to secondary "
                        f"(LLM identified it but didn't add to secondary_skills)"
                    )
                    secondary.append(SkillSelection(
                        skill_name=rel.target,
                        confidence=0.7,
                        reasoning=f"Auto-promoted from relationship: {rel.relationship_type.value}",
                        should_use_skill=True,
                        selection_type="secondary",
                    ))
                    existing_skill_names.add(rel.target)

            return MultiSkillSelection(
                primary=primary,
                secondary=secondary,
                alternatives=alternatives,
                relationships=relationships,
                user_intent_summary=data.get("user_intent_summary", ""),
                execution_suggestion=data.get("execution_suggestion", "sequential"),
            )

        except Exception as e:
            logger.error(f"Failed to parse multi-skill response: {e}")
            # Return empty selection
            return MultiSkillSelection(
                user_intent_summary="Failed to parse LLM response",
                execution_suggestion="sequential"
            )

    def _filter_redundant_skills(self, skill_names: List[str]) -> List[str]:
        """Remove sub-domain skills when a comprehensive parent skill is selected.

        Uses LLM selection reasoning + naming heuristics to detect when
        a broader skill already covers narrower sub-domain skills.
        """
        if len(skill_names) <= 1:
            return skill_names

        filtered = list(skill_names)

        # For each skill, check if it's a "comprehensive" skill whose
        # description indicates it covers multiple sub-domains.
        # Heuristic: if a skill name contains broad terms like "chronic-disease",
        # "comprehensive", "overall", "full" etc., treat it as comprehensive
        # and remove other skills whose names are sub-domains.
        broad_indicators = [
            "chronic-disease", "comprehensive", "overall",
            "full-health", "general-health", "multi-domain",
        ]

        for parent in skill_names:
            is_broad = any(indicator in parent for indicator in broad_indicators)
            if not is_broad:
                continue

            to_remove = []
            for child in filtered:
                if child == parent:
                    continue
                # A child skill is redundant if it shares the "-risk-assessment"
                # suffix pattern AND the parent is broader
                if child.endswith("-risk-assessment") and parent.endswith("-risk-assessment"):
                    # Compare domain breadth
                    parent_domain = parent.replace("-risk-assessment", "")
                    child_domain = child.replace("-risk-assessment", "")
                    # If parent domain contains child domain keywords
                    # or child is a specific condition within parent's scope
                    condition_keywords = [
                        "hypertension", "hyperglycemia", "hyperlipidemia",
                        "obesity", "hyperuricemia", "hypoglycemia",
                    ]
                    if any(kw in child_domain for kw in condition_keywords):
                        to_remove.append(child)

            for r in to_remove:
                if r in filtered:
                    filtered.remove(r)
                    logger.info(f"Skipping {r}: already covered by {parent}")

        return filtered

    async def _analyze_relationships(
        self,
        skill_names: List[str],
        all_skills: List[SkillInfo],
    ) -> List[SkillRelationship]:
        """
        Analyze relationships between selected skills.

        Args:
            skill_names: Selected skill names
            all_skills: All available skills

        Returns:
            List of relationships
        """
        relationships = []

        # Build skill lookup
        skill_map = {s.name: s for s in all_skills}

        # Check for explicit relationships in skill definitions
        for skill_name in skill_names:
            skill_info = skill_map.get(skill_name)
            if not skill_info:
                continue

            # Load full skill definition to check relationships
            skill_def = await self._repository.get_skill(skill_name)
            if skill_def and hasattr(skill_def, "metadata"):
                # Check frontmatter for relationship definitions
                # This would require parsing the frontmatter again
                # For now, use heuristic analysis
                pass

        # Heuristic: determine relationships from skill categories
        # Same category skills are usually independent
        categories = {}
        for skill_name in skill_names:
            skill_info = skill_map.get(skill_name)
            if skill_info:
                # Determine category from name/description
                category = self._determine_category(skill_info)
                categories.setdefault(category, []).append(skill_name)

        # Skills in same category are independent
        for category, skills_in_category in categories.items():
            if len(skills_in_category) > 1:
                for i, skill_a in enumerate(skills_in_category):
                    for skill_b in skills_in_category[i+1:]:
                        relationships.append(SkillRelationship(
                            source=skill_a,
                            target=skill_b,
                            relationship_type=RelationshipType.INDEPENDENT,
                        ))

        return relationships

    def _determine_category(self, skill_info: SkillInfo) -> str:
        """Determine category from skill info."""
        name_lower = skill_info.name.lower()
        desc_lower = skill_info.description.lower()

        if "assessment" in name_lower or "评估" in desc_lower:
            return "assessment"
        elif "prescription" in name_lower or "处方" in desc_lower or "建议" in desc_lower:
            return "prescription"
        elif "risk" in name_lower or "风险" in desc_lower:
            return "risk"
        else:
            return "general"

    async def _create_mixed_execution_plan(
        self,
        selection: MultiSkillSelection,
    ) -> ExecutionPlan:
        """Create mixed execution plan based on relationships."""
        # Group independent skills together
        groups = []
        group_id = 0

        processed = set()

        for skill_name in selection.all_selected_skills:
            if skill_name in processed:
                continue

            # Find skills that are independent with this one
            independent_with = [skill_name]

            for rel in selection.relationships:
                if rel.source == skill_name and rel.relationship_type == RelationshipType.INDEPENDENT:
                    if rel.target not in processed:
                        independent_with.append(rel.target)

            if len(independent_with) > 1:
                groups.append(ExecutionGroup(
                    group_id=f"group_{group_id}",
                    skills=independent_with,
                    execution_mode="parallel",
                ))
                processed.update(independent_with)
                group_id += 1
            else:
                groups.append(ExecutionGroup(
                    group_id=f"group_{group_id}",
                    skills=[skill_name],
                    execution_mode="sequential",
                ))
                processed.add(skill_name)
                group_id += 1

        return ExecutionPlan(
            skills=selection.all_selected_skills,
            execution_mode="mixed",
            groups=groups,
            aggregation_strategy="merge",
        )

    def _fallback_select(
        self,
        user_input: str,
        skill_descriptions: str,
    ) -> MultiSkillSelection:
        """Fallback keyword-based multi-skill selection."""
        user_lower = user_input.lower()

        # Extract skill names and descriptions
        import re
        skills = []
        for match in re.finditer(r'\*\*([^*]+)\*\*:\s*([^\n]+)', skill_descriptions):
            name = match.group(1)
            description = match.group(2).lower()
            skills.append((name, description))

        # Keyword mappings
        keyword_mappings = {
            "血压": ["hypertension", "blood pressure"],
            "糖尿病": ["diabetes", "hyperglycemia"],
            "血糖": ["hyperglycemia", "diabetes"],
            "血脂": ["hyperlipidemia", "lipid"],
            "胆固醇": ["cholesterol", "hyperlipidemia"],
            "痛风": ["gout", "hyperuricemia"],
            "尿酸": ["hyperuricemia", "gout"],
            "肥胖": ["obesity", "bmi"],
            "心血管": ["cvd", "cardiovascular", "heart"],
            "心脏病": ["cvd", "cardiovascular", "heart"],
            "中风": ["cvd", "stroke"],
        }

        # Score each skill
        scored_skills = []
        for name, description in skills:
            score = 0.0

            # Direct name match
            if name.lower() in user_lower:
                score += 0.8

            # Keyword matching
            for chinese_kw, eng_terms in keyword_mappings.items():
                if chinese_kw in user_lower:
                    for eng_term in eng_terms:
                        if eng_term in name.lower() or eng_term in description:
                            score += 0.4

            if score > 0:
                scored_skills.append((name, score))

        # Sort by score
        scored_skills.sort(key=lambda x: x[1], reverse=True)

        if not scored_skills:
            return MultiSkillSelection(
                user_intent_summary="No matching skills found",
                execution_suggestion="sequential"
            )

        # Select multiple skills if scores are close
        selected = []
        threshold = max(0.3, scored_skills[0][1] - 0.2)

        for name, score in scored_skills:
            if score >= threshold:
                selected.append((name, score))

        # Determine primary and secondary
        primary_skill = None
        secondary_skills = []

        if selected:
            if len(selected) == 1:
                primary_skill = selected[0][0]
            else:
                # First skill is primary
                primary_skill = selected[0][0]
                secondary_skills = [s[0] for s in selected[1:]]

        # Build selection
        result = MultiSkillSelection(
            user_intent_summary=f"Keyword-based selection: {len(selected)} skills",
            execution_suggestion="parallel" if len(selected) > 2 else "sequential",
        )

        if primary_skill:
            result.primary = SkillSelection(
                skill_name=primary_skill,
                confidence=selected[0][1],
                reasoning="Keyword match",
                should_use_skill=True,
                selection_type="primary",
            )

        for skill_name in secondary_skills:
            result.secondary.append(SkillSelection(
                skill_name=skill_name,
                confidence=0.6,
                reasoning="Keyword match",
                should_use_skill=True,
                selection_type="secondary",
            ))

        return result
