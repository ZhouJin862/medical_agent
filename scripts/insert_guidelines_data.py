"""
Insert medical guidelines data for four-highs-one-heavy diseases.

This script inserts comprehensive clinical practice guidelines for:
1. 高血压 (Hypertension)
2. 糖尿病 (Diabetes)
3. 血脂异常 (Dyslipidemia)
4. 痛风 (Gout)
5. 肥胖 (Obesity)

Usage:
    python scripts/insert_guidelines_data.py [--dry-run] [--rollback]
"""
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from src.config.settings import get_settings
from src.infrastructure.database import get_db_session_context, get_engine
from src.infrastructure.persistence.models.guideline_models import (
    GuidelineModel,
    GuidelineCategory,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =====================================================
# GUIDELINE DATA DEFINITIONS
# =====================================================

@dataclass
class GuidelineData:
    """Container for guideline data."""
    disease_code: str
    disease_name: str
    display_name: str
    description: str
    category: str
    content: Dict[str, Any]
    evidence_level: str = "A"
    sources: List[str] = field(default_factory=list)
    publication_year: int = 2023
    publisher: str = "中华医学会"
    target_population: Dict[str, Any] = field(default_factory=dict)


# =====================================================
# HYPERTENSION GUIDELINES (高血压防治指南)
# =====================================================

HYPERTENSION_GUIDELINE = GuidelineData(
    disease_code="hypertension",
    disease_name="高血压",
    display_name="中国高血压防治指南2023版",
    description="高血压的诊断、治疗与管理综合指南",
    category=GuidelineCategory.COMPREHENSIVE,
    evidence_level="A",
    sources=[
        "中国高血压防治指南修订委员会",
        "中华医学会心血管病学分会",
        "中国医师协会高血压专业委员会"
    ],
    publication_year=2023,
    target_population={
        "age_range": {"min": 18, "max": 75},
        "gender": ["male", "female"],
        "special_groups": ["elderly", "pregnant", "chronic_kidney_disease"]
    },
    content={
        "prevention": {
            "primary_prevention": [
                "减少钠盐摄入，每人每日食盐摄入量逐步降至<6g",
                "增加钾摄入，每日钾摄入量≥3.5g",
                "合理膳食，多吃蔬菜水果",
                "控制体重，BMI<24kg/m²，男性腰围<90cm，女性<85cm",
                "不吸烟或戒烟，避免二手烟",
                "限制饮酒，每日酒精摄入量男性<25g，女性<15g",
                "增加运动，每周中等强度运动150分钟",
                "减轻精神压力，保持心理平衡"
            ],
            "secondary_prevention": [
                "定期监测血压，每年至少测量1次",
                "高血压前期（120-139/80-89mmHg）每3-6个月测量1次",
                "控制可改变的危险因素：血脂异常、糖尿病、肥胖",
                "低危患者每3-6个月随访1次",
                "中危患者每2-3个月随访1次",
                "高危患者每1-2个月随访1次"
            ],
            "tertiary_prevention": [
                "规范化治疗，控制血压达标",
                "定期检查靶器官损害：心脏、脑、肾脏、血管",
                "预防并发症：脑卒中、冠心病、肾衰竭",
                "建立长期随访管理机制"
            ]
        },
        "treatment": {
            "pharmacological": {
                "first_line_medications": [
                    "钙通道阻滞剂（CCB）：氨氯地平、硝苯地平",
                    "血管紧张素转换酶抑制剂（ACEI）：依那普利、培哚普利",
                    "血管紧张素Ⅱ受体拮抗剂（ARB）：缬沙坦、氯沙坦",
                    "噻嗪类利尿剂：氢氯噻嗪、吲达帕胺",
                    "β受体阻滞剂：美托洛尔、比索洛尔"
                ],
                "combination_therapy": [
                    "CCB + ACEI/ARB",
                    "CCB + 噻嗪类利尿剂",
                    "ACEI/ARB + 噻嗪类利尿剂",
                    "单片复方制剂优先推荐"
                ],
                "special_populations": {
                    "elderly": "从小剂量开始，逐步增加剂量，避免体位性低血压",
                    "diabetes": "首选ACEI或ARB，保护肾功能",
                    "chronic_kidney_disease": "eGFR≥30优先ACEI/ARB，eGFR<30慎用",
                    "pregnant": "甲基多巴、拉贝洛尔，禁用ACEI/ARB"
                }
            },
            "non_pharmacological": [
                "DASH饮食模式：富含水果、蔬菜、低脂乳制品",
                "减重：每减重10kg，收缩压降低5-20mmHg",
                "限酒：收缩压降低2-4mmHg",
                "减盐：收缩压降低2-8mmHg",
                "运动：收缩压降低4-9mmHg",
                "减压：收缩压降低2-5mmHg"
            ],
            "emergency": {
                "hypertensive_crisis": {
                    "definition": "血压>180/120mmHg，伴靶器官损害",
                    "immediate_action": "立即就医，静脉降压药治疗",
                    "medications": ["硝普钠", "硝酸甘油", "乌拉地尔"],
                    "target": "1-2小时内平均动脉压降低不超过25%"
                }
            }
        },
        "diagnosis": {
            "diagnostic_criteria": [
                "诊室血压：收缩压≥140mmHg和/或舒张压≥90mmHg",
                "家庭血压：≥135/85mmHg",
                "动态血压：24h平均≥130/80mmHg，白天≥135/85mmHg，夜间≥120/70mmHg",
                "需不同日3次测量确认"
            ],
            "classification": {
                "正常血压": "<120/<80",
                "正常高值": "120-139/80-89",
                "高血压1级": "140-159/90-99",
                "高血压2级": "160-179/100-109",
                "高血压3级": "≥180/≥110",
                "单纯收缩期高血压": "≥140/<90"
            },
            "required_tests": [
                "基本检查：血常规、尿常规、心电图、空腹血糖、血脂",
                "推荐检查：超声心动图、颈动脉超声、肾功能、眼底检查",
                "选择性检查：动态血压监测、心率变异性、动脉硬化检测"
            ]
        },
        "monitoring": {
            "routine_monitoring": [
                "每日早晚各测量血压1次，每次测量2-3遍取平均值",
                "记录血压日记",
                "监测心率",
                "观察症状：头痛、头晕、胸闷"
            ],
            "frequency": {
                "low_risk": "每3个月1次",
                "medium_risk": "每2个月1次",
                "high_risk": "每月1次",
                "very_high_risk": "每2周1次"
            },
            "alert_thresholds": {
                "red_alert": "≥180/110mmHg立即就医",
                "yellow_alert": "≥160/100mmHg24小时内复测",
                "target": "<140/90mmHg（一般人群），<130/80mmHg（高危人群）"
            }
        },
        "lifestyle": {
            "diet": {
                "reduce_sodium": "每日食盐<6g，使用限盐勺",
                "increase_potassium": "新鲜蔬菜水果，香蕉、橙子、土豆",
                "DASH_diet": "低脂乳制品、全谷物、禽肉、鱼类、坚果",
                "limit_saturated_fat": "减少红肉，选用禽肉和鱼类"
            },
            "exercise": {
                "recommendations": "每周中等强度有氧运动150分钟或高强度75分钟",
                "types": ["快走", "慢跑", "游泳", "骑自行车", "太极拳"],
                "intensity": "最大心率的50-70%（最大心率=220-年龄）",
                "cautions": "避免剧烈运动和憋气动作"
            },
            "weight_control": {
                "target": "BMI<24kg/m²，腰围男性<90cm，女性<85cm",
                "strategy": "能量负平衡500-750kcal/d"
            },
            "smoking_alcohol": {
                "smoking": "完全戒烟，避免二手烟",
                "alcohol": "每日酒精摄入量男性<25g，女性<15g",
                "alcohol_conversion": "啤酒<750ml，葡萄酒<250ml，白酒<50ml"
            }
        },
        "risk_thresholds": {
            "low": {
                "bp": "<140/90",
                "risk_factors": "<2个",
                "target_organ_damage": "无"
            },
            "medium": {
                "bp": "140-159/90-99或140-179/90-109",
                "risk_factors": "2-3个",
                "target_organ_damage": "无"
            },
            "high": {
                "bp": "160-179/100-109",
                "risk_factors": "≥3个或糖尿病",
                "target_organ_damage": "无或轻度"
            },
            "very_high": {
                "bp": "≥180/≥110",
                "risk_factors": "≥3个或糖尿病或慢性肾病",
                "target_organ_damage": "存在"
            }
        }
    }
)


# =====================================================
# DIABETES GUIDELINES (糖尿病防治指南)
# =====================================================

DIABETES_GUIDELINE = GuidelineData(
    disease_code="diabetes",
    disease_name="糖尿病",
    display_name="中国2型糖尿病防治指南2023版",
    description="2型糖尿病的诊断、治疗与管理综合指南",
    category=GuidelineCategory.COMPREHENSIVE,
    evidence_level="A",
    sources=[
        "中华医学会糖尿病学分会",
        "中国医师协会内分泌代谢科医师分会"
    ],
    publication_year=2023,
    target_population={
        "age_range": {"min": 18, "max": 75},
        "gender": ["male", "female"],
        "special_groups": ["elderly", "pregnant", "adolescent"]
    },
    content={
        "prevention": {
            "primary_prevention": [
                "保持健康体重，BMI维持在18.5-23.9kg/m²",
                "合理膳食，控制总热量摄入",
                "减少精制碳水化合物，增加全谷物和膳食纤维",
                "限制含糖饮料和加工食品",
                "每周至少150分钟中等强度有氧运动",
                "减少静坐时间，每坐1小时活动5分钟",
                "限制饮酒",
                "保持7-8小时充足睡眠"
            ],
            "secondary_prevention": [
                "糖尿病前期（IFG/IGT）每年检测血糖",
                "IGT人群生活方式干预：减重5-10%",
                "必要时使用二甲双胍预防",
                "每3-6个月检测HbA1c",
                "定期筛查并发症"
            ],
            "tertiary_prevention": [
                "严格控制血糖：HbA1c<7.0%（一般人群）",
                "早期并发症筛查和干预",
                "多因素综合干预：血糖、血压、血脂",
                "建立糖尿病自我管理教育体系"
            ]
        },
        "treatment": {
            "pharmacological": {
                "first_line": "二甲双胍（无禁忌证情况下首选）",
                "oral_agents": [
                    "二甲双胍：降糖基础药物",
                    "磺脲类：格列美脲、格列齐特",
                    "格列奈类：瑞格列奈、那格列奈",
                    "α-糖苷酶抑制剂：阿卡波糖、伏格列波糖",
                    "DPP-4抑制剂：西格列汀、利格列汀",
                    "SGLT-2抑制剂：达格列净、恩格列净（心肾获益）",
                    "GLP-1受体激动剂：利拉鲁肽、司美格鲁肽"
                ],
                "injectable_agents": [
                    "胰岛素：基础胰岛素、预混胰岛素、强化胰岛素",
                    "GLP-1受体激动剂注射制剂"
                ],
                "treatment_algorithm": [
                    "新诊断T2DM：二甲双胍+生活方式",
                    "HbA1c不达标：加用第二种口服药",
                    "HbA1c仍不达标：加用第三种口服药或胰岛素",
                    "特殊人群：根据合并症选择药物"
                ]
            },
            "non_pharmacological": [
                "医学营养治疗：个体化营养处方",
                "运动治疗：每周150分钟中等强度有氧运动",
                "血糖监测：自我血糖监测+HbA1c",
                "糖尿病教育：自我管理技能培训",
                "心理支持：缓解焦虑抑郁"
            ],
            "emergency": {
                "diabetic_ketoacidosis": {
                    "definition": "血糖>13.9mmol/L，尿酮阳性，血pH<7.3",
                    "symptoms": ["恶心呕吐", "腹痛", "呼吸深快", "意识障碍"],
                    "immediate_action": "立即就医，补液+小剂量胰岛素"
                },
                "hypoglycemia": {
                    "definition": "血糖<3.9mmol/L",
                    "mild": "口服15g碳水化合物，15分钟后复测",
                    "severe": "意识障碍者静脉注射50%葡萄糖40ml或肌注胰高血糖素"
                }
            }
        },
        "diagnosis": {
            "diagnostic_criteria": [
                "典型症状+随机血糖≥11.1mmol/L",
                "空腹血糖≥7.0mmol/L",
                "OGTT 2h血糖≥11.1mmol/L",
                "HbA1c≥6.5%",
                "无典型症状需改日复查确认"
            ],
            "classification": {
                "1型糖尿病": "胰岛β细胞破坏，胰岛素绝对缺乏",
                "2型糖尿病": "胰岛素抵抗+胰岛素分泌不足",
                "妊娠期糖尿病": "妊娠期间发现的糖尿病",
                "特殊类型糖尿病": "基因缺陷、胰腺外分泌疾病等"
            },
            "required_tests": [
                "基本检查：空腹血糖、餐后2h血糖、HbA1c",
                "胰岛素功能：空腹胰岛素、C肽",
                "自身抗体：ICA、IAA、GAD（鉴别1型）",
                "并发症筛查：眼底、尿白蛋白、心电图、神经传导"
            ]
        },
        "monitoring": {
            "routine_monitoring": [
                "自我血糖监测：每日4-7次（强化治疗）或2-4次（常规治疗）",
                "监测点：空腹、三餐后2h、睡前、必要时夜间",
                "HbA1c：每3-6个月1次",
                "体重、血压：每次就诊",
                "足部检查：每日自我检查，每年1次专业检查"
            ],
            "frequency": {
                "unstable": "每日监测空腹和餐后血糖",
                "stable": "每周监测2-3天，每天2-4次",
                "HbA1c": "每3个月1次（达标后每6个月1次）"
            },
            "alert_thresholds": {
                "hypoglycemia": "<3.9mmol/L处理，<3.0mmol/L严重低血糖",
                "hyperglycemia": ">16.7mmol/L查酮体",
                "HbA1c_target": "<7.0%（一般），<8.0%（老年/脆弱），<6.5%（年轻/新诊断）"
            }
        },
        "lifestyle": {
            "diet": {
                "principles": [
                    "控制总热量，维持理想体重",
                    "合理分配三大营养素：碳水50-55%，蛋白15-20%，脂肪25-30%",
                    "少量多餐，定时定量",
                    "选择低GI食物：全谷物、杂豆、非淀粉类蔬菜"
                ],
                "carbohydrates": "每日200-300g，优先选择粗杂粮",
                "protein": "每日1.0-1.5g/kg（肾功能正常）",
                "fat": "每日0.8-1.0g/kg，限制饱和脂肪",
                "fiber": "每日25-30g膳食纤维",
                "avoid": "含糖饮料、精制甜点、油炸食品"
            },
            "exercise": {
                "recommendations": "每周≥150分钟中等强度有氧运动",
                "types": ["快走", "慢跑", "游泳", "骑自行车", "太极拳"],
                "resistance_training": "每周2-3次抗阻训练",
                "precautions": "避免空腹运动，注意足部保护"
            },
            "weight_control": {
                "target": "BMI<24kg/m²",
                "overweight": "减重7-15%有利于血糖控制"
            },
            "foot_care": [
                "每日检查足部有无破损",
                "温水洗脚（<37℃），彻底擦干",
                "选择合适鞋袜，避免赤脚",
                "及时处理鸡眼、老茧",
                "戒烟，保护足部血液循环"
            ]
        },
        "risk_thresholds": {
            "low": {
                "HbA1c": "<6.5%",
                "complications": "无"
            },
            "medium": {
                "HbA1c": "6.5-7.5%",
                "complications": "无或早期微血管病变"
            },
            "high": {
                "HbA1c": "7.5-9.0%",
                "complications": "早期微血管并发症"
            },
            "very_high": {
                "HbA1c": ">9.0%",
                "complications": "明显微血管或大血管并发症"
            }
        }
    }
)


# =====================================================
# DYSLIPIDEMIA GUIDELINES (血脂异常防治指南)
# =====================================================

DYSLIPIDEMIA_GUIDELINE = GuidelineData(
    disease_code="dyslipidemia",
    disease_name="血脂异常",
    display_name="中国成人血脂异常防治指南2023修订版",
    description="血脂异常的筛查、诊断与治疗指南",
    category=GuidelineCategory.COMPREHENSIVE,
    evidence_level="A",
    sources=[
        "中国成人血脂异常防治指南修订委员会",
        "中华医学会心血管病学分会"
    ],
    publication_year=2023,
    target_population={
        "age_range": {"min": 20, "max": 75},
        "gender": ["male", "female"],
        "special_groups": ["high_risk_CVD", "diabetes", "chronic_kidney_disease"]
    },
    content={
        "prevention": {
            "primary_prevention": [
                "低饱和脂肪饮食：饱和脂肪<7%总热量",
                "减少反式脂肪摄入",
                "增加膳食纤维：每日25-30g",
                "增加不饱和脂肪酸：鱼类、坚果、橄榄油",
                "控制体重：BMI<24kg/m²",
                "规律运动：每周150分钟中等强度运动",
                "限制饮酒",
                "戒烟"
            ],
            "secondary_prevention": [
                "40岁以上男性和绝经后女性每年检测血脂",
                "高危人群（高血压、糖尿病、肥胖）每6个月检测1次",
                "已有心血管疾病患者每3-6个月检测1次",
                "强化生活方式干预"
            ],
            "tertiary_prevention": [
                "长期降脂治疗，预防心血管事件复发",
                "综合控制其他危险因素",
                "定期监测肝功能、肌酸激酶"
            ]
        },
        "treatment": {
            "pharmacological": {
                "first_line": "他汀类药物（statins）",
                "statins": [
                    "阿托伐他汀：10-80mg/日",
                    "瑞舒伐他汀：5-40mg/日",
                    "辛伐他汀：20-40mg/日",
                    "匹伐他汀：2-4mg/日"
                ],
                "other_agents": [
                    "胆固醇吸收抑制剂：依折麦布10mg/日",
                    "PCSK9抑制剂：依洛尤单抗、阿利西尤单抗",
                    "贝特类：非诺贝特（高甘油三酯）",
                    "高纯度鱼油制剂（高甘油三酯）"
                ],
                "treatment_targets": {
                    "very_high_risk": "LDL-C<1.4mmol/L或较基线降低≥50%",
                    "high_risk": "LDL-C<1.8mmol/L或较基线降低≥50%",
                    "medium_risk": "LDL-C<2.6mmol/L",
                    "low_risk": "LDL-C<3.0mmol/L"
                }
            },
            "non_pharmacological": [
                "TLC饮食治疗：低饱和脂肪、低胆固醇",
                "增加植物甾醇摄入：每日2-3g",
                "增加可溶性膳食纤维：每日10-25g",
                "规律有氧运动",
                "减重：每减重10kg，LDL-C降低0.2mmol/L"
            ],
            "special_cases": {
                "hypertriglyceridemia": {
                    "mild": "2.3-5.6mmol/L：生活方式干预",
                    "moderate": "5.6-11.3mmol/L：贝特类或高纯度鱼油",
                    "severe": ">11.3mmol/L：立即启动治疗预防胰腺炎"
                }
            }
        },
        "diagnosis": {
            "diagnostic_criteria": {
                "total_cholesterol_elevated": "TC≥6.2mmol/L",
                "ldl_elevated": "LDL-C≥4.1mmol/L",
                "hdl_low": "HDL-C<1.0mmol/L",
                "triglycerides_elevated": "TG≥2.3mmol/L"
            },
            "classification": {
                "高胆固醇血症": "TC和/或LDL-C升高",
                "高甘油三酯血症": "TG升高",
                "混合型高脂血症": "TC+TG均升高",
                "低HDL-C血症": "HDL-C降低"
            },
            "required_tests": [
                "基本血脂检测：TC、TG、LDL-C、HDL-C",
                "空腹检测（空腹10-12小时）",
                "心血管风险评估",
                "肝功能、甲状腺功能（继发性因素筛查）"
            ]
        },
        "monitoring": {
            "routine_monitoring": [
                "服药后4-8周复查血脂、肝功能、CK",
                "达标后每3-6个月复查1次",
                "长期稳定者可6-12个月复查1次",
                "监测肌痛、乏力症状"
            ],
            "frequency": {
                "treatment_adjustment": "每4-8周1次",
                "stable": "每3-6个月1次",
                "adverse_events": "出现症状时立即检测"
            },
            "alert_thresholds": {
                "liver_enzymes": "ALT/AST>3倍正常上限，考虑停药",
                "CK": "CK>5倍正常上限或CK>10倍正常上限伴症状，停药",
                "LDL_C_target": "根据危险分层设定目标"
            }
        },
        "lifestyle": {
            "diet": {
                "reduce_saturated_fat": "红肉、黄油、全脂乳制品",
                "eliminate_trans_fat": "部分氢化植物油、油炸食品",
                "increase_unsaturated_fat": "鱼类、坚果、橄榄油、牛油果",
                "increase_fiber": "燕麦、豆类、水果、蔬菜",
                "plant_sterols": "强化食品，每日2-3g",
                "soy_protein": "每日25g大豆蛋白"
            },
            "exercise": {
                "aerobic": "每周≥150分钟中等强度有氧运动",
                "resistance": "每周2-3次抗阻训练",
                "effect": "运动可降低TG 10-20%，升高HDL-C 5-10%"
            },
            "weight_control": {
                "effect": "减重5-10%可改善所有血脂指标"
            },
            "smoking_alcohol": {
                "smoking": "戒烟可升高HDL-C",
                "alcohol": "限制饮酒，尤其高TG患者"
            }
        },
        "risk_thresholds": {
            "low": {
                "LDL_C": "<3.0mmol/L",
                "risk_factors": "0-1个"
            },
            "medium": {
                "LDL_C": "3.0-4.1mmol/L",
                "risk_factors": "2个"
            },
            "high": {
                "LDL_C": "4.1-4.9mmol/L",
                "risk_factors": "≥3个或高血压或糖尿病"
            },
            "very_high": {
                "LDL_C": "≥4.9mmol/L",
                "CVD": "已确诊心血管疾病"
            }
        }
    }
)


# =====================================================
# GOUT GUIDELINES (痛风防治指南)
# =====================================================

GOUT_GUIDELINE = GuidelineData(
    disease_code="gout",
    disease_name="痛风",
    display_name="中国高尿酸血症与痛风诊疗指南2023版",
    description="高尿酸血症与痛风的诊断、治疗与管理指南",
    category=GuidelineCategory.COMPREHENSIVE,
    evidence_level="A",
    sources=[
        "中华医学会内分泌学分会",
        "中华医学会风湿病学分会"
    ],
    publication_year=2023,
    target_population={
        "age_range": {"min": 18, "max": 75},
        "gender": ["male", "female"],
        "special_groups": ["chronic_kidney_disease", "transplant_recipients"]
    },
    content={
        "prevention": {
            "primary_prevention": [
                "限制高嘌呤食物：动物内脏、海鲜、肉汤",
                "限制酒精摄入，尤其啤酒和白酒",
                "减少果糖摄入：含糖饮料、高果糖水果",
                "增加水分摄入：每日≥2000ml",
                "规律运动，控制体重",
                "低脂乳制品摄入：每日300-500ml",
                "增加蔬菜摄入（除高嘌呤蔬菜外）",
                "避免过度劳累、受寒、关节损伤"
            ],
            "secondary_prevention": [
                "高尿酸血症（无症状）每3-6个月检测血尿酸",
                "尿酸>480μmol/L（男性）或>420μmol/L（女性）启动降尿酸治疗",
                "痛风发作后每年检测1-2次",
                "监测肾功能、尿常规"
            ],
            "tertiary_prevention": [
                "长期降尿酸治疗，维持血尿酸<360μmol/L",
                "严重痛风患者血尿酸<300μmol/L",
                "预防痛风石形成和缩小痛风石",
                "保护肾功能，预防痛风性肾病"
            ]
        },
        "treatment": {
            "pharmacological": {
                "acute_attack": [
                    "非甾体抗炎药：依托考昔、双氯芬酸钠、塞来昔布",
                    "秋水仙碱：首剂1mg，1小时后再服0.5mg",
                    "糖皮质激素：泼尼松0.5mg/kg/d，疗程5-10天"
                ],
                "urate_lowering": [
                    "别嘌醇：100-300mg/日，从小剂量开始",
                    "非布司他：40-80mg/日，尤其肾功能不全者",
                    "苯溴马隆：50-100mg/日，肾结石患者禁用"
                ],
                "prophylaxis": [
                    "起始降尿酸治疗时，预防性使用小剂量秋水仙碱或NSAIDs 3-6个月",
                    "避免尿酸急剧波动诱发急性发作"
                ]
            },
            "non_pharmacological": [
                "急性期休息，抬高患肢",
                "局部冷敷减轻疼痛",
                "多饮水，保证尿量>2000ml/d",
                "碱化尿液：口服碳酸氢钠或枸橼酸制剂，维持尿pH6.2-6.9"
            ],
            "tophus_management": [
                "降尿酸治疗是基础",
                "大痛风石可考虑手术切除",
                "局部护理，预防感染"
            ]
        },
        "diagnosis": {
            "diagnostic_criteria": {
                "acute_gout": [
                    "关节红肿热痛",
                    "首发多在第一跖趾关节",
                    "血尿酸升高",
                    "关节液穿刺找到尿酸盐结晶（金标准）",
                    "双能CT显示尿酸盐沉积"
                ],
                "hyperuricemia": [
                    "男性：血尿酸>420μmol/L",
                    "女性：血尿酸>360μmol/L"
                ]
            },
            "classification": {
                "无症状高尿酸血症": "仅血尿酸升高，无临床表现",
                "急性痛风性关节炎": "急性关节炎发作",
                "间歇期痛风": "两次发作间期",
                "慢性痛风性关节炎": "反复发作，关节畸形",
                "痛风性肾病": "尿酸沉积于肾脏"
            },
            "required_tests": [
                "血尿酸检测（清晨空腹）",
                "关节超声或双能CT",
                "关节液穿刺（必要时）",
                "肾功能、尿常规",
                "泌尿系超声（筛查肾结石）"
            ]
        },
        "monitoring": {
            "routine_monitoring": [
                "血尿酸：治疗初期每月1次，达标后每3-6个月1次",
                "肾功能：每3-6个月1次",
                "肝功能：服药期间定期检测",
                "关节症状：记录发作频率和部位"
            ],
            "frequency": {
                "treatment_initiation": "每月1次",
                "stable": "每3-6个月1次"
            },
            "alert_thresholds": {
                "uric_acid_target": "<360μmol/L（一般），<300μmol/L（严重痛风）",
                "renal_function": "eGFR<60ml/min/1.73m²需调整药物",
                "attack_frequency": "≥2次/年需启动降尿酸治疗"
            }
        },
        "lifestyle": {
            "diet": {
                "high_purine_foods_limit": [
                    "动物内脏：肝、肾、脑、肠",
                    "海鲜：沙丁鱼、凤尾鱼、贝类",
                    "浓肉汤、火锅汤",
                    "啤酒、白酒"
                ],
                "moderate_purine_foods": [
                    "肉类：牛肉、羊肉、猪肉（适量）",
                    "鱼类：鲤鱼、草鱼（适量）",
                    "豆类及豆制品（适量）"
                ],
                "low_purine_foods_encourage": [
                    "谷类：大米、小麦、面条",
                    "蔬菜：白菜、黄瓜、土豆、番茄",
                    "低脂乳制品",
                    "鸡蛋",
                    "水果（尤其低果糖水果）"
                ],
                "fructose_limit": "限制含糖饮料、高果糖水果（荔枝、龙眼）"
            },
            "exercise": {
                "recommendations": "非急性期规律运动，避免过度劳累",
                "cautions": "急性发作期休息，避免关节负重"
            },
            "weight_control": {
                "target": "BMI<24kg/m²",
                "note": "避免快速减重，可能诱发痛风发作"
            },
            "hydration": {
                "recommendation": "每日饮水≥2000ml",
                "options": ["白开水", "淡茶水", "苏打水"],
                "benefit": "促进尿酸排泄"
            }
        },
        "risk_thresholds": {
            "low": {
                "uric_acid": "<420μmol/L（男），<360μmol/L（女）",
                "attacks": "0次/年"
            },
            "medium": {
                "uric_acid": "420-480μmol/L（男），360-420μmol/L（女）",
                "attacks": "1次/年"
            },
            "high": {
                "uric_acid": "480-540μmol/L",
                "attacks": "2-3次/年",
                "tophus": "无"
            },
            "very_high": {
                "uric_acid": ">540μmol/L",
                "attacks": ">3次/年",
                "tophus": "有或关节畸形"
            }
        }
    }
)


# =====================================================
# OBESITY GUIDELINES (肥胖防治指南)
# =====================================================

OBESITY_GUIDELINE = GuidelineData(
    disease_code="obesity",
    disease_name="肥胖",
    display_name="中国肥胖症诊疗指南2023版",
    description="肥胖的筛查、诊断、治疗与预防指南",
    category=GuidelineCategory.COMPREHENSIVE,
    evidence_level="A",
    sources=[
        "中国营养学会肥胖防控分会",
        "中华医学会内分泌学分会"
    ],
    publication_year=2023,
    target_population={
        "age_range": {"min": 18, "max": 65},
        "gender": ["male", "female"],
        "special_groups": ["adolescent", "elderly", "postpartum"]
    },
    content={
        "prevention": {
            "primary_prevention": [
                "孕期合理增重，避免巨大儿",
                "母乳喂养至少6个月",
                "儿童期建立健康饮食习惯",
                "限制含糖饮料和高热量零食",
                "减少屏幕时间，增加户外活动",
                "保证充足睡眠",
                "家庭共同参与健康生活方式"
            ],
            "secondary_prevention": [
                "超重人群（BMI 24-28）每3-6个月监测体重",
                "腰围监测：男性≥90cm，女性≥85cm需关注",
                "每年检测血压、血糖、血脂",
                "评估肥胖相关并发症"
            ],
            "tertiary_prevention": [
                "长期体重管理，防止体重反弹",
                "预防肥胖相关疾病：糖尿病、高血压、OSA、骨关节病",
                "心理支持，预防肥胖相关的心理问题"
            ]
        },
        "treatment": {
            "pharmacological": {
                "indications": "BMI≥28或BMI≥24合并肥胖相关疾病",
                "medications": [
                    "奥利司他：脂肪酶抑制剂，120mg tid",
                    "利拉鲁肽3.0mg：GLP-1受体激动剂",
                    "司美格鲁肽2.4mg：GLP-1受体激动剂"
                ],
                "contraindications": [
                    "妊娠期、哺乳期",
                    "严重精神疾病",
                    "未控制的甲状腺疾病"
                ],
                "duration": "长期使用，定期评估疗效和安全性"
            },
            "non_pharmacological": [
                "医学营养治疗：低热量平衡膳食",
                "运动治疗：有氧+抗阻训练",
                "行为治疗：自我监测、刺激控制",
                "认知行为疗法：改变不良饮食行为",
                "强化生活方式干预：6-12个月"
            ],
            "surgical": {
                "indications": [
                    "BMI≥37.5",
                    "BMI≥32.5合并肥胖相关疾病"
                ],
                "procedures": [
                    "腹腔镜胃袖状切除术",
                    "Roux-en-Y胃旁路术"
                ],
                "expected_outcome": "减重15-30%"
            }
        },
        "diagnosis": {
            "diagnostic_criteria": {
                "BMI_based": {
                    "underweight": "BMI<18.5",
                    "normal": "BMI 18.5-23.9",
                    "overweight": "BMI 24.0-27.9",
                    "obese": "BMI≥28.0"
                },
                "waist_circumference_based": {
                    "male_central_obesity": "腰围≥90cm",
                    "female_central_obesity": "腰围≥85cm"
                }
            },
            "classification": {
                "grade_1_obesity": "BMI 28.0-32.4",
                "grade_2_obesity": "BMI 32.5-37.4",
                "grade_3_obesity": "BMI≥37.5"
            },
            "required_tests": [
                "基本检查：BMI、腰围、血压",
                "代谢评估：血糖、血脂、肝功能",
                "内分泌评估：甲状腺功能、皮质醇（必要时）",
                "并发症评估：脂肪肝、OSA筛查",
                "身体成分分析（骨密度、体脂率）"
            ]
        },
        "monitoring": {
            "routine_monitoring": [
                "体重：每周测量1-2次",
                "腰围：每月测量1次",
                "饮食日记：记录每日摄入",
                "运动记录：记录运动类型、时长、强度",
                "定期随访：每2-4周1次（减重期），每1-3月1次（维持期）"
            ],
            "frequency": {
                "weight": "每周1-2次",
                "waist": "每月1次",
                "lab_tests": "每3-6个月1次"
            },
            "alert_thresholds": {
                "weight_loss_target": "减重5-10%（显著健康获益）",
                "weight_loss_rate": "每周0.5-1kg（安全范围）",
                "warning_signs": ["快速体重下降", "电解质紊乱", "进食障碍"]
            }
        },
        "lifestyle": {
            "diet": {
                "calorie_restriction": "每日减少500-750kcal",
                "macronutrient_distribution": {
                    "carbohydrates": "45-65%",
                    "protein": "15-20%",
                    "fat": "20-30%"
                },
                "recommended_foods": [
                    "全谷物：燕麦、糙米、全麦面包",
                    "高蛋白食物：鱼、禽、蛋、豆类",
                    "蔬菜：非淀粉类蔬菜（菠菜、西兰花、黄瓜）",
                    "低糖水果：莓类、苹果"
                ],
                "avoid": [
                    "精制碳水化合物：白面包、糕点",
                    "含糖饮料",
                    "高脂肪食物：油炸食品、肥肉",
                    "加工食品"
                ],
                "meal_pattern": "定时定量，避免夜宵，细嚼慢咽"
            },
            "exercise": {
                "recommendations": "每周≥250分钟中等强度运动",
                "aerobic": "每周150-300分钟快走、慢跑、游泳、骑自行车",
                "resistance": "每周2-3次抗阻训练（20-30分钟）",
                "daily_activity": "每日步行≥8000步",
                "NEAT": "增加非运动性活动消耗（站立、家务、步行通勤）"
            },
            "behavior": {
                "self_monitoring": "记录体重、饮食、运动",
                "goal_setting": "短期目标（月度）+长期目标（年度）",
                "stimulus_control": ["清理家中高热量食物", "使用小餐具", "不在看电视时进食"],
                "problem_solving": "识别并应对诱发进食的情境",
                "stress_management": "非食物方式缓解压力"
            },
            "sleep": {
                "target": "7-9小时/晚",
                "importance": "睡眠不足影响食欲激素，导致食欲增加"
            }
        },
        "risk_thresholds": {
            "low": {
                "BMI": "24-27.9",
                "comorbidities": "无或1个"
            },
            "medium": {
                "BMI": "28-32.4",
                "comorbidities": "1-2个"
            },
            "high": {
                "BMI": "32.5-37.4",
                "comorbidities": "≥2个"
            },
            "very_high": {
                "BMI": "≥37.5",
                "comorbidities": "≥3个或严重并发症"
            }
        }
    }
)


# =====================================================
# ALL GUIDELINES
# =====================================================

ALL_GUIDELINES = [
    HYPERTENSION_GUIDELINE,
    DIABETES_GUIDELINE,
    DYSLIPIDEMIA_GUIDELINE,
    GOUT_GUIDELINE,
    OBESITY_GUIDELINE
]


# =====================================================
# DATABASE OPERATIONS
# =====================================================

async def insert_guideline(session: AsyncSession, guideline: GuidelineData) -> str:
    """
    Insert a single guideline into the database.

    Args:
        session: Database session
        guideline: GuidelineData to insert

    Returns:
        The ID of the inserted guideline
    """
    from src.infrastructure.persistence.models.guideline_models import GuidelineModel

    model = GuidelineModel(
        id=uuid4().hex,
        name=f"{guideline.disease_code}_guideline",
        display_name=guideline.display_name,
        description=guideline.description,
        disease_code=guideline.disease_code,
        disease_name=guideline.disease_name,
        category=guideline.category,
        guideline_content=guideline.content,
        evidence_level=guideline.evidence_level,
        sources=guideline.sources,
        publication_year=guideline.publication_year,
        publisher=guideline.publisher,
        target_population=guideline.target_population,
        version="1.0.0",
        enabled=True
    )

    session.add(model)
    await session.flush()

    logger.info(f"Inserted guideline: {guideline.display_name}")
    return model.id


async def check_existing_guidelines(session: AsyncSession) -> dict[str, Any]:
    """
    Check existing guidelines in the database.

    Args:
        session: Database session

    Returns:
        Dictionary with existing guidelines info
    """
    from src.infrastructure.persistence.models.guideline_models import GuidelineModel

    result = await session.execute(select(GuidelineModel.disease_code))
    existing_codes = {row[0] for row in result.fetchall()}

    return {
        "total": len(existing_codes),
        "disease_codes": existing_codes
    }


async def delete_guideline_by_disease(session: AsyncSession, disease_code: str) -> int:
    """
    Delete guidelines for a specific disease code.

    Args:
        session: Database session
        disease_code: Disease code to delete

    Returns:
        Number of rows deleted
    """
    from src.infrastructure.persistence.models.guideline_models import GuidelineModel

    stmt = delete(GuidelineModel).where(GuidelineModel.disease_code == disease_code)
    result = await session.execute(stmt)
    count = result.rowcount

    logger.info(f"Deleted {count} guideline(s) for disease: {disease_code}")
    return count


async def rollback_guidelines(session: AsyncSession, disease_codes: list[str] | None = None) -> int:
    """
    Rollback inserted guidelines.

    Args:
        session: Database session
        disease_codes: List of disease codes to rollback. If None, rollback all.

    Returns:
        Number of guidelines deleted
    """
    from src.infrastructure.persistence.models.guideline_models import GuidelineModel

    if disease_codes is None:
        stmt = delete(GuidelineModel)
    else:
        stmt = delete(GuidelineModel).where(
            GuidelineModel.disease_code.in_(disease_codes)
        )

    result = await session.execute(stmt)
    count = result.rowcount

    logger.warning(f"Rolled back {count} guideline(s)")
    return count


async def validate_guideline_content(guideline: GuidelineData) -> list[str]:
    """
    Validate guideline content structure.

    Args:
        guideline: GuidelineData to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required sections
    required_sections = [
        "prevention", "treatment", "diagnosis",
        "monitoring", "lifestyle", "risk_thresholds"
    ]

    for section in required_sections:
        if section not in guideline.content:
            errors.append(f"Missing required section: {section}")

    # Validate risk thresholds
    if "risk_thresholds" in guideline.content:
        for level in ["low", "medium", "high", "very_high"]:
            if level not in guideline.content["risk_thresholds"]:
                errors.append(f"Missing risk threshold level: {level}")

    return errors


# =====================================================
# MAIN SCRIPT
# =====================================================

async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Insert medical guidelines data")
    parser.add_argument("--dry-run", action="store_true", help="Validate data without inserting")
    parser.add_argument("--rollback", action="store_true", help="Rollback inserted data")
    parser.add_argument("--diseases", nargs="+", help="Specific diseases to insert (default: all)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing guidelines")

    args = parser.parse_args()

    # Filter guidelines if specific diseases requested
    guidelines_to_process = ALL_GUIDELINES
    if args.diseases:
        guidelines_to_process = [
            g for g in ALL_GUIDELINES
            if g.disease_code in args.diseases
        ]
        if not guidelines_to_process:
            logger.error(f"No matching guidelines found for: {args.diseases}")
            logger.info(f"Available disease codes: {[g.disease_code for g in ALL_GUIDELINES]}")
            return 1

    # Dry run: validate only
    if args.dry_run:
        logger.info("=== DRY RUN: Validating guideline data ===")
        all_valid = True
        for guideline in guidelines_to_process:
            errors = await validate_guideline_content(guideline)
            if errors:
                logger.error(f"Validation errors for {guideline.display_name}:")
                for error in errors:
                    logger.error(f"  - {error}")
                all_valid = False
            else:
                logger.info(f"✓ {guideline.display_name} - Valid")
        return 0 if all_valid else 1

    # Rollback mode
    if args.rollback:
        async with get_db_session_context() as session:
            disease_codes = [g.disease_code for g in guidelines_to_process]
            count = await rollback_guidelines(session, disease_codes)
            await session.commit()
            logger.info(f"Rollback complete: {count} guideline(s) deleted")
        return 0

    # Normal insertion mode
    logger.info("=== Inserting medical guidelines data ===")
    results = {
        "inserted": [],
        "skipped": [],
        "errors": []
    }

    async with get_db_session_context() as session:
        # Check existing guidelines
        existing = await check_existing_guidelines(session)
        logger.info(f"Existing guidelines: {existing}")

        # Process each guideline
        for guideline in guidelines_to_process:
            try:
                # Check if already exists
                if guideline.disease_code in existing["disease_codes"]:
                    if args.force:
                        logger.info(f"Overwriting existing guideline: {guideline.display_name}")
                        await delete_guideline_by_disease(session, guideline.disease_code)
                    else:
                        logger.warning(f"Skipping existing guideline: {guideline.display_name}")
                        results["skipped"].append(guideline.disease_code)
                        continue

                # Validate
                errors = await validate_guideline_content(guideline)
                if errors:
                    logger.error(f"Validation failed for {guideline.display_name}: {errors}")
                    results["errors"].append({
                        "disease": guideline.disease_code,
                        "errors": errors
                    })
                    continue

                # Insert
                guideline_id = await insert_guideline(session, guideline)
                results["inserted"].append({
                    "disease": guideline.disease_code,
                    "id": guideline_id,
                    "name": guideline.display_name
                })

            except Exception as e:
                logger.error(f"Error inserting {guideline.display_name}: {e}")
                results["errors"].append({
                    "disease": guideline.disease_code,
                    "error": str(e)
                })

        await session.commit()

    # Summary
    logger.info("\n=== Insertion Summary ===")
    logger.info(f"Inserted: {len(results['inserted'])} guideline(s)")
    for item in results["inserted"]:
        logger.info(f"  - {item['name']} (ID: {item['id']})")

    if results["skipped"]:
        logger.info(f"Skipped: {len(results['skipped'])} existing guideline(s)")
        for code in results["skipped"]:
            logger.info(f"  - {code}")

    if results["errors"]:
        logger.error(f"Errors: {len(results['errors'])}")
        for error in results["errors"]:
            logger.error(f"  - {error}")

    return 0 if not results["errors"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
