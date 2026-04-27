#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main entry point for hyperglycemia-risk-assessment skill.

Evaluates blood sugar levels and diabetes risk.
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

    # Check for blood sugar data
    fasting_glucose = vital_signs.get("fasting_glucose")
    hba1c = vital_signs.get("hba1c")

    has_required_data = bool(fasting_glucose or hba1c)

    if has_required_data:
        # Generate report number
        report_date = datetime.now().strftime("%Y年%m月%d日")
        report_number = f"EBM-{datetime.now().strftime('%Y%m%d')}-GLY"

        # Process glucose values
        fg = fasting_glucose if fasting_glucose else 0
        hba = hba1c if hba1c else 0

        # Classify based on diabetes guidelines
        if hba1c:
            if hba1c >= 6.5:
                glucose_status = "糖尿病"
                risk_level = "very_high"
                risk_category = "3"
                glucose_description = "糖化血红蛋白≥6.5%，提示糖尿病可能。建议进一步检查空腹血糖和餐后血糖，并咨询内分泌科医生。"
                three_year_risk = ">20"
            elif hba1c >= 6.0:
                glucose_status = "糖尿病高危"
                risk_level = "high"
                risk_category = "2"
                glucose_description = "糖化血红蛋白5.7-6.4%，提示糖尿病前期，存在高血糖风险。建议改善生活方式，定期监测血糖。"
                three_year_risk = "10-20"
            else:
                glucose_status = "血糖正常"
                risk_level = "normal"
                risk_category = "0"
                glucose_description = "糖化血红蛋白<5.7%，血糖水平正常。建议继续保持健康生活方式。"
                three_year_risk = "<5"
        elif fasting_glucose:
            if fasting_glucose >= 7.0:
                glucose_status = "糖尿病"
                risk_level = "very_high"
                risk_category = "3"
                glucose_description = "空腹血糖≥7.0 mmol/L，提示糖尿病可能。建议进一步检查糖化血红蛋白和餐后血糖，并咨询内分泌科医生。"
                three_year_risk = ">20"
            elif fasting_glucose >= 6.1:
                glucose_status = "空腹血糖受损"
                risk_level = "high"
                risk_category = "2"
                glucose_description = "空腹血糖6.1-6.9 mmol/L，提示空腹血糖受损（糖尿病前期）。建议改善生活方式，定期监测血糖。"
                three_year_risk = "10-20"
            elif fasting_glucose >= 5.6:
                glucose_status = "血糖偏高"
                risk_level = "moderate"
                risk_category = "1"
                glucose_description = "空腹血糖5.6-6.0 mmol/L，属于血糖偏高范围。建议注意饮食，控制糖分摄入，定期监测血糖。"
                three_year_risk = "5-10"
            else:
                glucose_status = "血糖正常"
                risk_level = "normal"
                risk_category = "0"
                glucose_description = "空腹血糖<5.6 mmol/L，血糖水平正常。建议继续保持健康生活方式。"
                three_year_risk = "<5"
        else:
            glucose_status = "血糖正常"
            risk_level = "normal"
            risk_category = "0"
            glucose_description = "血糖水平正常。建议继续保持健康生活方式。"
            three_year_risk = "<5"

        # Prediabetes assessment
        if risk_category == "0":
            prediabetes_assessment = "根据现有数据，不属于糖尿病前期人群。"
        elif risk_category == "1":
            prediabetes_assessment = "属于糖尿病前期风险人群，建议通过生活方式干预降低糖尿病发病风险。"
        else:
            prediabetes_assessment = "糖尿病风险较高，建议立即进行医学评估和干预。"

        # Insulin resistance assessment
        insulin_resistance_section = "暂无胰岛素和C肽数据，无法评估胰岛素抵抗情况。"

        # Complications screening
        complications_section = """建议定期进行糖尿病并发症筛查：
- 糖尿病肾病：尿微量白蛋白/肌酐比值
- 糖尿病视网膜病变：眼底检查
- 糖尿病神经病变：足部感觉检查
- 心血管疾病：心电图、心脏彩超"""

        # Glucose control target
        if risk_category == "0":
            glucose_target = "空腹血糖<6.1 mmol/L，糖化血红蛋白<5.7%"
        elif risk_category == "3":
            glucose_target = "空腹血糖<7.0 mmol/L，糖化血红蛋白<7.0%（老年人可放宽至<8.0%）"
        else:
            glucose_target = "空腹血糖<6.1 mmol/L，糖化血红蛋白<6.5%"

        # Lifestyle intervention
        lifestyle_intervention = """1. **饮食控制**：控制总热量摄入，低糖低脂饮食，增加膳食纤维
2. **规律运动**：每周中等强度运动150分钟，如快走、慢跑、游泳
3. **控制体重**：BMI控制在18.5-23.9 kg/m²，男性腰围<90cm，女性<85cm
4. **戒烟限酒**：完全戒烟，限制酒精摄入
5. **心理平衡**：保持心情舒畅，避免过度紧张焦虑"""

        # Medication recommendation
        if risk_category == "0":
            medication_recommendation = "暂无需药物治疗，建议通过生活方式干预控制血糖。"
        elif risk_category == "3":
            medication_recommendation = """建议启动降糖药物治疗，常用药物包括：
- 双胍类（如二甲双胍）
- 磺脲类（如格列吡嗪）
- α-糖苷酶抑制剂（如阿卡波糖）
- DPP-4抑制剂（如西格列汀）
- SGLT-2抑制剂（如达格列净）

具体用药方案请遵医嘱，根据个体情况选择。"""
        else:
            medication_recommendation = "暂无需药物治疗，建议通过生活方式干预控制血糖。如3个月后血糖仍不达标，考虑药物治疗。"

        # Follow-up plan
        if risk_category == "0":
            follow_up_plan = "每年检测一次空腹血糖和糖化血红蛋白。"
        elif risk_category == "3":
            follow_up_plan = "每3个月检测一次糖化血红蛋白，每2周测量一次空腹血糖和餐后血糖。"
        else:
            follow_up_plan = "每6个月检测一次糖化血红蛋白，每月测量一次空腹血糖和餐后血糖。"

        # Prepare template variables
        template_vars = {
            "report_number": report_number,
            "assessment_date": report_date,
            "fasting_glucose": f"{fg:.1f}" if fg else "未检测",
            "hba1c": f"{hba:.1f}" if hba else "未检测",
            "glucose_status": glucose_status,
            "glucose_description": glucose_description,
            "prediabetes_assessment": prediabetes_assessment,
            "three_year_risk": three_year_risk,
            "insulin_resistance_section": insulin_resistance_section,
            "complications_section": complications_section,
            "glucose_target": glucose_target,
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
                "skill_name": "hyperglycemia-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": glucose_status,
                    "assessment": f"空腹血糖{fg:.1f}mmol/L" if fg else f"糖化血红蛋白{hba:.1f}%"
                }
            }

        except Exception as e:
            # Fallback: create modules directly without template
            modules = {
                "糖代谢状态评估": f"""## 一、糖代谢状态评估

### 血糖测量值
| 项目 | 测量值 | 参考标准 |
|------|--------|---------|
| 空腹血糖 | {fg:.1f} mmol/L | <6.1 mmol/L |
| 糖化血红蛋白 | {hba:.1f} % | <5.7% |

### 糖代谢状态
**{glucose_status}**

{glucose_description}

**参考标准**：《中国2型糖尿病防治指南2020年版》""",

                "糖尿病风险评估": f"""## 二、糖尿病风险评估

### 糖尿病前期评估
{prediabetes_assessment}

### 3年糖尿病转化风险
**{three_year_risk}%**""",

                "干预建议": f"""## 五、干预建议

### 血糖控制目标
{glucose_target}

### 生活方式干预
{lifestyle_intervention}

### 药物治疗建议
{medication_recommendation}

### 随访计划
{follow_up_plan}"""
            }

            result = {
                "success": True,
                "skill_name": "hyperglycemia-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": glucose_status,
                    "assessment": f"空腹血糖{fg:.1f}mmol/L" if fg else f"糖化血红蛋白{hba:.1f}%"
                }
            }
    else:
        # Missing data
        result = {
            "success": True,
            "skill_name": "hyperglycemia-risk-assessment",
            "data": {
                "status": "incomplete",
                "message": "需要补充血糖数据才能进行风险评估",
                "required_fields": ["fasting_glucose", "hba1c"]
            }
        }

    # Use UTF-8 encoding for output to handle special characters on Windows
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
