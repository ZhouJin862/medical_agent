"""
Multi-Skill Selection Models

Data structures for handling selection and orchestration of multiple skills.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


class RelationshipType(str, Enum):
    """Type of relationship between skills."""
    INDEPENDENT = "independent"     # Can execute in parallel
    SEQUENTIAL = "sequential"       # Must execute in order
    COMPLEMENTARY = "complementary" # Enhances each other
    ALTERNATIVE = "alternative"     # Alternative option


@dataclass
class SkillSelection:
    """Single skill selection result."""
    skill_name: Optional[str]
    confidence: float
    reasoning: str
    should_use_skill: bool
    selection_type: Literal["primary", "secondary", "alternative"] = "secondary"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_name": self.skill_name,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "should_use_skill": self.should_use_skill,
            "selection_type": self.selection_type,
        }


@dataclass
class SkillRelationship:
    """Relationship between two skills."""
    source: str  # Source skill name
    target: str  # Target skill name
    relationship_type: RelationshipType
    confidence: float = 0.8
    context_transfer: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "relationship_type": self.relationship_type.value if isinstance(self.relationship_type, RelationshipType) else self.relationship_type,
            "confidence": self.confidence,
            "context_transfer": self.context_transfer,
        }


@dataclass
class MultiSkillSelection:
    """
    Multi-skill selection result.

    Contains the primary skill, secondary skills, and their relationships.
    """
    primary: Optional[SkillSelection] = None
    secondary: List[SkillSelection] = field(default_factory=list)
    alternatives: List[SkillSelection] = field(default_factory=list)
    relationships: List[SkillRelationship] = field(default_factory=list)
    user_intent_summary: str = ""
    execution_suggestion: Literal["parallel", "sequential", "mixed"] = "sequential"

    @property
    def has_multiple_skills(self) -> bool:
        """Check if multiple skills are selected."""
        count = 0
        if self.primary:
            count += 1
        count += len(self.secondary)
        return count > 1

    @property
    def all_selected_skills(self) -> List[str]:
        """Get all selected skill names."""
        skills = []
        if self.primary and self.primary.skill_name:
            skills.append(self.primary.skill_name)
        skills.extend([s.skill_name for s in self.secondary if s.skill_name])
        return skills

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary": self.primary.to_dict() if self.primary else None,
            "secondary": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.secondary],
            "alternatives": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.alternatives],
            "relationships": [
                r.to_dict() if hasattr(r, 'to_dict') else {
                    "source": r.source,
                    "target": r.target,
                    "type": r.relationship_type.value if isinstance(r.relationship_type, RelationshipType) else r.relationship_type,
                    "confidence": r.confidence,
                    "context_transfer": r.context_transfer,
                }
                for r in self.relationships
            ],
            "user_intent_summary": self.user_intent_summary,
            "execution_suggestion": self.execution_suggestion,
            "has_multiple_skills": self.has_multiple_skills,
        }


@dataclass
class ExecutionGroup:
    """A group of skills to execute together."""
    group_id: str
    skills: List[str]
    execution_mode: Literal["parallel", "sequential"]
    dependencies: List[str] = field(default_factory=list)  # Groups to complete first


@dataclass
class ExecutionPlan:
    """
    Execution plan for multiple skills.

    Defines how to orchestrate multiple skills including
    parallel groups, sequential chains, and result aggregation.
    """
    skills: List[str]
    execution_mode: Literal["parallel", "sequential", "mixed"]
    groups: List[ExecutionGroup] = field(default_factory=list)
    aggregation_strategy: Literal["merge", "chain", "enhance"] = "merge"
    context_passing: List[Dict[str, str]] = field(default_factory=list)

    @property
    def total_skills(self) -> int:
        """Total number of skills in the plan."""
        return len(self.skills)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skills": self.skills,
            "execution_mode": self.execution_mode,
            "groups": [
                {
                    "group_id": g.group_id,
                    "skills": g.skills,
                    "execution_mode": g.execution_mode,
                    "dependencies": g.dependencies,
                }
                for g in self.groups
            ],
            "aggregation_strategy": self.aggregation_strategy,
            "context_passing": self.context_passing,
            "total_skills": self.total_skills,
        }


@dataclass
class SkillExecutionResult:
    """Result from executing a single skill."""
    skill_name: str
    success: bool
    response: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_output(self) -> bool:
        """Check if result has any output."""
        return bool(self.response or self.structured_output)


@dataclass
class MultiSkillExecutionResult:
    """
    Result from executing multiple skills.

    Contains individual skill results and aggregated output.
    """
    success: bool
    execution_plan: ExecutionPlan
    skill_results: List[SkillExecutionResult] = field(default_factory=list)
    aggregated_response: str = ""
    structured_output: Optional[Dict[str, Any]] = None
    total_execution_time_ms: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def successful_skills(self) -> List[SkillExecutionResult]:
        """Get successfully executed skills."""
        return [r for r in self.skill_results if r.success]

    @property
    def failed_skills(self) -> List[SkillExecutionResult]:
        """Get failed skills."""
        return [r for r in self.skill_results if not r.success]

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if not self.skill_results:
            return 0.0
        return len(self.successful_skills) / len(self.skill_results)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "execution_plan": self.execution_plan.to_dict(),
            "skill_results": [r.to_dict() for r in self.skill_results],
            "aggregated_response": self.aggregated_response,
            "structured_output": self.structured_output,
            "total_execution_time_ms": self.total_execution_time_ms,
            "errors": self.errors,
            "successful_count": len(self.successful_skills),
            "failed_count": len(self.failed_skills),
            "success_rate": self.success_rate,
        }
