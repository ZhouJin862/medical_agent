#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cardiovascular Disease Risk Assessment - Main Execution Script

Main entry point for CVD risk assessment that:
- Accepts patient data from multiple input formats (CLI, JSON, agent context)
- Extracts/validates patient parameters (age, gender, BP, lipids, diabetes status, smoking, etc.)
- Calls risk_calculator.py for risk categorization
- Returns structured JSON output for the agent
"""

import json
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import asdict

# Import the risk calculator
from risk_calculator import (
    CVDRiskCalculator,
    PatientData,
    RiskCategory,
    RiskAssessmentResult
)


class CVDAssessmentExecutor:
    """Main executor for cardiovascular disease risk assessment"""

    def __init__(self):
        self.calculator = CVDRiskCalculator()

    def extract_patient_data(self, input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse patient data from various input formats

        Supported formats:
        1. JSON file path (string)
        2. JSON string
        3. Python dict with patient fields
        4. Agent nested format (patient_data, vital_signs)
        5. Natural text description (for agent context)
        """
        # Handle file path
        if isinstance(input_data, str):
            # Check if it's a file path
            input_path = Path(input_data)
            if input_path.exists():
                with open(input_path, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)
            else:
                # Try to parse as JSON string
                try:
                    input_data = json.loads(input_data)
                except json.JSONDecodeError:
                    # Treat as natural text description
                    return self._parse_natural_text(input_data)

        # Handle dict input (including parsed from JSON string or file)
        if isinstance(input_data, dict):
            # Check for agent nested format (patient_data, vital_signs, medical_history)
            if 'patient_data' in input_data or 'vital_signs' in input_data:
                return self._flatten_agent_format(input_data)

            # Check for health_metrics format (from health_data_validator)
            if 'health_metrics' in input_data or 'patient_info' in input_data:
                return self._flatten_health_metrics_format(input_data)

            # Check for user_input format (natural text description)
            if 'user_input' in input_data:
                result = {}
                # Parse natural text to extract patient data
                if input_data.get('user_input'):
                    natural_data = self._parse_natural_text(input_data['user_input'])
                    result.update(natural_data)
                # Also include any other fields from input_data
                for key, value in input_data.items():
                    if key != 'user_input' and value is not None:
                        result[key] = value
                return result

            # Flat format - return as is
            return input_data

        return {}

    def _flatten_agent_format(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten agent nested format to flat patient data

        Input: {"patient_data": {"basic_info": {"age": 45}, ...},
                "vital_signs": {"systolic_bp": 185, "diastolic_bp": 105}}
        Output: {"age": 45, "gender": "male", "sbp": 185, "dbp": 105}
        """
        patient_data = {}

        # Extract from patient_data (handle nested basic_info format)
        if 'patient_data' in input_data:
            pd = input_data['patient_data']

            # Handle nested basic_info format from agent
            if 'basic_info' in pd:
                bi = pd['basic_info']
                age = bi.get('age')
                # Convert age to int if it's a string (Ping An API returns age as string)
                if age is not None:
                    try:
                        patient_data['age'] = int(str(age).strip())
                    except (ValueError, TypeError):
                        patient_data['age'] = age
                # Gender is not extracted by agent, will be parsed from user_input later
            else:
                # Handle flat format
                age = pd.get('age')
                if age is not None:
                    try:
                        patient_data['age'] = int(str(age).strip())
                    except (ValueError, TypeError):
                        patient_data['age'] = age
                patient_data['gender'] = pd.get('gender')

        # Extract from vital_signs
        if 'vital_signs' in input_data:
            vs = input_data['vital_signs']
            # Map agent field names to internal names
            field_mapping = {
                'systolic_bp': 'sbp',
                'diastolic_bp': 'dbp',
                'total_cholesterol': 'tc',
                'ldl_c': 'ldl_c',
                'hdl_c': 'hdl_c',
                'tg': 'tg',
                'fasting_glucose': 'fasting_glucose',
                'hba1c': 'hba1c',
                'bmi': 'bmi',
                'waist': 'waist_circumference',
                'uric_acid': 'uric_acid'
            }
            for agent_field, internal_field in field_mapping.items():
                if agent_field in vs and vs[agent_field] is not None:
                    patient_data[internal_field] = vs[agent_field]

        # Extract from medical_history
        if 'medical_history' in input_data:
            mh = input_data['medical_history']
            patient_data.update({
                'has_diabetes': mh.get('has_diabetes', False),
                'smoker': mh.get('smoker', False),
                'family_history_premature_cvd': mh.get('family_history_premature_cvd', False),
                'has_ckd': mh.get('has_ckd', False),
                'has_established_cvd': mh.get('has_established_cvd', False)
            })

        # DERIVE has_diabetes from vital_signs if not already set
        # HbA1c ≥6.5% indicates diabetes
        if not patient_data.get('has_diabetes') and patient_data.get('hba1c'):
            if patient_data['hba1c'] >= 6.5:
                patient_data['has_diabetes'] = True
        # Fasting glucose ≥7.0 mmol/L also indicates diabetes
        if not patient_data.get('has_diabetes') and patient_data.get('fasting_glucose'):
            if patient_data['fasting_glucose'] >= 7.0:
                patient_data['has_diabetes'] = True

        # DERIVE CKD stage from medical diagnoses if not set
        if not patient_data.get('has_ckd') and 'medical_history' in input_data:
            diagnoses = input_data['medical_history'].get('diagnoses', [])
            if isinstance(diagnoses, list):
                for d in diagnoses:
                    if isinstance(d, dict) and d.get('code'):
                        code = d['code']
                        # N18.x = Chronic kidney disease, stage 5
                        # N19.x = Chronic kidney disease, unspecified
                        if code.startswith('N18') or code.startswith('N19'):
                            patient_data['has_ckd'] = True
                            patient_data['ckd_stage'] = 3  # Default to stage 3 if CKD diagnosis exists
                            break

        # Parse gender from user_input as fallback (agent doesn't extract gender)
        if 'user_input' in input_data and input_data['user_input']:
            user_text = input_data['user_input']
            # Extract gender from user input
            if any(word in user_text for word in ['男性', '男', 'male', '先生', '他']):
                patient_data['gender'] = 'male'
            elif any(word in user_text for word in ['女性', '女', 'female', '女士', '她']):
                patient_data['gender'] = 'female'

            # Also parse other natural language data to fill missing fields
            natural_data = self._parse_natural_text(user_text)
            for key, value in natural_data.items():
                if key not in patient_data or patient_data[key] is None:
                    patient_data[key] = value

        return patient_data

    def _flatten_health_metrics_format(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten health_metrics format to flat patient data

        Input: {"patient_info": {"age": 45, "gender": "male"},
                "health_metrics": {"blood_pressure": {"systolic": 185, "diastolic": 105}}}
        Output: {"age": 45, "gender": "male", "sbp": 185, "dbp": 105}
        """
        patient_data = {}

        # Extract from patient_info
        if 'patient_info' in input_data:
            pi = input_data['patient_info']
            age = pi.get('age')
            # Convert age to int if it's a string
            if age is not None:
                try:
                    patient_data['age'] = int(age)
                except (ValueError, TypeError):
                    patient_data['age'] = age
            patient_data['gender'] = pi.get('gender')

        # Extract from health_metrics
        if 'health_metrics' in input_data:
            hm = input_data['health_metrics']

            # Blood pressure
            if 'blood_pressure' in hm:
                bp = hm['blood_pressure']
                patient_data['sbp'] = bp.get('systolic')
                patient_data['dbp'] = bp.get('diastolic')

            # Blood glucose
            if 'blood_glucose' in hm:
                bg = hm['blood_glucose']
                patient_data['fasting_glucose'] = bg.get('fasting')
                patient_data['hba1c'] = bg.get('hba1c')

            # Blood lipids
            if 'blood_lipid' in hm:
                bl = hm['blood_lipid']
                patient_data['tc'] = bl.get('tc')
                patient_data['tg'] = bl.get('tg')
                patient_data['ldl_c'] = bl.get('ldl_c')
                patient_data['hdl_c'] = bl.get('hdl_c')

            # Uric acid
            if 'uric_acid' in hm:
                patient_data['uric_acid'] = hm['uric_acid']

            # BMI
            if 'bmi' in hm:
                bmi_data = hm['bmi']
                if isinstance(bmi_data, dict):
                    patient_data['bmi'] = bmi_data.get('value')
                    patient_data['waist_circumference'] = bmi_data.get('waist_circumference')
                else:
                    patient_data['bmi'] = bmi_data

            # Basic info (height, weight, waist)
            if 'basic' in hm:
                basic = hm['basic']
                if 'height' in basic:
                    patient_data['height'] = basic['height']
                if 'weight' in basic:
                    patient_data['weight'] = basic['weight']
                if 'waist_circumference' in basic:
                    patient_data['waist_circumference'] = basic['waist_circumference']

        # Parse gender and other data from user_input if not already set
        if 'user_input' in input_data and input_data['user_input']:
            user_text = input_data['user_input']
            if not patient_data.get('gender'):
                # Extract gender from user input
                if any(word in user_text for word in ['男性', '男', 'male', '先生', '他']):
                    patient_data['gender'] = 'male'
                elif any(word in user_text for word in ['女性', '女', 'female', '女士', '她']):
                    patient_data['gender'] = 'female'

            # Also parse other natural language data to fill missing fields (age, BP, etc.)
            natural_data = self._parse_natural_text(user_text)
            for key, value in natural_data.items():
                if key not in patient_data or patient_data[key] is None:
                    patient_data[key] = value

        return patient_data

    def _parse_natural_text(self, text: str) -> Dict[str, Any]:
        """
        Extract patient data from natural text description

        Example: "45岁男性，血压185/105，有糖尿病，吸烟"
        Also handles: "45yo male BP 185/105", "45 male BP 185/105"
        """
        patient_data = {}

        # Extract age (support both Chinese and English formats)
        # Try specific patterns first
        age_patterns = [
            r'(\d+)\s*岁',  # 45岁
            r'(\d+)\s*yo\b',  # 45yo (word boundary)
            r'(\d+)\s*year[s]?\s*old',  # 45 years old
            r'age\s*[:：]?\s*(\d+)',  # age: 45
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, text, re.IGNORECASE)
            if age_match:
                patient_data['age'] = int(age_match.group(1))
                break

        # If no age found yet, try to extract a number that's likely an age
        # Look for numbers between 1-120 that appear near gender keywords
        if 'age' not in patient_data:
            # Pattern: number followed by gender indicator
            age_context_patterns = [
                r'(\d{2})\s*(?:岁|yo|year)?\s*(?:男|女|male|female|先生|女士)',
                r'(?:男|女|male|female|先生|女士)\s*(?:岁|yo|year)?\s*(\d{2})',
            ]
            for pattern in age_context_patterns:
                age_match = re.search(pattern, text, re.IGNORECASE)
                if age_match:
                    # Try both groups as some patterns have different group order
                    for group in age_match.groups():
                        if group and 1 < int(group) < 120:
                            patient_data['age'] = int(group)
                            break
                    if 'age' in patient_data:
                        break

        # Extract gender
        if any(word in text for word in ['男性', '男', 'male', '先生']):
            patient_data['gender'] = 'male'
        elif any(word in text for word in ['女性', '女', 'female', '女士']):
            patient_data['gender'] = 'female'

        # Extract blood pressure (patterns: 185/105, 185-105, BP 185/105, 收缩压185舒张压105)
        bp_patterns = [
            r'BP\s*[:：]?\s*(\d{2,3})[\/\-](\d{2,3})',  # BP 185/105
            r'(\d{2,3})[\/\-](\d{2,3})',  # 185/105 or 185-105
            r'收缩压\s*(\d{2,3})[^\d]*舒张压\s*(\d{2,3})',  # 收缩压185舒张压105
            r'血压\s*[:：]?\s*(\d{2,3})[\/\-](\d{2,3})',  # 血压:185/105
        ]
        for pattern in bp_patterns:
            bp_match = re.search(pattern, text, re.IGNORECASE)
            if bp_match:
                patient_data['sbp'] = int(bp_match.group(1))
                patient_data['dbp'] = int(bp_match.group(2))
                break

        # Extract diabetes status
        if any(word in text for word in ['糖尿病', 'dm', 'diabetes', '有糖尿病']):
            patient_data['has_diabetes'] = True

        # Extract smoking status
        if any(word in text for word in ['吸烟', '抽烟', 'smoke', 'smoker', '吸烟者']):
            patient_data['smoker'] = True

        # Extract BMI if present
        bmi_match = re.search(r'bmi\s*[:：]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
        if bmi_match:
            patient_data['bmi'] = float(bmi_match.group(1))

        # Extract LDL-C
        ldl_patterns = [
            r'ldl[\/\-c]*\s*[:：]?\s*(\d+\.?\d*)',
            r'低密度脂蛋白\s*[:：]?\s*(\d+\.?\d*)',
        ]
        for pattern in ldl_patterns:
            ldl_match = re.search(pattern, text, re.IGNORECASE)
            if ldl_match:
                patient_data['ldl_c'] = float(ldl_match.group(1))
                break

        return patient_data

    def validate_patient_data(self, patient_data: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Check required fields and return validation result

        Returns:
            (is_valid, missing_fields)
        """
        missing_fields = []

        # Required fields - age is mandatory, gender is optional (will use default)
        age = patient_data.get('age')
        if age is None or (isinstance(age, str) and not age.strip()):
            missing_fields.append('age')

        # Note: Gender is optional - if missing, will use conservative default (female)
        # This allows partial assessment when gender is not available

        return len(missing_fields) == 0, missing_fields

    def patient_dict_to_dataclass(self, patient_dict: Dict[str, Any]) -> PatientData:
        """Convert dict to PatientData dataclass"""
        # Normalize gender - use conservative default (female) if missing
        gender = patient_dict.get('gender')
        if gender:
            if gender in ['男', '男性', 'male']:
                gender = 'male'
            elif gender in ['女', '女性', 'female']:
                gender = 'female'
            else:
                gender = 'female'  # Default to female (conservative - higher age threshold)
        else:
            gender = 'female'  # Default to female (conservative - higher age threshold)

        # Calculate non-HDL-C if not provided (non-HDL-C = TC - HDL-C)
        non_hdl_c = patient_dict.get('non_hdl_c')
        if non_hdl_c is None:
            tc = patient_dict.get('tc')
            hdl_c = patient_dict.get('hdl_c')
            if tc is not None and hdl_c is not None:
                non_hdl_c = tc - hdl_c

        return PatientData(
            age=patient_dict.get('age'),
            gender=gender,
            sbp=patient_dict.get('sbp'),
            dbp=patient_dict.get('dbp'),
            ldl_c=patient_dict.get('ldl_c'),
            tc=patient_dict.get('tc'),
            hdl_c=patient_dict.get('hdl_c'),
            non_hdl_c=non_hdl_c,
            tg=patient_dict.get('tg'),
            has_diabetes=patient_dict.get('has_diabetes', False),
            diabetes_with_organ_damage=patient_dict.get('diabetes_with_organ_damage', False),
            smoker=patient_dict.get('smoker', False),
            bmi=patient_dict.get('bmi'),
            waist_circumference=patient_dict.get('waist_circumference'),
            family_history_premature_cvd=patient_dict.get('family_history_premature_cvd', False),
            has_ckd=patient_dict.get('has_ckd', False),
            ckd_stage=patient_dict.get('ckd_stage'),
            has_established_cvd=patient_dict.get('has_established_cvd', False)
        )

    def generate_risk_report(self, result: RiskAssessmentResult) -> Dict[str, Any]:
        """Format output for agent consumption"""
        return {
            "risk_category": result.risk_category.value,
            "risk_category_zh": self._get_category_zh(result.risk_category),
            "risk_factors_count": result.risk_factors_count,
            "key_factors": result.key_factors,
            "follow_up_interval": result.follow_up_interval
        }

    def _get_category_zh(self, category: RiskCategory) -> str:
        """Get Chinese name for risk category"""
        mapping = {
            RiskCategory.LOW: "低危",
            RiskCategory.MEDIUM: "中危",
            RiskCategory.HIGH: "高危",
            RiskCategory.VERY_HIGH: "很高危"
        }
        return mapping.get(category, "")

    def assess(self, input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main assessment function

        Args:
            input_data: Patient data in various formats

        Returns:
            JSON output with risk assessment results in agent-expected format
        """
        # Extract patient data
        patient_dict = self.extract_patient_data(input_data)

        # Validate required fields
        is_valid, missing_fields = self.validate_patient_data(patient_dict)

        if not is_valid:
            # Return incomplete status in agent-expected format
            return {
                "success": False,
                "status": "incomplete",
                "message": "Missing required patient data",
                "required_fields": missing_fields,
                "provided_data": patient_dict
            }

        # Check if gender was defaulted
        gender_defaulted = not patient_dict.get('gender')

        # Convert to dataclass and calculate risk
        patient = self.patient_dict_to_dataclass(patient_dict)
        result = self.calculator.calculate_risk(patient)

        # Generate report
        risk_report = self.generate_risk_report(result)

        # Add note if gender was defaulted
        if gender_defaulted:
            risk_report['_note'] = 'Gender not provided - using conservative default (female) for risk calculation. For accurate assessment, please provide gender.'

        # Return in agent-expected format with modules directly in final_output
        # This allows ms_agent_executor.py to extract and format the result correctly
        modules = self._format_modules_output(result, patient)
        return {
            "success": True,
            "status": "completed",
            "skill_name": "cvd-risk-assessment",
            "final_output": {
                "modules": modules,
                "total_modules": len(modules)
            },
            "risk_assessment": risk_report,
            "patient_data": {
                "age": patient.age,
                "gender": patient.gender
            }
        }

    def _format_modules_output(self, result: RiskAssessmentResult, patient: PatientData) -> Dict[str, Any]:
        """Format output in modules structure for agent consumption"""
        category_zh = self._get_category_zh(result.risk_category)
        factors = result.key_factors

        # 生成健康洞察
        health_insight = self._generate_health_insight(result, patient)

        # Build modules structure with risk assessment and health insight
        modules = {
            "risk_assessment": {
                "risk_level": result.risk_category.value,
                "risk_level_zh": category_zh,
                "risk_factors_count": result.risk_factors_count,
                "key_factors": factors,
                "follow_up": result.follow_up_interval,
                "assessment_path": result.assessment_path
            },
            "health_insight": health_insight
        }

        # 添加10年风险信息
        if result.ten_year_risk:
            modules["risk_assessment"]["ten_year_risk"] = result.ten_year_risk
            modules["risk_assessment"]["ten_year_risk_zh"] = self._get_category_zh_by_value(result.ten_year_risk)

        # 添加10年风险范围信息
        if result.ten_year_risk_range:
            modules["risk_assessment"]["ten_year_risk_range"] = result.ten_year_risk_range

        # 添加10年心血管病发病风险信息
        if result.ten_year_cvd_risk:
            modules["risk_assessment"]["ten_year_cvd_risk"] = result.ten_year_cvd_risk
        if result.ten_year_cvd_risk_zh:
            modules["risk_assessment"]["ten_year_cvd_risk_zh"] = result.ten_year_cvd_risk_zh

        # 添加余生风险信息
        if result.lifetime_risk:
            modules["risk_assessment"]["lifetime_risk"] = result.lifetime_risk
            modules["risk_assessment"]["lifetime_risk_zh"] = "高危" if result.lifetime_risk == "high" else "低危"

        return modules

    def _generate_health_insight(self, result: RiskAssessmentResult, patient: PatientData) -> str:
        """
        生成健康洞察

        基于风险评估结果提供个性化的健康建议和解读
        """
        insights = []

        # 风险等级解读
        risk_map = {
            "low": "您的当前心血管健康状况良好，风险较低",
            "medium": "您的存在一定心血管风险，建议关注危险因素",
            "high": "您的心血管风险较高，需要积极干预",
            "very_high": "您处于很高危状态，需要立即关注"
        }

        base_insight = risk_map.get(result.risk_category.value, "")
        if base_insight:
            insights.append(f"**风险解读**: {base_insight}")

        # 根据评估路径给出建议
        if result.assessment_path == "initial_high":
            insights.append("**评估说明**: 您存在严重的心血管危险因素，已被直接判定为高危人群")
        elif result.assessment_path == "ten_year_risk":
            if result.ten_year_risk == "low":
                insights.append("**评估说明**: 通过10年ASCVD风险评估，您的心血管病发病风险较低")
            elif result.ten_year_risk == "medium":
                insights.append("**评估说明**: 通过10年ASCVD风险评估，您的心血管病发病风险处于中等水平")
            else:
                insights.append("**评估说明**: 通过10年ASCVD风险评估，您的心血管病发病风险较高")
        elif result.assessment_path == "lifetime_high":
            insights.append("**评估说明**: 您的10年风险虽非高危，但余生风险较高，需要长期管理")

        # 根据危险因素给出针对性建议
        if result.key_factors:
            factor_tips = {
                "高血压": "控制血压在正常范围（<140/90 mmHg）是预防心血管病的关键",
                "年龄≥45岁": "年龄是心血管病的不可控风险因素，更需要关注可控因素",
                "吸烟": "戒烟是降低心血管风险最有效的方法之一",
                "HDL-C低": "提高HDL-C（好胆固醇）可通过规律运动和健康饮食实现",
                "肥胖（BMI≥28": "控制体重可显著改善心血管健康",
                "收缩压极高（≥160": "血压显著升高增加了心血管事件风险，需要立即关注",
                "舒张压极高（≥100": "血压显著升高增加了心血管事件风险，需要立即关注",
                "非HDL-C极高（≥5.2": "非HDL-C包含了所有致动脉粥样硬化的胆固醇，需要严格控制",
                "LDL-C重度升高": "LDL-C是动脉粥样硬化的主要致病因素，需要强化降脂治疗"
            }

            for factor in result.key_factors:
                factor_key = factor.split("（")[0] if "（" in factor else factor
                if factor_key in factor_tips:
                    insights.append(f"**{factor}**: {factor_tips[factor_key]}")
                    break  # 只给出第一个主要因素的建议，避免过长

        return "\n\n".join(insights) if insights else "暂无特殊健康洞察"

    def _get_category_zh_by_value(self, value: str) -> str:
        """Get Chinese name for risk category by value"""
        mapping = {
            "low": "低危",
            "medium": "中危",
            "high": "高危",
            "very_high": "很高危"
        }
        return mapping.get(value, "")

    def assess_with_skill_output(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """
        Generate formatted output for skill execution

        Returns formatted markdown text for agent response
        """
        result = self.assess(input_data)

        if not result.get("success"):
            missing = result.get("required_fields", [])
            missing_zh = {
                "age": "年龄",
                "gender": "性别"
            }
            missing_list = [missing_zh.get(f, f) for f in missing]

            return f"""# 心血管风险评估

⚠️ **数据不完整**

为了进行心血管风险评估，需要补充以下信息：
- {chr(10).join(f'- {m}' for m in missing_list)}

当前已提供的数据：{result.get("provided_data", {})}
"""

        # Generate formatted report
        report = result["risk_assessment"]
        category_zh = report["risk_category_zh"]
        factors = report["key_factors"]

        factor_list = "\n".join(f"- {f}" for f in factors)

        return f"""# 心血管风险评估

## 风险等级: {category_zh}

### 识别的危险因素 ({report["risk_factors_count"]}个)
{factor_list if factors else "- 无明显危险因素"}

### 随访间隔
{report["follow_up_interval"]}
"""


def main():
    """CLI entry point"""
    # UTF-8 encoding fix for Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(
        description='Cardiovascular Disease Risk Assessment'
    )
    parser.add_argument(
        '--input',
        help='Input file path (JSON) or natural text description'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON format instead of human-readable text'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode for manual data entry'
    )
    parser.add_argument(
        '--mode',
        default='standalone',
        choices=['standalone', 'skill'],
        help='Running mode: standalone or skill integration'
    )

    args = parser.parse_args()

    executor = CVDAssessmentExecutor()

    # Skill mode: read from --input file or stdin JSON
    if args.mode == 'skill':
        # Try to read from --input file first, fallback to stdin
        input_data = None
        if args.input:
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IOError):
                pass

        # If --input not provided or failed, try stdin
        if input_data is None:
            try:
                input_data = json.load(sys.stdin)
            except (json.JSONDecodeError, IOError):
                result = {
                    "success": False,
                    "error": "Invalid JSON input"
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1

        assessment_result = executor.assess(input_data)

        # Add skill name for routing
        assessment_result["skill_name"] = "cvd-risk-assessment"

        print(json.dumps(assessment_result, ensure_ascii=False, indent=2))
        return 0 if assessment_result["success"] else 1

    # Interactive mode
    if args.interactive:
        print("=== 心血管风险评估 (交互式) ===\n")

        try:
            age = int(input("请输入年龄: "))
            gender_input = input("请输入性别 (男/女): ").strip()
            gender = "male" if gender_input in ["男", "男性", "male", "m"] else "female"

            patient_data = {"age": age, "gender": gender}

            # Optional fields
            sbp_input = input("收缩压 (mmHg，可选): ").strip()
            if sbp_input:
                patient_data["sbp"] = int(sbp_input)

            dbp_input = input("舒张压 (mmHg，可选): ").strip()
            if dbp_input:
                patient_data["dbp"] = int(dbp_input)

            ldl_input = input("LDL-C (mmol/L，可选): ").strip()
            if ldl_input:
                patient_data["ldl_c"] = float(ldl_input)

            diabetes_input = input("是否有糖尿病 (是/否，可选): ").strip()
            if diabetes_input in ["是", "yes", "y"]:
                patient_data["has_diabetes"] = True

            smoker_input = input("是否吸烟 (是/否，可选): ").strip()
            if smoker_input in ["是", "yes", "y"]:
                patient_data["smoker"] = True

            bmi_input = input("BMI (可选): ").strip()
            if bmi_input:
                patient_data["bmi"] = float(bmi_input)

            result = executor.assess(patient_data)

            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("\n" + executor.assess_with_skill_output(patient_data))

            return 0

        except (ValueError, KeyboardInterrupt) as e:
            print(f"\n错误: {e}")
            return 1

    # File input mode
    if args.input:
        result = executor.assess(args.input)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(executor.assess_with_skill_output(args.input))

        return 0 if result["success"] else 1

    # No input provided
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
