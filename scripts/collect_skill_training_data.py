#!/usr/bin/env python3
"""
Collect training data for skill prompt optimization.

This script collects training examples from consultation history
and skill execution logs for use in prompt optimization.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select

from src.config.settings import get_settings
from src.infrastructure.database import get_db_session_context
from src.application.services.skill_optimizer_service import TrainingExample


async def collect_from_consultations(
    skill_name: str,
    limit: int = 50,
) -> List[TrainingExample]:
    """
    Collect training examples from consultation history.

    Args:
        skill_name: Name of the skill to collect data for
        limit: Maximum examples to collect

    Returns:
        List of training examples
    """
    examples = []

    # TODO: Query consultation history and skill usage
    # This is a placeholder implementation

    # Example hypertension training data
    if skill_name == "hypertension_assessment":
        example_data = [
            {
                "inputs": {
                    "blood_pressure": {
                        "systolic": 135,
                        "diastolic": 88,
                    },
                    "patient_data": {
                        "age": 45,
                        "gender": "male",
                    },
                },
                "expected_output": {
                    "hypertension_assessment": {
                        "level": "normal_high",
                        "systolic_level": "elevated",
                        "diastolic_level": "normal",
                        "risk_category": "low",
                    }
                },
                "metadata": {"source": "synthetic"},
            },
            {
                "inputs": {
                    "blood_pressure": {
                        "systolic": 155,
                        "diastolic": 95,
                    },
                    "patient_data": {
                        "age": 55,
                        "gender": "male",
                    },
                },
                "expected_output": {
                    "hypertension_assessment": {
                        "level": "grade_1",
                        "systolic_level": "grade_1",
                        "diastolic_level": "grade_1",
                        "risk_category": "moderate",
                    }
                },
                "metadata": {"source": "synthetic"},
            },
            {
                "inputs": {
                    "blood_pressure": {
                        "systolic": 175,
                        "diastolic": 105,
                    },
                    "patient_data": {
                        "age": 62,
                        "gender": "female",
                    },
                },
                "expected_output": {
                    "hypertension_assessment": {
                        "level": "grade_2",
                        "systolic_level": "grade_2",
                        "diastolic_level": "grade_2",
                        "risk_category": "high",
                    }
                },
                "metadata": {"source": "synthetic"},
            },
        ]

        for data in example_data:
            examples.append(TrainingExample(**data))

    return examples[:limit]


async def collect_from_skill_logs(
    skill_name: str,
    limit: int = 50,
) -> List[TrainingExample]:
    """
    Collect training examples from skill execution logs.

    Args:
        skill_name: Name of the skill
        limit: Maximum examples

    Returns:
        List of training examples
    """
    # TODO: Implement log parsing
    return []


async def save_training_data(
    skill_name: str,
    examples: List[TrainingExample],
    output_dir: str = "data/training",
) -> None:
    """
    Save training examples to file.

    Args:
        skill_name: Name of the skill
        examples: Training examples to save
        output_dir: Output directory
    """
    output_path = Path(output_dir) / f"{skill_name}_training_data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [
        {
            "inputs": ex.inputs,
            "expected_output": ex.expected_output,
            "actual_output": ex.actual_output,
            "user_feedback": ex.user_feedback,
            "metadata": ex.metadata,
        }
        for ex in examples
    ]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(examples)} examples to {output_path}")


async def load_training_data(
    skill_name: str,
    input_dir: str = "data/training",
) -> List[TrainingExample]:
    """
    Load training examples from file.

    Args:
        skill_name: Name of the skill
        input_dir: Input directory

    Returns:
        List of training examples
    """
    input_path = Path(input_dir) / f"{skill_name}_training_data.json"

    if not input_path.exists():
        print(f"No training data found for {skill_name}")
        return []

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    examples = []
    for item in data:
        examples.append(TrainingExample(
            inputs=item["inputs"],
            expected_output=item["expected_output"],
            actual_output=item.get("actual_output"),
            user_feedback=item.get("user_feedback"),
            metadata=item.get("metadata", {}),
        ))

    print(f"Loaded {len(examples)} examples from {input_path}")
    return examples


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect skill training data")
    parser.add_argument("--skill", required=True, help="Skill name to collect data for")
    parser.add_argument("--output", default="data/training", help="Output directory")
    parser.add_argument("--limit", type=int, default=50, help="Maximum examples to collect")

    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"Training Data Collection for {args.skill}")
    print(f"{'='*60}")

    # Collect examples
    examples = await collect_from_consultations(args.skill, args.limit)

    # Save to file
    await save_training_data(args.skill, examples, args.output)

    print(f"{'='*60}")
    print(f"Collected {len(examples)} training examples")
    print(f"Output: {args.output}/{args.skill}_training_data.json")


if __name__ == "__main__":
    asyncio.run(main())
