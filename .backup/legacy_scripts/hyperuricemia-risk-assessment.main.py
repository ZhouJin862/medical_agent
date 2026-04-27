#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main entry point for hyperuricemia-risk-assessment skill.

Evaluates uric acid levels and gout risk.
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

    # Check for uric acid data
    uric_acid = vital_signs.get("uric_acid")

    has_required_data = uric_acid is not None

    if has_required_data:
        # Generate report number
        report_date = datetime.now().strftime("%Y年%m月%d日")
        report_number = f"EBM-{datetime.now().strftime('%Y%m%d')}-UA"

        # Process uric acid value
        ua = uric_acid if uric_acid else 0

        # Classify based on gender (different normal ranges for men/women)
        gender = patient_data.get("gender", "male")

        if gender == "female":
            normal_range = "<360 μmol/L"
            if ua >= 420:
                uric_acid_level = "高尿酸血症"
                uric_acid_description = "血尿酸≥420 μmol/L，诊断为高尿酸血症。建议改善生活方式，限制高嘌呤食物摄入。"
                risk_level = "high"
            elif ua >= 360:
                uric_acid_level = "血尿酸偏高"
                uric_acid_description = "血尿酸360-419 μmol/L，属于偏高范围。建议注意饮食，限制高嘌呤食物摄入。"
                risk_level = "moderate"
            else:
                uric_acid_level = "血尿酸正常"
                uric_acid_description = "血尿酸<360 μmol/L，在正常范围内。建议继续保持健康生活方式。"
                risk_level = "normal"
        else:
            normal_range = "<420 μmol/L"
            if ua >= 480:
                uric_acid_level = "高尿酸血症（重度）"
                uric_acid_description = "血尿酸≥480 μmol/L，属于重度高尿酸血症，痛风风险显著增加。建议立即进行医学评估和干预。"
                risk_level = "very_high"
            elif ua >= 420:
                uric_acid_level = "高尿酸血症"
                uric_acid_description = "血尿酸420-479 μmol/L，诊断为高尿酸血症。建议改善生活方式，限制高嘌呤食物摄入。"
                risk_level = "high"
            else:
                uric_acid_level = "血尿酸正常"
                uric_acid_description = "血尿酸<420 μmol/L，在正常范围内。建议继续保持健康生活方式。"
                risk_level = "normal"

        # Annual gout risk
        if ua >= 600:
            annual_gout_risk = "7.0%（高危）"
            gout_risk_level = "高风险"
        elif ua >= 540:
            annual_gout_risk = "4.3%"
            gout_risk_level = "中高风险"
        elif ua >= 480:
            annual_gout_risk = "0.8%"
            gout_risk_level = "中低风险"
        elif ua >= 420:
            annual_gout_risk = "0.4%"
            gout_risk_level = "低风险"
        else:
            annual_gout_risk = "<0.1%"
            gout_risk_level = "极低风险"

        # Kidney assessment
        kidney_assessment_section = """建议定期检查肾功能：
- 血肌酐、尿素氮
- 尿常规
- 尿微量白蛋白/肌酐比值

高尿酸血症可导致尿酸性肾病，需警惕肾功能损害。"""

        # Metabolic syndrome assessment
        metabolic_syndrome_section = """高尿酸血症常与代谢综合征合并存在，建议筛查：
- 血脂：总胆固醇、甘油三酯、HDL-C
- 血糖：空腹血糖、糖化血红蛋白
- 血压
- 体重和腰围"""

        # Uric acid control target
        uric_acid_target = "<360 μmol/L（有痛风史者<300 μmol/L）"

        # Lifestyle intervention
        lifestyle_intervention = """1. **低嘌呤饮食**：限制动物内脏、海鲜、肉汤等高嘌呤食物
2. **限制酒精**：尤其是啤酒和白酒，建议戒酒
3. **多饮水**：每日饮水量≥2000ml，促进尿酸排泄
4. **控制体重**：BMI控制在18.5-23.9 kg/m²
5. **规律运动**：每周中等强度运动150分钟
6. **限制果糖**：减少含糖饮料和高糖水果摄入"""

        # Medication recommendation
        if ua >= 480 or gout_risk_level == "高风险":
            medication_recommendation = """建议启动降尿酸药物治疗，常用药物包括：
- 抑制尿酸生成药：别嘌醇、非布司他
- 促进尿酸排泄药：苯溴马隆

具体用药方案请遵医嘱，根据个体情况选择。"""
        elif ua >= 420:
            medication_recommendation = "暂无需药物治疗，建议通过生活方式干预控制尿酸。如6个月后尿酸仍不达标，考虑药物治疗。"
        else:
            medication_recommendation = "暂无需药物治疗，建议通过生活方式干预维持尿酸在正常范围。"

        # Follow-up plan
        if ua >= 480:
            follow_up_plan = "每3个月检测一次血尿酸，定期监测肾功能。"
        elif ua >= 420:
            follow_up_plan = "每6个月检测一次血尿酸，定期监测肾功能。"
        else:
            follow_up_plan = "每年检测一次血尿酸，保持健康生活方式。"

        # Prepare template variables
        template_vars = {
            "report_number": report_number,
            "assessment_date": report_date,
            "uric_acid": f"{ua:.0f}",
            "normal_range": normal_range,
            "uric_acid_level": uric_acid_level,
            "uric_acid_description": uric_acid_description,
            "annual_gout_risk": annual_gout_risk,
            "gout_risk_level": gout_risk_level,
            "kidney_assessment_section": kidney_assessment_section,
            "metabolic_syndrome_section": metabolic_syndrome_section,
            "uric_acid_target": uric_acid_target,
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
                "skill_name": "hyperuricemia-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": gout_risk_level,
                    "assessment": f"血尿酸{ua:.0f}μmol/L，{uric_acid_level}"
                }
            }

        except Exception as e:
            # Fallback: create modules directly without template
            modules = {
                "尿酸水平评估": f"""## 一、尿酸水平评估

### 尿酸测量值
| 项目 | 测量值 | 参考标准 |
|------|--------|---------|
| 血尿酸 | {ua:.0f} μmol/L | {normal_range} |

### 尿酸水平判定
**{uric_acid_level}**

{uric_acid_description}

**参考标准**：《中国高尿酸血症与痛风诊疗指南2019》""",

                "痛风风险评估": f"""## 二、痛风风险评估

### 年痛风发生率
**{annual_gout_risk}**

### 痛风风险等级
**{gout_risk_level}**""",

                "干预建议": f"""## 五、干预建议

### 尿酸控制目标
{uric_acid_target}

### 生活方式干预
{lifestyle_intervention}

### 药物治疗建议
{medication_recommendation}

### 随访计划
{follow_up_plan}"""
            }

            result = {
                "success": True,
                "skill_name": "hyperuricemia-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": risk_level,
                    "risk_grade": gout_risk_level,
                    "assessment": f"血尿酸{ua:.0f}μmol/L，{uric_acid_level}"
                }
            }
    else:
        # Missing data
        result = {
            "success": True,
            "skill_name": "hyperuricemia-risk-assessment",
            "data": {
                "status": "incomplete",
                "message": "需要补充血尿酸数据才能进行风险评估",
                "required_fields": ["uric_acid"]
            }
        }

    # Use UTF-8 encoding for output to handle special characters on Windows
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
