"""
Skill Optimizer Service

Automatically optimizes skill prompt templates using DSPy Teleprompter concepts.
Improves prompt quality through iterative testing and refinement.
"""

import logging
import json
from typing import Any, Optional, List, Dict, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session_context
from src.infrastructure.persistence.models.skill_models import SkillModel
from src.application.services.skill_prompt_template_service import SkillPromptTemplateService
from src.infrastructure.dspy.base_skill import BaseSkill, SkillConfig
from src.infrastructure.llm import LLMFactory, ModelProvider

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """
    Result of a prompt optimization iteration.

    Attributes:
        iteration: Iteration number
        prompt: The prompt used
        score: Quality score (0-1)
        metrics: Evaluation metrics
        timestamp: When this iteration ran
    """
    iteration: int
    prompt: str
    score: float
    metrics: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TrainingExample:
    """
    A single training example for optimization.

    Attributes:
        inputs: Input values for the skill
        expected_output: Expected output (for comparison)
        actual_output: Actual output from current prompt
        user_feedback: Optional user feedback score
        metadata: Additional metadata
    """
    inputs: Dict[str, Any]
    expected_output: Dict[str, Any]
    actual_output: Optional[Dict[str, Any]] = None
    user_feedback: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationConfig:
    """
    Configuration for prompt optimization.

    Attributes:
        max_iterations: Maximum optimization iterations
        target_score: Target quality score to achieve
        improvement_threshold: Minimum improvement to continue
        examples: Training examples to use
        eval_function: Custom evaluation function
    """
    max_iterations: int = 10
    target_score: float = 0.85
    improvement_threshold: float = 0.05
    examples: List[TrainingExample] = field(default_factory=list)
    eval_function: Optional[Callable[[str, List[TrainingExample]], float]] = None


class PromptEvaluator(ABC):
    """Base class for prompt evaluators."""

    @abstractmethod
    async def evaluate(
        self,
        prompt: str,
        examples: List[TrainingExample],
    ) -> float:
        """
        Evaluate a prompt's quality.

        Args:
            prompt: The prompt to evaluate
            examples: Training examples

        Returns:
            Quality score (0-1)
        """
        pass


class AccuracyEvaluator(PromptEvaluator):
    """
    Evaluates prompt quality based on output accuracy.

    Compares actual outputs with expected outputs and calculates accuracy.
    """

    def __init__(self, skill: BaseSkill):
        self.skill = skill

    async def evaluate(
        self,
        prompt: str,
        examples: List[TrainingExample],
    ) -> float:
        """
        Evaluate using accuracy metrics.

        Args:
            prompt: Prompt to evaluate
            examples: Training examples

        Returns:
            Accuracy score (0-1)
        """
        if not examples:
            return 0.0

        # Temporarily update the skill's prompt
        original_prompt = self.skill.config.signature_class.prompt_template
        self.skill.config.signature_class.prompt_template = prompt

        try:
            correct = 0
            total = 0

            for example in examples:
                try:
                    result = await self.skill.execute(**example.inputs)

                    if result.success and result.data:
                        # Compare key fields
                        actual = result.data
                        expected = example.expected_output

                        # Simple accuracy check: do key fields match?
                        match = self._compare_outputs(actual, expected)
                        if match:
                            correct += 1
                        total += 1

                except Exception as e:
                    logger.warning(f"Evaluation failed: {e}")
                    total += 1

            accuracy = correct / total if total > 0 else 0.0
            return accuracy

        finally:
            # Restore original prompt
            self.skill.config.signature_class.prompt_template = original_prompt

    def _compare_outputs(self, actual: Dict, expected: Dict) -> bool:
        """Compare actual and expected outputs."""
        # Compare top-level keys
        for key in expected:
            if key not in actual:
                return False

            # Simple value comparison
            if isinstance(expected[key], (int, float, str, bool)):
                if actual[key] != expected[key]:
                    # Allow some tolerance for numeric values
                    if isinstance(expected[key], (int, float)):
                        try:
                            if abs(float(actual[key]) - float(expected[key])) > 0.1:
                                return False
                        except:
                            return False
                    else:
                        return False

        return True


class FeedbackEvaluator(PromptEvaluator):
    """
    Evaluates prompt quality based on user feedback.

    Uses user ratings/scores to calculate average satisfaction.
    """

    async def evaluate(
        self,
        prompt: str,
        examples: List[TrainingExample],
    ) -> float:
        """
        Evaluate using user feedback scores.

        Args:
            prompt: Prompt to evaluate
            examples: Training examples with feedback

        Returns:
            Average feedback score (0-1)
        """
        feedback_scores = [
            ex.user_feedback for ex in examples
            if ex.user_feedback is not None
        ]

        if not feedback_scores:
            return 0.0

        # Normalize to 0-1 range (assuming feedback is 1-5)
        return sum(score / 5.0 for score in feedback_scores) / len(feedback_scores)


class SkillOptimizer:
    """
    Optimizes skill prompts using iterative improvement.

    Features:
    - Evaluates current prompt quality
    - Generates prompt variations
    - Tests variations against training data
    - Selects best performing prompt
    - Updates database with optimized prompt
    """

    def __init__(self, skill_name: str):
        """
        Initialize the optimizer.

        Args:
            skill_name: Name of the skill to optimize
        """
        self.skill_name = skill_name
        self.optimization_history: List[OptimizationResult] = []

    async def optimize(
        self,
        config: OptimizationConfig,
        evaluator: Optional[PromptEvaluator] = None,
    ) -> OptimizationResult:
        """
        Run the optimization process.

        Args:
            config: Optimization configuration
            evaluator: Optional custom evaluator

        Returns:
            Best optimization result
        """
        logger.info(f"Starting optimization for skill: {self.skill_name}")

        # Get current prompt
        current_prompt = await self._get_current_prompt()
        if not current_prompt:
            raise ValueError(f"No prompt found for skill: {self.skill_name}")

        # Create evaluator if not provided
        if evaluator is None:
            skill = await self._create_skill_instance()
            evaluator = AccuracyEvaluator(skill)

        # Evaluate current prompt
        current_score = await evaluator.evaluate(current_prompt.content, config.examples)
        logger.info(f"Current prompt score: {current_score:.3f}")

        best_result = OptimizationResult(
            iteration=0,
            prompt=current_prompt.content,
            score=current_score,
            metrics={"evaluated": True},
        )

        # Check if already meets target
        if current_score >= config.target_score:
            logger.info(f"Current prompt already meets target score: {config.target_score}")
            return best_result

        # Optimization loop
        for iteration in range(1, config.max_iterations + 1):
            # Generate prompt variations
            variations = self._generate_prompt_variations(
                best_result.prompt,
                num_variations=3,
            )

            # Evaluate each variation
            for variation in variations:
                score = await evaluator.evaluate(variation, config.examples)

                logger.info(f"Iteration {iteration}: variation score = {score:.3f}")

                if score > best_result.score + config.improvement_threshold:
                    logger.info(f"New best prompt found: {score:.3f}")

                    best_result = OptimizationResult(
                        iteration=iteration,
                        prompt=variation,
                        score=score,
                        metrics={"improved": True},
                    )

                    # Check if target reached
                    if score >= config.target_score:
                        logger.info(f"Target score {config.target_score} reached!")
                        break

            # Add to history
            self.optimization_history.append(best_result)

        # Save optimized prompt if improvement was made
        if best_result.iteration > 0:
            await self._save_optimized_prompt(best_result)

        return best_result

    async def _get_current_prompt(self) -> Optional[Any]:
        """Get the current prompt template from database."""
        # Try to get user prompt from database
        templates = await SkillPromptTemplateService.load_prompt_templates(
            self.skill_name
        )

        if "user" in templates:
            return templates["user"]

        # Fall back to signature class prompt
        from src.infrastructure.dspy.skill_registry import SkillRegistry

        try:
            skill_info = SkillRegistry.get_skill_info(self.skill_name)
            if skill_info and skill_info.signature_class:
                # Return a mock object with content attribute
                class MockPrompt:
                    def __init__(self, content):
                        self.content = content
                return MockPrompt(
                    skill_info.signature_class.get_prompt_template()
                )
        except Exception as e:
            logger.warning(f"Could not get signature prompt: {e}")

        return None

    async def _create_skill_instance(self) -> BaseSkill:
        """Create a skill instance for evaluation."""
        from src.infrastructure.dspy.skill_registry import SkillRegistry

        skill_info = SkillRegistry.get_skill_info(self.skill_name)
        if not skill_info:
            raise ValueError(f"Skill not found: {self.skill_name}")

        return skill_info.skill_class()

    def _generate_prompt_variations(
        self,
        base_prompt: str,
        num_variations: int = 3,
    ) -> List[str]:
        """
        Generate prompt variations for testing.

        Args:
            base_prompt: Original prompt
            num_variations: Number of variations to generate

        Returns:
            List of prompt variations
        """
        variations = []

        # Strategy 1: Add more specific instructions
        if "请" in base_prompt and "评估" in base_prompt:
            variation = base_prompt.replace(
                "请",
                "请仔细、详细地",
                1
            )
            variations.append(variation)

        # Strategy 2: Add output format requirements
        if "json" not in base_prompt.lower():
            format_instruction = "\n\n请严格按照JSON格式输出结果，包含所有必需字段。"
            variations.append(base_prompt + format_instruction)

        # Strategy 3: Add context about medical guidelines
        guidelines_hint = "\n\n请参考最新的临床实践指南进行评估。"
        variations.append(base_prompt + guidelines_hint)

        # Strategy 4: Emphasize precision
        if "准确" not in base_prompt:
            precision_instruction = "\n\n请注意提供准确、精确的评估结果，避免模糊表述。"
            variations.append(base_prompt + precision_instruction)

        # Strategy 5: Add step-by-step instruction
        if "步骤" not in base_prompt:
            step_instruction = "\n\n请按以下步骤评估：1)分析数据，2)判断等级，3)评估风险，4)给出建议。"
            variations.append(base_prompt + step_instruction)

        # Return requested number of variations
        return variations[:num_variations]

    async def _save_optimized_prompt(self, result: OptimizationResult) -> None:
        """
        Save the optimized prompt to database.

        Args:
            result: Optimization result to save
        """
        # Save as a new version
        await SkillPromptTemplateService.update_prompt_template(
            skill_id=self.skill_name,
            prompt_type="user",
            content=result.prompt,
            version=f"optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

        logger.info(f"Saved optimized prompt for {self.skill_name}")

    async def collect_training_data(
        self,
        limit: int = 100,
    ) -> List[TrainingExample]:
        """
        Collect training data from skill execution history.

        Args:
            limit: Maximum examples to collect

        Returns:
            List of training examples
        """
        # TODO: Implement collection from consultation history
        # For now, return empty list
        logger.warning("Training data collection not yet implemented")
        return []

    def get_optimization_history(self) -> List[OptimizationResult]:
        """Get the optimization history."""
        return self.optimization_history

    def save_optimization_report(self, filepath: str) -> None:
        """
        Save optimization report to file.

        Args:
            filepath: Path to save report
        """
        report = {
            "skill_name": self.skill_name,
            "optimization_history": [
                {
                    "iteration": r.iteration,
                    "score": r.score,
                    "timestamp": r.timestamp.isoformat(),
                    "metrics": r.metrics,
                }
                for r in self.optimization_history
            ],
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Optimization report saved to {filepath}")


class PromptOptimizationService:
    """
    Service for managing prompt optimization across all skills.

    Provides:
    - Batch optimization of multiple skills
    - Scheduling of optimization jobs
    - Monitoring of optimization progress
    - Reporting and analytics
    """

    @classmethod
    async def optimize_skill(
        cls,
        skill_name: str,
        config: Optional[OptimizationConfig] = None,
    ) -> OptimizationResult:
        """
        Optimize prompts for a specific skill.

        Args:
            skill_name: Name of the skill to optimize
            config: Optimization configuration

        Returns:
            Optimization result
        """
        optimizer = SkillOptimizer(skill_name)

        if config is None:
            # Use default config
            config = OptimizationConfig(
                max_iterations=5,
                target_score=0.80,
            )

        return await optimizer.optimize(config)

    @classmethod
    async def optimize_all_skills(
        cls,
        skill_names: Optional[List[str]] = None,
        config: Optional[OptimizationConfig] = None,
    ) -> Dict[str, OptimizationResult]:
        """
        Optimize prompts for multiple skills.

        Args:
            skill_names: List of skills to optimize (all if None)
            config: Optimization configuration

        Returns:
            Dict mapping skill name to optimization result
        """
        # Get all skills if not specified
        if skill_names is None:
            from src.infrastructure.dspy.skill_registry import SkillRegistry
            skill_names = SkillRegistry.list_skill_names()

        results = {}

        for skill_name in skill_names:
            try:
                logger.info(f"Optimizing skill: {skill_name}")
                result = await cls.optimize_skill(skill_name, config)
                results[skill_name] = result
            except Exception as e:
                logger.error(f"Failed to optimize {skill_name}: {e}")
                results[skill_name] = None

        return results

    @classmethod
    async def get_optimization_status(
        cls,
        skill_name: str,
    ) -> Dict[str, Any]:
        """
        Get optimization status for a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            Status information
        """
        optimizer = SkillOptimizer(skill_name)

        return {
            "skill_name": skill_name,
            "optimization_history_count": len(optimizer.get_optimization_history()),
            "last_optimization": (
                optimizer.optimization_history[-1].timestamp.isoformat()
                if optimizer.optimization_history
                else None
            ),
            "best_score": (
                max(r.score for r in optimizer.optimization_history)
                if optimizer.optimization_history
                else None
            ),
        }
