"""
Test script for Composite Skills functionality.

Tests:
1. Creating composite skills
2. Loading composite skill configuration
3. Executing composite skills
4. Skill aggregation
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database import init_database, get_db_session
from src.domain.shared.services.composite_skill_executor import (
    CompositeSkillExecutor,
    CompositeSkillConfig,
)
from src.domain.shared.services.unified_skills_repository import (
    UnifiedSkillsRepository,
)
from src.infrastructure.persistence.models.skill_models import (
    SkillModel,
    SkillType,
)
from sqlalchemy import select
import uuid


async def setup_test_composite_skill():
    """Create a test composite skill in the database."""
    async for session in get_db_session():
        try:
            # Check if test skill already exists
            existing_stmt = select(SkillModel).where(
                SkillModel.name == "test_composite_skill"
            )
            existing_result = await session.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                print("[OK] Test composite skill already exists")
                return existing.id

            # Create composite skill
            skill = SkillModel(
                id=str(uuid.uuid4()),
                name="test_composite_skill",
                display_name="测试组合技能",
                description="用于测试的组合技能，组合高血压和糖尿病评估",
                type=SkillType.GENERIC,
                enabled=True,
                version="1.0.0",
                config={
                    "base_skills": [
                        "hypertension-assessment",
                        "diabetes_assessment",
                    ],
                    "override_settings": {
                        "response_style": "standard",
                        "include_recommendations": True,
                    },
                    "business_rules": {},
                    "workflow_config": {},
                    "display_name": "测试组合技能",
                    "response_style": "standard",
                    "execution_mode": "sequential",
                },
            )

            session.add(skill)
            await session.commit()
            await session.refresh(skill)

            print(f"[OK] Created test composite skill: {skill.id}")
            return skill.id

        except Exception as e:
            print(f"[FAIL] Failed to create test skill: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return None


async def test_load_composite_config():
    """Test loading composite skill configuration."""
    print("\n" + "="*60)
    print("Test 1: Load Composite Configuration")
    print("="*60)

    async for session in get_db_session():
        try:
            repository = UnifiedSkillsRepository(session)
            executor = CompositeSkillExecutor(repository)

            # Load composite config
            config = await executor.load_composite_config_from_database(
                "test_composite_skill"
            )

            if config:
                print(f"[OK] Loaded composite config")
                print(f"  - Base skills: {config.base_skills}")
                print(f"  - Response style: {config.response_style}")
                print(f"  - Execution mode: {config.execution_mode}")
                print(f"  - Override settings: {config.override_settings}")
                return True
            else:
                print("[FAIL] Failed to load composite config")
                return False

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_composite_execution():
    """Test executing a composite skill."""
    print("\n" + "="*60)
    print("Test 2: Execute Composite Skill")
    print("="*60)

    async for session in get_db_session():
        try:
            repository = UnifiedSkillsRepository(session)
            executor = CompositeSkillExecutor(repository)

            # Load composite config
            config = await executor.load_composite_config_from_database(
                "test_composite_skill"
            )

            if not config:
                print("[FAIL] Failed to load composite config")
                return False

            # Execute composite skill
            print("\nExecuting composite skill...")
            result = await executor.execute_composite_skill(
                config=config,
                user_input="我血压150/95，空腹血糖7.5，请帮我评估一下",
                patient_context={
                    "basic_info": {"age": 45, "gender": "male"},
                    "vital_signs": {
                        "blood_pressure_systolic": 150,
                        "blood_pressure_diastolic": 95,
                        "fasting_glucose": 7.5,
                    },
                },
                conversation_context=None,
            )

            if result.success:
                print(f"[OK] Composite skill executed successfully")
                print(f"  - Execution time: {result.execution_time_ms}ms")
                print(f"  - Base skills used: {result.metadata.get('loaded_skills', [])}")
                print(f"  - Number of results: {len(result.skill_results)}")
                print(f"\n  Response preview (first 200 chars):")
                print(f"  {result.response[:200]}...")
                return True
            else:
                print(f"[FAIL] Execution failed: {result.error}")
                return False

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_parallel_execution():
    """Test parallel execution mode."""
    print("\n" + "="*60)
    print("Test 3: Parallel Execution Mode")
    print("="*60)

    async for session in get_db_session():
        try:
            repository = UnifiedSkillsRepository(session)
            executor = CompositeSkillExecutor(repository)

            # Create parallel config
            config = CompositeSkillConfig(
                base_skills=["hypertension-assessment", "diabetes_assessment"],
                execution_mode="parallel",
                response_style="standard",
            )

            print("\nExecuting in parallel mode...")
            result = await executor.execute_composite_skill(
                config=config,
                user_input="帮我评估血压和血糖",
                patient_context={
                    "basic_info": {"age": 50, "gender": "female"},
                    "vital_signs": {
                        "blood_pressure_systolic": 140,
                        "blood_pressure_diastolic": 90,
                        "fasting_glucose": 6.8,
                    },
                },
                conversation_context=None,
            )

            if result.success:
                print(f"[OK] Parallel execution succeeded")
                print(f"  - Execution time: {result.execution_time_ms}ms")
                print(f"  - Results: {len(result.skill_results)} skills")
                return True
            else:
                print(f"[FAIL] Parallel execution failed: {result.error}")
                return False

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_vip_response_style():
    """Test VIP detailed response style."""
    print("\n" + "="*60)
    print("Test 4: VIP Detailed Response Style")
    print("="*60)

    async for session in get_db_session():
        try:
            repository = UnifiedSkillsRepository(session)
            executor = CompositeSkillExecutor(repository)

            # Create VIP config
            config = CompositeSkillConfig(
                base_skills=["hypertension-assessment", "diabetes_assessment"],
                execution_mode="sequential",
                response_style="vip_detailed",
                override_settings={
                    "include_recommendations": True,
                    "add_personal_notes": True,
                },
            )

            print("\nExecuting with VIP style...")
            result = await executor.execute_composite_skill(
                config=config,
                user_input="我是VIP用户，请帮我做综合评估",
                patient_context={
                    "basic_info": {"age": 55, "gender": "male"},
                    "vital_signs": {
                        "blood_pressure_systolic": 145,
                        "blood_pressure_diastolic": 92,
                        "fasting_glucose": 7.2,
                    },
                },
                conversation_context=None,
            )

            if result.success:
                print(f"[OK] VIP style execution succeeded")
                print(f"\n  Response preview (first 300 chars):")
                print(f"  {result.response[:300]}...")

                # Check for VIP formatting
                if "## Personalized Health Assessment" in result.response or \
                   "### Executive Summary" in result.response:
                    print(f"[OK] VIP formatting detected")
                else:
                    print(f"[WARN] VIP formatting may not be applied correctly")

                return True
            else:
                print(f"[FAIL] VIP execution failed: {result.error}")
                return False

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Composite Skills Test Suite")
    print("="*60)

    try:
        # Initialize database
        await init_database()
        print("[OK] Database initialized")

        # Setup test composite skill
        skill_id = await setup_test_composite_skill()
        if not skill_id:
            print("\n[FAIL] Failed to setup test skill. Exiting.")
            return

        # Run tests
        results = []

        results.append(("Load Config", await test_load_composite_config()))
        results.append(("Execute Composite", await test_composite_execution()))
        results.append(("Parallel Execution", await test_parallel_execution()))
        results.append(("VIP Response Style", await test_vip_response_style()))

        # Summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            status = "[OK]" if result else "[FAIL]"
            print(f"{status} {name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n[OK] All tests passed!")
        else:
            print(f"\n[WARN] {total - passed} test(s) failed")

    except Exception as e:
        print(f"\n[FAIL] Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
