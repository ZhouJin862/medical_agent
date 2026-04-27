#!/usr/bin/env python3
"""
Insert skill prompt templates for common health assessment skills.

This script inserts default prompt templates for the four-highs skills:
- Hypertension assessment
- Diabetes assessment
- Dyslipidemia assessment
- Hyperuricemia assessment
- Obesity assessment
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func

from src.config.settings import get_settings
from src.infrastructure.database import get_db_session_context
from src.infrastructure.persistence.models.skill_models import SkillPromptModel, SkillModel
from src.application.services.skill_prompt_template_service import SkillPromptTemplateService


# Default prompt templates for health assessment skills
PROMPT_TEMPLATES = [
    # ========== 高血压评估 ==========
    {
        "skill_name": "hypertension_assessment",
        "prompts": [
            {
                "prompt_type": "system",
                "content": """你是一位专业的高血压健康管理助手。你的职责是：

1. 根据用户提供的血压数据和健康信息，评估血压状况
2. 判断血压水平（正常、正常高值、高血压1级、2级、3级）
3. 识别心血管危险因素
4. 提供科学的生活建议和就医指导

参考标准：
- 收缩压<120且舒张压<80 mmHg：正常血压
- 收缩压120-139和/或舒张压80-89 mmHg：正常高值
- 收缩压140-159和/或舒张压90-99 mmHg：高血压1级
- 收缩压160-179和/或舒张压100-109 mmHg：高血压2级
- 收缩压≥180和/或舒张压≥110 mmHg：高血压3级

请以专业、易懂的方式提供评估结果和建议。""",
                "version": "1.0.0",
            },
            {
                "prompt_type": "user",
                "content": """请评估以下血压数据：

患者信息：
- 姓名：{patient_name}
- 年龄：{age}岁
- 收缩压：{systolic_pressure} mmHg
- 舒张压：{diastolic_pressure} mmHg
- 测量时间：{measurement_time}
- 既往病史：{medical_history}
- 当前症状：{symptoms}

请提供：
1. 血压水平判断
2. 心血管风险评估
3. 生活建议
4. 是否需要就医及就医建议""",
                "version": "1.0.0",
            },
        ],
    },
    # ========== 糖尿病评估 ==========
    {
        "skill_name": "diabetes_assessment",
        "prompts": [
            {
                "prompt_type": "system",
                "content": """你是一位专业的糖尿病健康管理助手。你的职责是：

1. 根据用户提供的血糖数据评估糖尿病风险
2. 判断血糖水平（正常、糖耐量受损、糖尿病）
3. 考虑用户的危险因素和症状
4. 提供科学的饮食、运动和就医指导

参考标准：
- 空腹血糖：正常<6.1，受损6.1-7.0，糖尿病≥7.0 mmol/L
- 餐后2h血糖：正常<7.8，受损7.8-11.1，糖尿病≥11.1 mmol/L
- 糖化血红蛋白：正常<6.0，受损6.0-6.5，糖尿病≥6.5 %

请以专业、关怀的方式提供评估结果和建议。""",
                "version": "1.0.0",
            },
            {
                "prompt_type": "user",
                "content": """请评估以下血糖数据：

患者信息：
- 姓名：{patient_name}
- 年龄：{age}岁
- 空腹血糖：{fasting_glucose} mmol/L
- 餐后2h血糖：{postprandial_glucose} mmol/L
- 糖化血红蛋白：{hba1c} %
- 体重指数：{bmi} kg/m²
- 家族史：{family_history}
- 当前症状：{symptoms}

请提供：
1. 血糖水平判断
2. 糖尿病风险评估
3. 饮食和运动建议
4. 是否需要进一步检查及就医建议""",
                "version": "1.0.0",
            },
        ],
    },
    # ========== 血脂异常评估 ==========
    {
        "skill_name": "dyslipidemia_assessment",
        "prompts": [
            {
                "prompt_type": "system",
                "content": """你是一位专业的血脂健康管理助手。你的职责是：

1. 根据用户提供的血脂数据评估血脂异常风险
2. 判断各血脂指标的水平
3. 评估心血管疾病风险
4. 提供科学的饮食和用药指导

参考标准：
- 总胆固醇(TC)：合适<5.2，边缘升高5.2-6.2，升高≥6.2 mmol/L
- 甘油三酯(TG)：合适<1.7，边缘升高1.7-2.3，升高≥2.3 mmol/L
- LDL-C：合适<3.4，边缘升高3.4-4.1，升高≥4.1 mmol/L
- HDL-C：合适≥1.0，降低<1.0 mmol/L

请以专业、科学的方式提供评估结果和建议。""",
                "version": "1.0.0",
            },
            {
                "prompt_type": "user",
                "content": """请评估以下血脂数据：

患者信息：
- 姓名：{patient_name}
- 年龄：{age}岁
- 总胆固醇：{total_cholesterol} mmol/L
- 甘油三酯：{triglycerides} mmol/L
- LDL-C：{ldl_c} mmol/L
- HDL-C：{hdl_c} mmol/L
- 既往病史：{medical_history}
- 用药情况：{medications}

请提供：
1. 各血脂指标水平判断
2. 心血管疾病风险评估
3. 饮食调整建议
4. 是否需要药物治疗建议""",
                "version": "1.0.0",
            },
        ],
    },
    # ========== 高尿酸血症评估 ==========
    {
        "skill_name": "hyperuricemia_assessment",
        "prompts": [
            {
                "prompt_type": "system",
                "content": """你是一位专业的高尿酸血症健康管理助手。你的职责是：

1. 根据用户提供的血尿酸数据评估高尿酸血症风险
2. 判断尿酸水平
3. 识别痛风的危险因素
4. 提供科学的饮食和生活指导

参考标准：
- 正常血尿酸：<420 μmol/L (男性)，<360 μmol/L (女性更年期前)
- 高尿酸血症：≥420 μmol/L (男性)，≥360 μmol/L (女性更年期前)
- 痛风风险：尿酸>480 μmol/L

请以专业、关怀的方式提供评估结果和建议。""",
                "version": "1.0.0",
            },
            {
                "prompt_type": "user",
                "content": """请评估以下血尿酸数据：

患者信息：
- 姓名：{patient_name}
- 性别：{gender}
- 年龄：{age}岁
- 血尿酸：{uric_acid} μmol/L
- 体重指数：{bmi} kg/m²
- 痛风发作史：{gout_history}
- 当前症状：{symptoms}
- 饮食习惯：{diet_habits}

请提供：
1. 血尿酸水平判断
2. 痛风风险评估
3. 饮食控制建议（低嘌呤饮食）
4. 是否需要药物治疗建议""",
                "version": "1.0.0",
            },
        ],
    },
    # ========== 肥胖评估 ==========
    {
        "skill_name": "obesity_assessment",
        "prompts": [
            {
                "prompt_type": "system",
                "content": """你是一位专业的肥胖健康管理助手。你的职责是：

1. 根据用户提供的体型数据评估肥胖程度
2. 判断BMI和腰围水平
3. 评估肥胖相关疾病风险
4. 提供科学的减重和健康管理指导

参考标准：
- BMI：正常18.5-24，超重24-28，肥胖≥28 kg/m²
- 男性腰围：正常<90，中心性肥胖≥90 cm
- 女性腰围：正常<85，中心性肥胖≥85 cm
- 腰臀比：男性<0.90，女性<0.85

请以专业、鼓励的方式提供评估结果和建议。""",
                "version": "1.0.0",
            },
            {
                "prompt_type": "user",
                "content": """请评估以下体型数据：

患者信息：
- 姓名：{patient_name}
- 性别：{gender}
- 年龄：{age}岁
- 身高：{height} cm
- 体重：{weight} kg
- 腰围：{waist_circumference} cm
- 臀围：{hip_circumference} cm
- 既往病史：{medical_history}
- 运动习惯：{exercise_habits}
- 饮食习惯：{diet_habits}

请提供：
1. BMI和腰臀比水平判断
2. 肥胖相关疾病风险评估
3. 减重目标和建议
4. 饮食和运动处方建议""",
                "version": "1.0.0",
            },
        ],
    },
]


async def get_skill_id_by_name(session, skill_name: str) -> str | None:
    """Get skill ID by name."""
    result = await session.execute(
        select(SkillModel.id).where(SkillModel.name == skill_name)
    )
    return result.scalar_one_or_none()


async def insert_prompt_templates(
    skill_id: str,
    prompts: list[dict],
    force: bool = False,
) -> dict:
    """Insert prompt templates for a skill."""
    inserted = []
    skipped = []
    updated = []

    for prompt_def in prompts:
        prompt_type = prompt_def["prompt_type"]
        content = prompt_def["content"]
        version = prompt_def["version"]

        # Check if exists
        existing = await SkillPromptTemplateService.load_prompt_templates(skill_id)

        if prompt_type in existing:
            if force:
                await SkillPromptTemplateService.update_prompt_template(
                    skill_id=skill_id,
                    prompt_type=prompt_type,
                    content=content,
                    version=version,
                )
                updated.append(prompt_type)
            else:
                skipped.append(prompt_type)
        else:
            await SkillPromptTemplateService.create_prompt_template(
                skill_id=skill_id,
                prompt_type=prompt_type,
                content=content,
                version=version,
            )
            inserted.append(prompt_type)

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Insert skill prompt templates")
    parser.add_argument("--dry-run", action="store_true", help="Validate without inserting")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing prompts")
    parser.add_argument("--skills", nargs="+", help="Specific skills to process (all if not specified)")

    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"Skill Prompt Templates Insertion")
    print(f"{'='*60}")
    print(f"Total skills: {len(PROMPT_TEMPLATES)}")
    print(f"Force: {args.force}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("Validation passed. Templates look good:")
        for skill_data in PROMPT_TEMPLATES:
            print(f"  - {skill_data['skill_name']}: {len(skill_data['prompts'])} prompts")
        print(f"\nReady to insert.")
        return

    # Filter skills if specified
    skills_to_process = PROMPT_TEMPLATES
    if args.skills:
        skills_to_process = [s for s in PROMPT_TEMPLATES if s["skill_name"] in args.skills]

    # Get skill IDs
    async with get_db_session_context() as session:
        skill_ids = {}
        for skill_data in skills_to_process:
            skill_id = await get_skill_id_by_name(session, skill_data["skill_name"])
            if skill_id:
                skill_ids[skill_data["skill_name"]] = skill_id
            else:
                print(f"Warning: Skill '{skill_data['skill_name']}' not found in database")

    # Insert prompts
    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    for skill_data in skills_to_process:
        skill_name = skill_data["skill_name"]
        skill_id = skill_ids.get(skill_name)

        if not skill_id:
            print(f"Skipped {skill_name}: Skill not found")
            continue

        result = await insert_prompt_templates(skill_id, skill_data["prompts"], args.force)

        print(f"{skill_name}:")
        print(f"  Inserted: {len(result['inserted'])}")
        print(f"  Updated: {len(result['updated'])}")
        print(f"  Skipped: {len(result['skipped'])}")

        total_inserted += len(result['inserted'])
        total_updated += len(result['updated'])
        total_skipped += len(result['skipped'])

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total Inserted: {total_inserted}")
    print(f"  Total Updated: {total_updated}")
    print(f"  Total Skipped: {total_skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
