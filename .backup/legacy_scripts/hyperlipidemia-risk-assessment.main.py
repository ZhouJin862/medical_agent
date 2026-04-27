#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main entry point for hyperlipidemia-risk-assessment skill.

Evaluates cholesterol and lipid levels.
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

    # Check for lipid data
    total_cholesterol = vital_signs.get("total_cholesterol")
    ldl_c = vital_signs.get("ldl_c")
    tg = vital_signs.get("tg")
    hdl_c = vital_signs.get("hdl_c")

    has_required_data = bool(total_cholesterol or ldl_c or tg or hdl_c)

    if has_required_data:
        # Generate report number
        report_date = datetime.now().strftime("%Y年%m月%d日")
        report_number = f"EBM-{datetime.now().strftime('%Y%m%d')}-LIP"

        # Process lipid values
        tc = total_cholesterol if total_cholesterol else 0
        ld = ldl_c if ldl_c else 0
        t = tg if tg else 0
        hd = hdl_c if hdl_c else 0

        # Classify TC
        if tc >= 6.22:
            tc_level = "升高"
        elif tc >= 5.18:
            tc_level = "边缘升高"
        else:
            tc_level = "正常"

        # Classify TG
        if t >= 2.26:
            tg_level = "升高"
        elif t >= 1.70:
            tg_level = "边缘升高"
        else:
            tg_level = "正常"

        # Classify LDL-C
        if ld >= 4.9:
            ldl_c_level = "升高"
        elif ld >= 3.37:
            ldl_c_level = "边缘升高"
        else:
            ldl_c_level = "正常"

        # Classify HDL-C
        if hd < 1.04:
            hdl_c_level = "降低"
        else:
            hdl_c_level = "正常"

        # Determine lipid disorder type
        disorders = []
        if tc_level == "升高":
            disorders.append("高胆固醇血症")
        if tg_level == "升高":
            disorders.append("高甘油三酯血症")
        if ldl_c_level == "升高":
            disorders.append("高低密度脂蛋白胆固醇血症")
        if hdl_c_level == "降低":
            disorders.append("低高密度脂蛋白胆固醇血症")

        if disorders:
            lipid_disorder_type = "、".join(disorders)
        elif tc_level == "边缘升高" or tg_level == "边缘升高" or ldl_c_level == "边缘升高":
            lipid_disorder_type = "血脂边缘升高"
        else:
            lipid_disorder_type = "血脂正常"

        # Risk tier based on LDL-C
        if ld >= 4.9:
            risk_tier = "高危"
            ldl_target = "<2.6 mmol/L"
        elif ld >= 3.37:
            risk_tier = "中危"
            ldl_target = "<3.0 mmol/L"
        else:
            risk_tier = "低危"
            ldl_target = "<3.4 mmol/L"

        # At target check
        at_target = "是" if ld < 3.0 else "否"

        # Residual risk assessment
        residual_risk_section = "即使LDL-C达标，如果存在TG升高或HDL-C降低，仍存在心血管残余风险。建议关注非HDL-C水平。"

        # Cardiovascular risk assessment
        cardiovascular_risk_section = """根据现有数据，建议进行10年ASCVD发病风险评估。
如存在以下危险因素，风险增加：
- 高血压
- 糖尿病
- 吸烟
- 肥胖
- 家族早发心血管病史"""

        # LDL control target
        ldl_control_target = ldl_target

        # Lifestyle intervention
        lifestyle_intervention = """1. **低脂饮食**：减少饱和脂肪酸摄入，增加不饱和脂肪酸摄入
2. **控制体重**：BMI控制在18.5-23.9 kg/m²
3. **规律运动**：每周中等强度运动150分钟
4. **戒烟限酒**：完全戒烟，限制酒精摄入
5. **增加膳食纤维**：每天摄入25-30g膳食纤维"""

        # Medication recommendation
        if ld >= 4.0 or tc >= 6.22:
            medication_recommendation = """建议启动他汀类药物治疗，常用药物包括：
- 阿托伐他汀
- 瑞舒伐他汀
- 辛伐他汀

具体用药方案请遵医嘱，根据个体情况选择。"""
        else:
            medication_recommendation = "暂无需药物治疗，建议通过生活方式干预控制血脂。"

        # Follow-up plan
        if ld >= 3.37 or tc >= 5.18:
            follow_up_plan = "每3个月检测一次血脂，监测血脂变化。"
        else:
            follow_up_plan = "每6个月检测一次血脂，保持健康生活方式。"

        # Prepare template variables
        template_vars = {
            "report_number": report_number,
            "assessment_date": report_date,
            "tc": f"{tc:.1f}" if tc else "未检测",
            "tg": f"{t:.1f}" if t else "未检测",
            "ldl_c": f"{ld:.1f}" if ld else "未检测",
            "hdl_c": f"{hd:.1f}" if hd else "未检测",
            "tc_level": tc_level,
            "tg_level": tg_level,
            "ldl_c_level": ldl_c_level,
            "hdl_c_level": hdl_c_level,
            "lipid_disorder_type": lipid_disorder_type,
            "risk_tier": risk_tier,
            "ldl_target": ldl_target,
            "at_target": at_target,
            "residual_risk_section": residual_risk_section,
            "cardiovascular_risk_section": cardiovascular_risk_section,
            "ldl_control_target": ldl_control_target,
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
                "skill_name": "hyperlipidemia-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": "high" if ld >= 4.9 else "moderate" if ld >= 3.37 else "normal",
                    "risk_grade": risk_tier,
                    "assessment": f"总胆固醇{tc:.1f}mmol/L，{lipid_disorder_type}"
                }
            }

        except Exception as e:
            # Fallback: create modules directly without template
            modules = {
                "血脂水平评估": f"""## 一、血脂水平评估

### 血脂测量值
| 项目 | 测量值 | 参考标准 | 评估 |
|------|--------|---------|------|
| 总胆固醇(TC) | {tc:.1f} mmol/L | <5.18 mmol/L | {tc_level} |
| 甘油三酯(TG) | {t:.1f} mmol/L | <1.70 mmol/L | {tg_level} |
| LDL-C | {ld:.1f} mmol/L | <3.35 mmol/L | {ldl_c_level} |
| HDL-C | {hd:.1f} mmol/L | ≥1.04 mmol/L | {hdl_c_level} |

### 血脂异常分类
**{lipid_disorder_type}**

**参考标准**：《中国成人血脂异常防治指南2016年修订版》""",

                "LDL-C危险分层": f"""## 二、LDL-C危险分层

### 危险分层结果
**{risk_tier}**

| 项目 | 结果 |
|------|------|
| LDL-C水平 | {ld:.1f} mmol/L |
| 危险分层 | {risk_tier} |
| LDL-C目标值 | {ldl_target} |
| 是否达标 | {at_target} |""",

                "干预建议": f"""## 五、干预建议

### LDL-C控制目标
{ldl_control_target}

### 生活方式干预
{lifestyle_intervention}

### 药物治疗建议
{medication_recommendation}

### 随访计划
{follow_up_plan}"""
            }

            result = {
                "success": True,
                "skill_name": "hyperlipidemia-risk-assessment",
                "data": {
                    "modules": modules,
                    "total_modules": len(modules),
                    "risk_level": "high" if ld >= 4.9 else "moderate" if ld >= 3.37 else "normal",
                    "risk_grade": risk_tier,
                    "assessment": f"总胆固醇{tc:.1f}mmol/L，{lipid_disorder_type}"
                }
            }
    else:
        # Missing data - show current health data
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
        if vital_signs_parts:
            current_data_parts.append(f"**已有检查数据**: {', '.join(vital_signs_parts)}")
        else:
            current_data_parts.append("**已有检查数据**: 暂无")

        # Missing lipid data
        current_data_parts.append("**缺少数据**: 总胆固醇、低密度脂蛋白、高密度脂蛋白、甘油三酯")

        current_data_display = "\n\n".join(current_data_parts)

        result = {
            "success": True,
            "skill_name": "hyperlipidemia-risk-assessment",
            "data": {
                "status": "incomplete",
                "current_data": current_data_display,
                "message": f"需要补充血脂数据才能进行风险评估\n\n{current_data_display}",
                "required_fields": ["total_cholesterol", "ldl_c", "hdl_c", "tg"]
            }
        }

    # Use UTF-8 encoding for output to handle special characters on Windows
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
