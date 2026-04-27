#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main entry point for obesity-risk-assessment skill.

Evaluates BMI and obesity risk.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Import template manager
sys.path.insert(0, str(Path(__file__).parent))
from template_manager import TemplateManager


def main():
    """Main entry point for skill execution."""
    # Parse arguments
    input_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--input" and i + 1 < len(sys.argv):
            input_file = sys.argv[i + 1]
            break

    if not input_file:
        result = {
            "success": False,
            "error": "No input file specified. Use --input <file.json>"
        }
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        else:
            print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # Read input data
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except Exception as e:
        result = {
            "success": False,
            "error": f"Failed to read input: {str(e)}"
        }
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        else:
            print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # Extract data
    user_input = input_data.get("user_input", "")
    patient_data = input_data.get("patient_data", {})
    vital_signs = input_data.get("vital_signs", {})
    medical_history = input_data.get("medical_history", {})

    # Check for height and weight data
    height = vital_signs.get("height")
    weight = vital_signs.get("weight")
    waist = vital_signs.get("waist")
    gender = patient_data.get("gender", "male")

    has_required_data = bool(height and weight)

    if has_required_data:
        # Generate report number
        report_date = datetime.now().strftime("%Y年%m月%d日")
        report_number = f"EBM-{datetime.now().strftime('%Y%m%d')}-OB"

        # Calculate BMI
        h = height if height else 0
        w = weight if weight else 0
        bmi = w / ((h / 100) ** 2) if h > 0 else 0

        # BMI classification
        if bmi < 18.5:
            bmi_level = "体重过低"
            risk_level = "low"
        elif bmi < 24:
            bmi_level = "体重正常"
            risk_level = "normal"
        elif bmi < 28:
            bmi_level = "超重"
            risk_level = "moderate"
        elif bmi < 32:
            bmi_level = "肥胖I级"
            risk_level = "high"
        elif bmi < 38:
            bmi_level = "肥胖II级"
            risk_level = "very_high"
        else:
            bmi_level = "肥胖III级"
            risk_level = "extremely_high"

        # Central obesity assessment
        waist_threshold = "85" if gender == "male" else "80"
        waist_val = waist if waist else 0

        if waist:
            if (gender == "male" and waist >= 90) or (gender == "female" and waist >= 85):
                central_obesity_level = "中心型肥胖"
            else:
                central_obesity_level = "无中心型肥胖"
        else:
            central_obesity_level = "未检测腰围"

        # Metabolic syndrome components
        fasting_glucose = vital_signs.get("fasting_glucose", 0)
        systolic_bp = vital_signs.get("systolic_bp", 0)
        diastolic_bp = vital_signs.get("diastolic_bp", 0)
        tg = vital_signs.get("tg", 0)
        hdl_c = vital_signs.get("hdl_c", 0)

        # Check metabolic syndrome components
        met_count = 0
        waist_met = "否"
        waist_result = "未检测"
        if waist:
            if (gender == "male" and waist >= 90) or (gender == "female" and waist >= 85):
                met_count += 1
                waist_met = "是"
                waist_result = f"腰围 {waist} cm（异常）"
            else:
                waist_result = f"腰围 {waist} cm（正常）"

        glucose_met = "否"
        glucose_result = "未检测"
        if fasting_glucose:
            if fasting_glucose >= 5.6:
                met_count += 1
                glucose_met = "是"
                glucose_result = f"空腹血糖 {fasting_glucose} mmol/L（异常）"
            else:
                glucose_result = f"空腹血糖 {fasting_glucose} mmol/L（正常）"

        bp_met = "否"
        bp_result = "未检测"
        if systolic_bp and diastolic_bp:
            if systolic_bp >= 130 or diastolic_bp >= 85:
                met_count += 1
                bp_met = "是"
                bp_result = f"血压 {systolic_bp}/{diastolic_bp} mmHg（异常）"
            else:
                bp_result = f"血压 {systolic_bp}/{diastolic_bp} mmHg（正常）"

        tg_met = "否"
        tg_result = "未检测"
        if tg:
            if tg >= 1.7:
                met_count += 1
                tg_met = "是"
                tg_result = f"甘油三酯 {tg} mmol/L（异常）"
            else:
                tg_result = f"甘油三酯 {tg} mmol/L（正常）"

        hdl_met = "否"
        hdl_result = "未检测"
        if hdl_c:
            if (gender == "male" and hdl_c < 1.04) or (gender == "female" and hdl_c < 1.30):
                met_count += 1
                hdl_met = "是"
                hdl_result = f"HDL-C {hdl_c} mmol/L（异常）"
            else:
                hdl_result = f"HDL-C {hdl_c} mmol/L（正常）"

        # Metabolic syndrome diagnosis
        if met_count >= 3:
            metabolic_syndrome_diagnosis = f"诊断为代谢综合征（满足{met_count}项）"
        else:
            metabolic_syndrome_diagnosis = f"未诊断为代谢综合征（满足{met_count}项）"

        # Body fat section
        body_fat_section = "暂无体脂率数据，建议使用体成分分析仪进行体脂评估。"

        # Related diseases section
        related_diseases_section = """肥胖相关疾病风险增加：
- 2型糖尿病
- 高血压
- 冠心病
- 脂肪肝
- 睡眠呼吸暂停综合征
- 骨关节疾病
- 某些癌症（如乳腺癌、结肠癌）"""

        # Target weight calculation
        target_bmi = 22  # Normal BMI
        target_weight = target_bmi * ((h / 100) ** 2)

        # Weight loss goal
        if bmi >= 24:
            weight_to_lose = w - target_weight
            weight_loss_goal = f"建议减重 {weight_to_lose:.1f} kg，达到目标体重 {target_weight:.1f} kg"
        else:
            weight_loss_goal = "保持当前体重，通过运动增加肌肉量"

        # Lifestyle intervention
        lifestyle_intervention = """1. **饮食控制**：控制总热量摄入，低脂低糖饮食，增加膳食纤维
2. **规律运动**：每周中等强度运动150-250分钟，如快走、慢跑、游泳
3. **行为干预**：规律作息，减少久坐，细嚼慢咽
4. **心理支持**：建立健康体重观念，避免极端减重方法"""

        # Treatment recommendation
        if bmi >= 32:
            treatment_recommendation = """建议综合减重治疗：
- 生活方式干预为基础
- 药物治疗：奥利司他、利拉鲁肽等
- 必要时考虑代谢手术

具体方案请遵医嘱。"""
        elif bmi >= 28:
            treatment_recommendation = "建议启动药物治疗（如奥利司他），配合生活方式干预。"
        else:
            treatment_recommendation = "暂无需药物治疗，建议通过生活方式干预控制体重。"

        # Follow-up plan
        if bmi >= 28:
            follow_up_plan = "每2周测量一次体重，每月评估一次BMI和腰围。"
        elif bmi >= 24:
            follow_up_plan = "每4周测量一次体重，每3个月评估一次BMI和腰围。"
        else:
            follow_up_plan = "每3个月测量一次体重，保持健康生活方式。"

        # Prepare template variables
        template_vars = {
            "report_number": report_number,
            "assessment_date": report_date,
            "height": f"{h:.0f}",
            "weight": f"{w:.1f}",
            "bmi": f"{bmi:.1f}",
            "bmi_level": bmi_level,
            "waist": f"{waist_val:.0f}" if waist else "未检测",
            "waist_threshold": waist_threshold,
            "central_obesity_level": central_obesity_level,
            "waist_result": waist_result,
            "waist_met": waist_met,
            "glucose_result": glucose_result,
            "glucose_met": glucose_met,
            "bp_result": bp_result,
            "bp_met": bp_met,
            "tg_result": tg_result,
            "tg_met": tg_met,
            "hdl_result": hdl_result,
            "hdl_met": hdl_met,
            "metabolic_syndrome_diagnosis": metabolic_syndrome_diagnosis,
            "body_fat_section": body_fat_section,
            "related_diseases_section": related_diseases_section,
            "target_weight": f"{target_weight:.1f} kg",
            "weight_loss_goal": weight_loss_goal,
            "lifestyle_intervention": lifestyle_intervention,
            "treatment_recommendation": treatment_recommendation,
            "follow_up_plan": follow_up_plan
        }

        # Load template and generate modular output
        template_manager = TemplateManager()
        try:
            template_manager.load_template('report')
            sections = template_manager.render_template_by_section(template_vars)

            # Create modular response - include section titles in content
            modules = {}
            for section_key, section_content in sections.items():
                if section_content.strip():
                    # Handle header section specially - no title needed
                    if section_key == "header":
                        modules["报告信息"] = section_content
                    else:
                        # Add section title as markdown header at the start of content
                        formatted_content = f"## {section_key}\n\n{section_content}"
                        modules[section_key] = formatted_content

            result = {
                "success": True,
                "skill_name": "obesity-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": bmi_level,
                    "assessment": f"BMI{bmi:.1f}kg/m²，{bmi_level}"
                }
            }

        except Exception as e:
            # Fallback: create modules directly without template
            modules = {
                "BMI评估": f"""## 一、BMI评估

### 体格测量值
| 项目 | 测量值 |
|------|--------|
| 身高 | {h:.0f} cm |
| 体重 | {w:.1f} kg |
| BMI | {bmi:.1f} kg/m² |

### BMI分级
**{bmi_level}**

**参考标准**：《中国成人超重和肥胖症预防控制指南》""",

                "中心型肥胖评估": f"""## 二、中心型肥胖评估

### 腰围测量
| 项目 | 测量值 | 参考标准 |
|------|--------|---------|
| 腰围 | {waist_val:.0f} cm | <{waist_threshold} cm |

### 中心型肥胖判定
**{central_obesity_level}**""",

                "干预建议": f"""## 六、干预建议

### 目标体重
{target_weight:.1f} kg

### 减重目标
{weight_loss_goal}

### 生活方式干预
{lifestyle_intervention}

### 随访计划
{follow_up_plan}"""
            }

            result = {
                "success": True,
                "skill_name": "obesity-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": bmi_level,
                    "assessment": f"BMI{bmi:.1f}kg/m²，{bmi_level}"
                }
            }
    else:
        # Missing data
        result = {
            "success": True,
            "skill_name": "obesity-risk-assessment",
            "data": {
                "status": "incomplete",
                "message": "需要补充身高和体重数据才能进行风险评估",
                "required_fields": ["height", "weight"]
            }
        }

    # Use UTF-8 encoding for output to handle special characters on Windows
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
