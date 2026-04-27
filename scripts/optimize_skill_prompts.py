#!/usr/bin/env python3
"""
Execute skill prompt optimization.

This script runs the SkillOptimizer to improve skill prompt templates.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.application.services.skill_optimizer_service import (
    SkillOptimizer,
    OptimizationConfig,
    TrainingExample,
    AccuracyEvaluator,
)
from src.infrastructure.dspy.base_skill import BaseSkill


async def optimize_hypertension_skill():
    """Optimize hypertension assessment skill prompts."""
    print("Optimizing hypertension assessment skill...")

    # Create training examples
    examples = [
        TrainingExample(
            inputs={
                "blood_pressure": {"systolic": 135, "diastolic": 88},
                "patient_data": {"age": 45, "gender": "male"},
            },
            expected_output={
                "hypertension_assessment": {
                    "level": "normal_high",
                    "risk_category": "low",
                }
            },
        ),
        TrainingExample(
            inputs={
                "blood_pressure": {"systolic": 155, "diastolic": 95},
                "patient_data": {"age": 55, "gender": "male"},
            },
            expected_output={
                "hypertension_assessment": {
                    "level": "grade_1",
                    "risk_category": "moderate",
                }
            },
        ),
        TrainingExample(
            inputs={
                "blood_pressure": {"systolic": 175, "diastolic": 105},
                "patient_data": {"age": 62, "gender": "female"},
            },
            expected_output={
                "hypertension_assessment": {
                    "level": "grade_2",
                    "risk_category": "high",
                }
            },
        ),
    ]

    # Create optimizer
    optimizer = SkillOptimizer("hypertension_assessment")

    # Create config
    config = OptimizationConfig(
        max_iterations=5,
        target_score=0.75,
        improvement_threshold=0.05,
        examples=examples,
    )

    # Note: Actual optimization requires running the skill
    # This is a simplified version that demonstrates the concept
    print(f"Optimization config created for hypertension_assessment")
    print(f"Training examples: {len(examples)}")
    print(f"Max iterations: {config.max_iterations}")
    print(f"Target score: {config.target_score}")

    # For demo purposes, just show the structure
    print("\nNote: Full optimization requires:")
    print("1. Skill instance creation")
    print("2. Prompt variation generation")
    print("3. Iterative evaluation")
    print("4. Best prompt selection")

    return True


async def optimize_diabetes_skill():
    """Optimize diabetes assessment skill prompts."""
    print("Optimizing diabetes assessment skill...")

    examples = [
        TrainingExample(
            inputs={
                "blood_glucose": {
                    "fasting": 6.5,
                    "postprandial": 8.2,
                    "hba1c": 6.8,
                },
                "patient_data": {"age": 50, "gender": "male"},
            },
            expected_output={
                "diabetes_assessment": {
                    "status": "diabetes",
                    "control": "poor",
                }
            },
        ),
        TrainingExample(
            inputs={
                "blood_glucose": {
                    "fasting": 5.8,
                    "postprandial": 7.5,
                    "hba1c": 6.2,
                },
                "patient_data": {"age": 40, "gender": "female"},
            },
            expected_output={
                "diabetes_assessment": {
                    "status": "prediabetes",
                    "control": "good",
                }
            },
        ),
    ]

    optimizer = SkillOptimizer("diabetes_assessment")

    config = OptimizationConfig(
        max_iterations=5,
        target_score=0.75,
        improvement_threshold=0.05,
        examples=examples,
    )

    print(f"Optimization config created for diabetes_assessment")
    print(f"Training examples: {len(examples)}")

    return True


async def optimize_risk_assessment_skill():
    """Optimize risk assessment skill prompts."""
    print("Optimizing risk assessment skill...")

    examples = [
        TrainingExample(
            inputs={
                "patient_data": {"age": 45, "gender": "male"},
                "vital_signs": {
                    "bmi": 27,
                    "blood_pressure": {"systolic": 140, "diastolic": 90},
                    "blood_glucose": 6.8,
                },
            },
            expected_output={
                "risk_predictions": {
                    "cvd_risk": "moderate",
                    "diabetes_risk": "elevated",
                }
            },
        ),
    ]

    optimizer = SkillOptimizer("health_assessment")

    config = OptimizationConfig(
        max_iterations=3,
        target_score=0.70,
        improvement_threshold=0.05,
        examples=examples,
    )

    print(f"Optimization config created for risk_assessment")
    print(f"Training examples: {len(examples)}")

    return True


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run skill prompt optimization")
    parser.add_argument(
        "--skill",
        choices=["hypertension", "diabetes", "risk", "all"],
        default="all",
        help="Skill to optimize",
    )

    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"Skill Prompt Optimization")
    print(f"{'='*60}")
    print(f"Target skill: {args.skill}")
    print(f"{'='*60}\n")

    if args.skill == "hypertension":
        await optimize_hypertension_skill()
    elif args.skill == "diabetes":
        await optimize_diabetes_skill()
    elif args.skill == "risk":
        await optimize_risk_assessment_skill()
    elif args.skill == "all":
        print("Running optimization for all skills...\n")
        await optimize_hypertension_skill()
        print()
        await optimize_diabetes_skill()
        print()
        await optimize_risk_assessment_skill()

    print(f"\n{'='*60}")
    print(f"Optimization setup complete!")
    print(f"{'='*60}")
    print(f"\nNote: This is a demonstration setup.")
    print(f"Full optimization requires:")
    print(f"1. Complete training data collection")
    print(f"2. Skill instance with LLM access")
    print(f"3. Iterative evaluation with metrics")
    print(f"4. A/B testing framework")


if __name__ == "__main__":
    asyncio.run(main())
