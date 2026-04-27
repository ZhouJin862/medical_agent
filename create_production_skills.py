"""
创建生产环境可用的技能数据
配合规则引擎一起使用
"""
import asyncio
import sys
sys.path.insert(0, 'C:/Users/jinit/work/code/medical_agent')

from sqlalchemy import select
from src.infrastructure.database import get_db_session
from src.infrastructure.persistence.models.skill_models import (
    SkillModel, SkillType, SkillCategory
)
from src.application.services.skill_management_service import SkillManagementApplicationService
from src.domain.shared.services.rule_enhanced_skill import (
    RuleEnhancedSkillRepository, RuleEnhancementConfig
)

# 定义生产环境技能列表
PRODUCTION_SKILLS = [
    {
        "name": "hypertension_assessment",
        "display_name": "高血压评估",
        "description": "评估患者血压水平，根据临床指南进行分级诊断，提供个性化健康建议",
        "skill_type": "disease_specific",
        "category": "health_assessment",
        "intent_keywords": ["高血压", "血压", "血压高", "收缩压", "舒张压", "头晕", "头痛"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["diagnosis", "risk_assessment"],
            "disease_code": "hypertension",
            "use_vital_signs": True,
            "use_risk_scoring": True,
            "risk_diseases": ["hypertension"]
        }
    },
    {
        "name": "diabetes_assessment",
        "display_name": "糖尿病评估",
        "description": "评估患者血糖水平，进行糖尿病筛查和风险评估，提供生活方式建议",
        "skill_type": "disease_specific",
        "category": "health_assessment",
        "intent_keywords": ["糖尿病", "血糖", "高血糖", "空腹血糖", "餐后血糖", "糖化血红蛋白"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["diagnosis", "risk_assessment", "reference_value"],
            "disease_code": "diabetes",
            "use_vital_signs": True,
            "use_risk_scoring": True,
            "risk_diseases": ["diabetes"]
        }
    },
    {
        "name": "dyslipidemia_assessment",
        "display_name": "血脂异常评估",
        "description": "评估患者血脂水平，识别高脂血症风险，提供饮食和运动建议",
        "skill_type": "disease_specific",
        "category": "health_assessment",
        "intent_keywords": ["血脂", "胆固醇", "甘油三酯", "高血脂", "低密度脂蛋白", "高密度脂蛋白"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["diagnosis", "risk_assessment", "reference_value"],
            "disease_code": "dyslipidemia",
            "use_vital_signs": True,
            "use_risk_scoring": True,
            "risk_diseases": ["dyslipidemia"]
        }
    },
    {
        "name": "gout_assessment",
        "display_name": "痛风评估",
        "description": "评估患者尿酸水平，识别痛风风险，提供饮食和生活方式指导",
        "skill_type": "disease_specific",
        "category": "health_assessment",
        "intent_keywords": ["痛风", "尿酸", "关节痛", "脚趾痛", "高尿酸"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["diagnosis", "risk_assessment", "reference_value"],
            "disease_code": "gout",
            "use_vital_signs": True,
            "use_risk_scoring": True,
            "risk_diseases": ["gout"]
        }
    },
    {
        "name": "health_checkup_assessment",
        "display_name": "健康体检综合评估",
        "description": "综合分析体检数据，评估四高（高血压、高血糖、高血脂、高尿酸）风险，提供整体健康建议",
        "skill_type": "generic",
        "category": "health_assessment",
        "intent_keywords": ["体检", "健康体检", "体检报告", "全面检查", "综合评估"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["diagnosis", "risk_assessment", "reference_value"],
            "use_vital_signs": True,
            "use_risk_scoring": True,
            "risk_diseases": ["hypertension", "diabetes", "dyslipidemia", "gout"]
        }
    },
    {
        "name": "obesity_assessment",
        "display_name": "肥胖评估",
        "description": "评估患者体重指数(BMI)和体脂情况，识别肥胖风险，提供减重建议",
        "skill_type": "disease_specific",
        "category": "health_assessment",
        "intent_keywords": ["肥胖", "体重", "BMI", "减肥", "超重", "体脂"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["diagnosis", "risk_assessment"],
            "disease_code": "obesity",
            "use_vital_signs": True,
            "use_risk_scoring": True,
            "risk_diseases": ["obesity", "hypertension", "diabetes"]
        }
    },
    {
        "name": "medication_reminder",
        "display_name": "用药提醒",
        "description": "提醒患者按时服药，解释药物作用和注意事项",
        "skill_type": "generic",
        "category": "medication_check",
        "intent_keywords": ["吃药", "用药", "服药", "药物", "提醒", "忘记吃药"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["prescription"],
            "use_vital_signs": False,
            "use_risk_scoring": False
        }
    },
    {
        "name": "health_consultation",
        "display_name": "健康咨询",
        "description": "回答患者健康相关问题，提供基础健康指导和建议",
        "skill_type": "generic",
        "category": "health_promotion",
        "intent_keywords": ["健康", "咨询", "建议", "指导", "怎么", "如何"],
        "rule_enhancement": {
            "enabled": True,
            "categories": ["risk_assessment"],
            "use_vital_signs": True,
            "use_risk_scoring": False
        }
    }
]

async def create_production_skills():
    """创建生产环境技能"""

    print("=" * 60)
    print("开始创建生产环境技能")
    print("=" * 60)

    async for session in get_db_session():
        try:
            skill_service = SkillManagementApplicationService(session)
            rule_repo = RuleEnhancedSkillRepository(session)

            created_count = 0
            updated_count = 0

            for skill_config in PRODUCTION_SKILLS:
                name = skill_config["name"]
                rule_config = skill_config.pop("rule_enhancement")

                # Check if skill already exists
                stmt = select(SkillModel).where(SkillModel.name == name)
                result = await session.execute(stmt)
                existing_skill = result.scalar_one_or_none()

                if existing_skill:
                    print(f"\n[更新] 技能已存在: {skill_config['display_name']} ({name})")

                    # Update rule enhancement config
                    rule_enhancement_config = RuleEnhancementConfig(**rule_config)
                    await rule_repo.update_skill_rule_config(existing_skill.id, rule_enhancement_config)
                    updated_count += 1
                else:
                    print(f"\n[创建] 新技能: {skill_config['display_name']} ({name})")

                    # Create the skill
                    skill = await skill_service.create_skill(
                        name=name,
                        display_name=skill_config["display_name"],
                        description=skill_config["description"],
                        skill_type=skill_config["skill_type"],
                        category=skill_config["category"],
                        intent_keywords=skill_config["intent_keywords"],
                    )

                    # Add rule enhancement config
                    rule_enhancement_config = RuleEnhancementConfig(**rule_config)
                    await rule_repo.update_skill_rule_config(skill["id"], rule_enhancement_config)
                    created_count += 1

                print(f"  - 规则增强: {'启用' if rule_config['enabled'] else '禁用'}")
                if rule_config.get('categories'):
                    print(f"  - 规则分类: {', '.join(rule_config['categories'])}")
                if rule_config.get('disease_code'):
                    print(f"  - 关联病种: {rule_config['disease_code']}")
                if rule_config.get('risk_diseases'):
                    print(f"  - 风险评分: {', '.join(rule_config['risk_diseases'])}")

            print("\n" + "=" * 60)
            print("技能创建完成!")
            print(f"  - 新创建: {created_count} 个")
            print(f"  - 更新: {updated_count} 个")
            print("=" * 60)

            # List all rule-enhanced skills
            print("\n[验证] 规则增强技能列表:")
            rule_enhanced_skills = await rule_repo.get_rule_enhanced_skills()
            for skill in rule_enhanced_skills:
                config = dict(skill.config).get("rule_enhancement", {}) if skill.config else {}
                print(f"  OK {skill.display_name} ({skill.name})")
                print(f"     分类: {skill.category or '通用'}")
                print(f"     关键词: {', '.join(skill.intent_keywords or [])[:5]}...")
                print(f"     规则: {config.get('categories', [])}")

        except Exception as e:
            print(f"\n[错误] 创建技能时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.commit()
        break

if __name__ == "__main__":
    asyncio.run(create_production_skills())
