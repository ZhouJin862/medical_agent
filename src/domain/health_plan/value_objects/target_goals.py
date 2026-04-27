"""Target Goals value object."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class GoalStatus(Enum):
    """Status of a goal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"


@dataclass(frozen=True)
class TargetGoal:
    """A single target goal within a health plan."""
    description: str
    target_value: Optional[str] = None
    deadline: Optional[datetime] = None
    status: GoalStatus = GoalStatus.PENDING
    category: Optional[str] = None


@dataclass(frozen=True)
class TargetGoals:
    """Value object representing collection of target goals for a health plan."""

    goals: tuple[TargetGoal, ...] = field(default_factory=tuple)

    def __post_init__(self):
        goals_list = list(self.goals)
        object.__setattr__(self, '_goals', tuple(goals_list))

    @property
    def active_goals(self) -> tuple[TargetGoal, ...]:
        """Get all active (pending or in_progress) goals."""
        return tuple(
            g for g in self.goals
            if g.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS)
        )

    @property
    def achieved_goals(self) -> tuple[TargetGoal, ...]:
        """Get all achieved goals."""
        return tuple(g for g in self.goals if g.status == GoalStatus.ACHIEVED)

    def add_goal(self, goal: TargetGoal) -> 'TargetGoals':
        """Add a new goal."""
        new_goals = tuple(self.goals) + (goal,)
        return TargetGoals(goals=new_goals)

    def __len__(self) -> int:
        return len(self.goals)

    def __iter__(self):
        return iter(self.goals)
