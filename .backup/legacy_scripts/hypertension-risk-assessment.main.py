#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main entry point for hypertension-risk-assessment skill.

This script orchestrates the health assessment workflow.
"""
import sys
import json
import subprocess
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

    # For now, return a simplified response
    # In production, this would call the actual validation and calculation scripts

    has_required_data = bool(
        vital_signs.get("systolic_bp") and
        vital_signs.get("diastolic_bp")
    )

    if has_required_data:
        # Process with actual data
        systolic = vital_signs.get("systolic_bp", 0)
        diastolic = vital_signs.get("diastolic_bp", 0)
        age = patient_data.get("age", "")
        gender = patient_data.get("gender", "male")

        # Generate report number
        report_date = datetime.now().strftime("%Y年%m月%d日")
        report_number = f"EBM-{datetime.now().strftime('%Y%m%d')}-HTN"

        # Blood pressure classification
        if systolic >= 180 or diastolic >= 110:
            bp_level = "3级高血压（重度）"
            bp_grade = "3级"
            bp_description = "收缩压≥180 mmHg和/或舒张压≥110 mmHg，属于重度高血压，需要立即就医治疗。"
            risk_level = "very_high"
            risk_category = "3"
            overall_risk = "高危"
        elif systolic >= 160 or diastolic >= 100:
            bp_level = "2级高血压（中度）"
            bp_grade = "2级"
            bp_description = "收缩压160-179 mmHg和/或舒张压100-109 mmHg，属于中度高血压，建议启动药物治疗。"
            risk_level = "high"
            risk_category = "2"
            overall_risk = "中高危"
        elif systolic >= 140 or diastolic >= 90:
            bp_level = "1级高血压（轻度）"
            bp_grade = "1级"
            bp_description = "收缩压140-159 mmHg和/或舒张压90-99 mmHg，属于轻度高血压，建议改善生活方式并监测血压。"
            risk_level = "moderate"
            risk_category = "1"
            overall_risk = "中低危"
        else:
            bp_level = "血压正常"
            bp_grade = "正常"
            bp_description = "血压在正常范围内，建议继续保持健康生活方式。"
            risk_level = "normal"
            risk_category = "0"
            overall_risk = "低危"

        # Risk factors assessment
        risk_factors = []
        risk_factors_count = 0

        # Check for other risk factors
        if vital_signs.get("fasting_glucose") and vital_signs["fasting_glucose"] >= 5.6:
            risk_factors.append("空腹血糖升高")
            risk_factors_count += 1
        if vital_signs.get("total_cholesterol") and vital_signs["total_cholesterol"] >= 5.18:
            risk_factors.append("血脂异常")
            risk_factors_count += 1
        if vital_signs.get("bmi") and vital_signs["bmi"] >= 24:
            risk_factors.append("超重/肥胖")
            risk_factors_count += 1
        if age and isinstance(age, str) and age.replace("岁", "").isdigit():
            age_val = int(age.replace("岁", ""))
            if age_val >= 45:
                risk_factors.append("年龄≥45岁")
                risk_factors_count += 1
        if medical_history.get("diagnoses"):
            risk_factors.append("有既往病史")
            risk_factors_count += 1

        risk_factors_summary = "、".join(risk_factors) if risk_factors else "无其他明显危险因素"

        # Organ damage assessment
        organ_damage_status = "未评估"
        organ_damage_section = "根据现有数据，未发现明确的靶器官损害证据。建议定期检查心电图、眼底、肾功能等。"

        # H-type hypertension assessment
        h_type_assessment = "暂同型半胱氨酸数据，无法评估H型高血压风险。"

        # BP target
        if risk_category == "0":
            bp_target = "<140/90 mmHg"
        else:
            bp_target = "<130/80 mmHg（若耐受可进一步降低）"

        # Lifestyle intervention
        lifestyle_intervention = f"""1. **限盐**：每日食盐摄入量<5g，减少腌制食品、加工食品
2. **控制体重**：BMI控制在18.5-23.9 kg/m²，男性腰围<90cm，女性<85cm
3. **规律运动**：每周中等强度运动150分钟，如快走、慢跑、游泳
4. **戒烟限酒**：完全戒烟，限制酒精摄入
5. **心理平衡**：保持心情舒畅，避免过度紧张焦虑"""

        # Medication recommendation
        if risk_category == "0":
            medication_recommendation = "暂无需药物治疗，建议通过生活方式干预控制血压。"
        else:
            medication_recommendation = f"""建议启动降压药物治疗，常用药物包括：
- ACEI/ARB类（如依那普利、氯沙坦）
- 钙通道阻滞剂（如氨氯地平、硝苯地平）
- 利尿剂（如氢氯噻嗪）

具体用药方案请遵医嘱，根据个体情况选择。"""

        # Follow-up plan
        if risk_category == "0":
            follow_up_plan = "每6个月测量一次血压，保持健康生活方式。"
        elif risk_category == "1":
            follow_up_plan = "每3个月测量一次血压，监测血压变化。"
        else:
            follow_up_plan = "每1-2周测量一次血压，密切监测，定期复诊。"

        # Prepare template variables
        template_vars = {
            "report_number": report_number,
            "assessment_date": report_date,
            "systolic": str(systolic),
            "diastolic": str(diastolic),
            "bp_level": bp_level,
            "bp_description": bp_description,
            "bp_grade": bp_grade,
            "risk_factors_summary": risk_factors_summary,
            "risk_stratification": f"综合评估为{overall_risk}",
            "risk_factors_count": str(risk_factors_count),
            "organ_damage_status": organ_damage_status,
            "organ_damage_section": organ_damage_section,
            "h_type_assessment": h_type_assessment,
            "bp_target": bp_target,
            "lifestyle_intervention": lifestyle_intervention,
            "medication_recommendation": medication_recommendation,
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
                "skill_name": "hypertension-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": bp_grade,
                    "assessment": f"血压{systolic}/{diastolic} mmHg，{bp_level}"
                }
            }

        except Exception as e:
            # Fallback: create modules directly without template
            modules = {
                "血压水平评估": f"""## 一、血压水平评估

### 血压测量值
| 项目 | 测量值 | 参考标准 |
|------|--------|---------|
| 收缩压 | {systolic} mmHg | <140 mmHg |
| 舒张压 | {diastolic} mmHg | <90 mmHg |

### 血压分级
**{bp_level}**

{bp_description}

**参考标准**：《中国高血压防治指南2018年修订版》""",

                "心血管风险分层": f"""## 二、心血管风险分层

### 危险因素评估
{risk_factors_summary}

### 风险分层结果
**综合评估为{overall_risk}**

| 项目 | 结果 |
|------|------|
| 血压级别 | {bp_grade} |
| 危险因素数量 | {risk_factors_count}项 |
| 靶器官损害 | {organ_damage_status} |
| 综合风险 | {overall_risk} |""",

                "干预建议": f"""## 五、干预建议

### 血压控制目标
{bp_target}

### 生活方式干预
{lifestyle_intervention}

### 药物治疗建议
{medication_recommendation}

### 随访计划
{follow_up_plan}"""
            }

            result = {
                "success": True,
                "skill_name": "hypertension-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": bp_grade,
                    "assessment": f"血压{systolic}/{diastolic} mmHg，{bp_level}"
                }
            }
    else:
        # Missing data - need to collect, show current health data
        # Build current health data display
        current_data_parts = []
        current_data_parts.append("### 当前健康档案")

        # Basic info - include party_id and source if available
        basic_info_parts = []
        name = patient_data.get("name", "患者")
        basic_info_parts.append(name)

        # Add party_id (customer ID) if available
        party_id = patient_data.get("party_id")
        if party_id:
            basic_info_parts.append(f"客户号: {party_id}")

        # Add age and gender
        age = patient_data.get("age")
        if age:
            basic_info_parts.append(f"{age}岁")

        gender = patient_data.get("gender", "")
        if gender == "male":
            basic_info_parts.append("男")
        elif gender == "female":
            basic_info_parts.append("女")

        # Add data source if available
        source = patient_data.get("source")
        if source == "ping_an_api":
            basic_info_parts.append("(来源: 平安健康档案)")

        current_data_parts.append(f"**基本信息**: {' '.join(basic_info_parts)}")

        # Medical history - diagnoses/conditions
        diagnoses = medical_history.get("diagnoses", [])
        chronic_diseases = medical_history.get("chronic_diseases", [])
        all_conditions = []

        for item in diagnoses:
            if isinstance(item, dict):
                code = item.get("code")
                if code:
                    all_conditions.append(code)
            elif isinstance(item, str):
                all_conditions.append(item)

        for item in chronic_diseases:
            if isinstance(item, dict):
                code = item.get("code")
                if code and code not in all_conditions:
                    all_conditions.append(code)
            elif isinstance(item, str):
                if item not in all_conditions:
                    all_conditions.append(item)

        if all_conditions:
            current_data_parts.append(f"**疾病史**: {', '.join(all_conditions)}")

        # Vital signs
        vital_signs_parts = []
        if vital_signs.get("height"):
            vital_signs_parts.append(f"身高 {vital_signs['height']}cm")
        if vital_signs.get("weight"):
            vital_signs_parts.append(f"体重 {vital_signs['weight']}kg")
        if vital_signs.get("bmi"):
            vital_signs_parts.append(f"BMI {vital_signs['bmi']}")
        if vital_signs.get("systolic_bp") or vital_signs.get("diastolic_bp"):
            sbp = vital_signs.get("systolic_bp", "?")
            dbp = vital_signs.get("diastolic_bp", "?")
            vital_signs_parts.append(f"血压 {sbp}/{dbp} mmHg")
        if vital_signs.get("fasting_glucose"):
            vital_signs_parts.append(f"空腹血糖 {vital_signs['fasting_glucose']} mmol/L")
        if vital_signs.get("total_cholesterol"):
            vital_signs_parts.append(f"总胆固醇 {vital_signs['total_cholesterol']} mmol/L")

        if vital_signs_parts:
            current_data_parts.append(f"**已有检查数据**: {', '.join(vital_signs_parts)}")
        else:
            current_data_parts.append("**已有检查数据**: 暂无")

        # Missing blood pressure data
        current_data_parts.append("**缺少数据**: 收缩压、舒张压")

        current_data_display = "\n\n".join(current_data_parts)

        result = {
            "success": True,
            "skill_name": "hypertension-risk-assessment",
            "data": {
                "status": "incomplete",
                "current_data": current_data_display,
                "message": f"需要补充血压数据才能进行风险评估\n\n{current_data_display}",
                "required_fields": ["systolic_bp", "diastolic_bp"]
            }
        }
        # Use UTF-8 encoding for output
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return

    # Use UTF-8 encoding for output to handle special characters on Windows
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
