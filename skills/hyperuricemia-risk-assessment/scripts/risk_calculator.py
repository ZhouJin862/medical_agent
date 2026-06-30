#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高尿酸风险评估计算脚本

功能：
1. 尿酸水平评估
2. 痛风风险预测
3. 肾功能评估
4. 代谢综合征评估
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple


class HyperuricemiaRiskCalculator:
    """高尿酸风险评估计算器"""
    
    # 尿酸水平分类标准（《中国高尿酸血症与痛风诊疗指南2019》）
    URIC_ACID_LEVELS = {
        'male': {'normal': (208, 416), 'elevated': (417, 999)},
        'female': {'normal': (155, 357), 'elevated': (358, 999)}
    }
    
    # 评估标准来源
    STANDARD_SOURCE = {
        'standard': '《中国高尿酸血症与痛风诊疗指南2019》',
        'organization': '中华医学会内分泌学分会',
        'type': '行业标准'
    }
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行高尿酸风险评估"""
        self.results = {
            'patient_info': data.get('patient_info', {}),
            'assessment_date': datetime.now().strftime('%Y-%m-%d'),
            'assessment_type': 'hyperuricemia',
            'standard': self.STANDARD_SOURCE
        }
        
        metrics = data.get('health_metrics', {})
        
        # 1. 尿酸水平评估
        uric_acid_assessment = self._assess_uric_acid(metrics, data)
        self.results['uric_acid_assessment'] = uric_acid_assessment
        
        # 2. 痛风风险评估
        gout_risk = self._assess_gout_risk(data, uric_acid_assessment)
        self.results['gout_risk'] = gout_risk
        
        # 3. 肾功能评估
        kidney_assessment = self._assess_kidney(metrics)
        self.results['kidney_assessment'] = kidney_assessment
        
        # 4. 代谢综合征评估
        metabolic_syndrome = self._assess_metabolic_syndrome(data)
        self.results['metabolic_syndrome'] = metabolic_syndrome
        
        # 5. 综合风险评估
        overall_risk = self._overall_risk_assessment(uric_acid_assessment, gout_risk, kidney_assessment)
        self.results['overall_risk'] = overall_risk
        
        return self.results
    
    def _assess_uric_acid(self, metrics: Dict, data: Dict) -> Dict:
        """评估尿酸水平"""
        uric_acid = metrics.get('uric_acid', 0)
        gender = data.get('patient_info', {}).get('gender', 'male')
        is_male = gender in ['male', '男']
        
        gender_key = 'male' if is_male else 'female'
        normal_range = self.URIC_ACID_LEVELS[gender_key]['normal']
        
        is_elevated = uric_acid > normal_range[1]
        
        return {
            'value': uric_acid,
            'gender': gender_key,
            'normal_range': f'{normal_range[0]}-{normal_range[1]}',
            'is_elevated': is_elevated,
            'level': '高尿酸血症' if is_elevated else '正常'
        }
    
    def _assess_gout_risk(self, data: Dict, ua: Dict) -> Dict:
        """评估痛风风险"""
        uric_acid = ua['value']
        
        # 基于尿酸水平的痛风年发生率
        if uric_acid < 420:
            annual_risk = 0.1
        elif uric_acid < 480:
            annual_risk = 0.4
        elif uric_acid < 540:
            annual_risk = 0.8
        elif uric_acid < 600:
            annual_risk = 4.3
        else:
            annual_risk = 7.0
        
        # 风险等级
        if uric_acid >= 600:
            risk_level = '高风险'
        elif uric_acid >= 480:
            risk_level = '中风险'
        else:
            risk_level = '低风险'
        
        return {
            'annual_gout_risk': f'{annual_risk}%',
            'risk_level': risk_level,
            'recommendation': self._get_gout_recommendation(uric_acid)
        }
    
    def _get_gout_recommendation(self, uric_acid: float) -> str:
        """获取痛风预防建议"""
        if uric_acid >= 540:
            return '尿酸水平较高，建议降尿酸治疗'
        elif uric_acid >= 420:
            return '建议低嘌呤饮食，定期监测尿酸'
        else:
            return '尿酸水平正常，保持健康生活方式'
    
    def _assess_kidney(self, metrics: Dict) -> Dict:
        """评估肾功能"""
        kidney = metrics.get('kidney', {})
        egfr = kidney.get('egfr', 100)
        uacr = kidney.get('uacr', 0)
        creatinine = kidney.get('serum_creatinine', 0)
        
        # eGFR分期
        if egfr >= 90:
            gfr_stage = 'G1 (正常)'
        elif egfr >= 60:
            gfr_stage = 'G2 (轻度下降)'
        elif egfr >= 45:
            gfr_stage = 'G3a (轻中度下降)'
        elif egfr >= 30:
            gfr_stage = 'G3b (中重度下降)'
        elif egfr >= 15:
            gfr_stage = 'G4 (重度下降)'
        else:
            gfr_stage = 'G5 (肾衰竭)'
        
        # UACR评估
        if uacr < 30:
            albuminuria = '正常'
        elif uacr < 300:
            albuminuria = '微量白蛋白尿'
        else:
            albuminuria = '大量白蛋白尿'
        
        return {
            'egfr': egfr,
            'gfr_stage': gfr_stage,
            'uacr': uacr,
            'albuminuria': albuminuria,
            'creatinine': creatinine,
            'has_kidney_damage': egfr < 60 or uacr > 30
        }
    
    def _assess_metabolic_syndrome(self, data: Dict) -> Dict:
        """评估代谢综合征"""
        criteria = []
        metrics = data.get('health_metrics', {})
        patient = data.get('patient_info', {})
        
        # 1. 中心型肥胖
        waist = patient.get('waist', 0)
        gender = patient.get('gender', 'male')
        waist_threshold = 90 if gender in ['male', '男'] else 85
        if waist >= waist_threshold:
            criteria.append({'criterion': '中心型肥胖', 'value': f'腰围{waist}cm'})
        
        # 2. 高血糖
        fasting = metrics.get('blood_glucose', {}).get('fasting', 0)
        if fasting >= 6.1:
            criteria.append({'criterion': '高血糖', 'value': f'空腹血糖{fasting}mmol/L'})
        
        # 3. 高血压
        bp = metrics.get('blood_pressure', {})
        if bp.get('systolic', 0) >= 130 or bp.get('diastolic', 0) >= 85:
            criteria.append({'criterion': '高血压', 'value': f"血压{bp.get('systolic', 0)}/{bp.get('diastolic', 0)}mmHg"})
        
        # 4. 高甘油三酯
        tg = metrics.get('blood_lipid', {}).get('tg', 0)
        if tg >= 1.7:
            criteria.append({'criterion': '高甘油三酯', 'value': f'TG={tg}mmol/L'})
        
        # 5. 低HDL-C
        hdl_c = metrics.get('blood_lipid', {}).get('hdl_c', 0)
        hdl_threshold = 1.04 if gender in ['male', '男'] else 1.30
        if hdl_c < hdl_threshold:
            criteria.append({'criterion': '低HDL-C', 'value': f'HDL-C={hdl_c}mmol/L'})
        
        has_metabolic_syndrome = len(criteria) >= 3
        
        return {
            'has_metabolic_syndrome': has_metabolic_syndrome,
            'criteria_count': len(criteria),
            'criteria': criteria,
            'summary': f'满足{len(criteria)}项代谢综合征标准' if criteria else '不满足代谢综合征诊断'
        }
    
    def _overall_risk_assessment(self, ua: Dict, gout: Dict, kidney: Dict) -> Dict:
        """综合风险评估"""
        risk_factors = []
        
        if ua['is_elevated']:
            risk_factors.append('高尿酸血症')
        
        if kidney['has_kidney_damage']:
            risk_factors.append('肾功能损害')
        
        if gout['risk_level'] == '高风险':
            risk_factors.append('痛风高风险')
        
        if len(risk_factors) >= 2:
            risk_level = '高风险'
        elif len(risk_factors) == 1:
            risk_level = '中风险'
        else:
            risk_level = '低风险'
        
        return {
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'uric_acid_target': self._get_ua_target(gout['risk_level']),
            'recommendation': self._get_overall_recommendation(risk_level, ua['is_elevated'])
        }
    
    def _get_ua_target(self, gout_risk: str) -> str:
        """获取尿酸控制目标"""
        if gout_risk == '高风险':
            return '<300μmol/L'
        else:
            return '<360μmol/L'
    
    def _get_overall_recommendation(self, risk_level: str, has_hua: bool) -> str:
        """获取综合建议"""
        if risk_level == '高风险':
            return '建议积极降尿酸治疗，定期监测肾功能'
        elif has_hua:
            return '建议低嘌呤饮食，限制饮酒，定期随访'
        else:
            return '保持健康生活方式，定期监测尿酸'




def _build_structured_result(risk_data, overall_risk, health_metrics, input_data):
    """Build structured result for unified assessment JSON schema."""
    risk_grade = overall_risk.get('risk_grade', '') or overall_risk.get('risk_level', '')
    category = _map_risk_to_category(risk_grade)

    # 1. Population classification
    primary = "健康"
    if "高危" in risk_grade or "很高危" in risk_grade:
        primary = "重症"
    elif "中危" in risk_grade or "中" in risk_grade:
        primary = "慢病"
    elif "低" in risk_grade:
        primary = "亚健康"

    # Grouping basis
    disease_risks = []
    ua = risk_data.get('uric_acid')
    if ua:
        try:
            uv = float(ua)
            if uv >= 600:
                disease_risks.append("重度高尿酸血症")
            elif uv >= 480:
                disease_risks.append("高尿酸血症")
            elif uv >= 420:
                disease_risks.append("高尿酸血症（临界）")
        except (ValueError, TypeError):
            pass
    if risk_data.get('has_gout'):
        disease_risks.append("痛风")

    disease_staging = ""
    if ua:
        try:
            uv = float(ua)
            if uv >= 600:
                disease_staging = "重度高尿酸血症"
            elif uv >= 480:
                disease_staging = "高尿酸血症"
            elif uv >= 420:
                disease_staging = "高尿酸血症（临界）"
        except (ValueError, TypeError):
            pass

    disease_name = "痛风" if risk_data.get('has_gout') else "高尿酸"
    population_classification = {
        "primary_category": primary,
        "grouping_basis": [{
            "disease": disease_name,
            "type": disease_staging or "",
            "level": risk_grade or "",
            "note": f"{disease_staging}{risk_grade or ''}" if disease_staging else (risk_grade or ""),
        }],
    }

    # 2. Recommended data collection (check for missing vitals)
    recommended = []
    if not risk_data.get('uric_acid'):
        recommended.append({"item": "血尿酸", "reason": "缺少血尿酸数据"})
    kidney = input_data.get('kidney_assessment', {})
    if not kidney.get('egfr'):
        recommended.append({"item": "肾功能检查(eGFR)", "reason": "需要评估肾功能状况"})
    gout = input_data.get('gout_risk', {})
    if not gout.get('risk_level'):
        recommended.append({"item": "痛风风险评估", "reason": "需要评估痛风风险"})

    # 3. Abnormal indicators
    abnormal = []
    ua_val = risk_data.get('uric_acid')
    if ua_val:
        try:
            uv = float(ua_val)
            if uv >= 420:
                abnormal.append({"indicator": "血尿酸", "value": f"{ua_val} μmol/L", "reference": "<420 μmol/L(男)，<360 μmol/L(女)"})
        except (ValueError, TypeError):
            pass

    # 4. Disease prediction
    disease_prediction = []
    is_elevated = input_data.get('uric_acid_assessment', {}).get('is_elevated', False)
    if is_elevated:
        disease_prediction.append({"disease": "痛风", "risk": "高", "description": "高尿酸血症是痛风的重要危险因素"})
        disease_prediction.append({"disease": "尿酸性肾病", "risk": "中高", "description": "长期高尿酸可导致肾脏损害"})
    gout_risk_level = risk_data.get('gout_risk_level', '')
    if gout_risk_level in ('高', '很高'):
        disease_prediction.append({"disease": "急性痛风发作", "risk": "高", "description": "近期痛风发作风险较高"})

    # risk_warnings and intervention_prescriptions are generated by
    # dedicated LLM skills (risk-warning / prescription-recommendation) in Phase 3.5,
    # so scripts only output empty placeholders here.
    return {
        "population_classification": population_classification,
        "recommended_data_collection": recommended,
        "abnormal_indicators": abnormal,
        "disease_prediction": disease_prediction,
        "intervention_prescriptions": [],
        "risk_warnings": [],
    }


def _map_risk_to_category(risk_grade):
    if not risk_grade:
        return "健康"
    grade = risk_grade.lower()
    if "很高危" in grade or "极高" in grade:
        return "重症"
    if "高危" in grade or "高" in grade:
        return "慢病"
    if "中危" in grade or "中" in grade:
        return "亚健康"
    return "健康"


def run(input_data: dict) -> dict:
    """Standard function interface for skill executor."""
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
    from data_format_adapter import adapt_agent_format
    adapted = adapt_agent_format(input_data)
    calculator = HyperuricemiaRiskCalculator()
    results = calculator.calculate(adapted)
    overall_risk = results.get('risk_stratification', {})
    health_metrics = results.get('cardiovascular_risk', {})
    structured_result = _build_structured_result(results, overall_risk, health_metrics, adapted)
    results['structured_result'] = structured_result
    return results


def main():
    # UTF-8 encoding fix for Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    parser = argparse.ArgumentParser(description='高尿酸风险评估计算')
    parser.add_argument('--input', required=True, help='输入验证后的健康数据文件路径')
    parser.add_argument('--output', default='hyperuricemia_risk.json', help='输出风险评估文件路径')
    
    args = parser.parse_args()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件不存在 {args.input}")
        return 1
    except json.JSONDecodeError:
        print(f"错误: JSON格式错误 {args.input}")
        return 1
    
    calculator = HyperuricemiaRiskCalculator()
    results = calculator.calculate(data)
    
    # 保存结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Human-readable output to stderr (for logging)
    print(f"尿酸水平: {results['uric_acid_assessment']['value']} μmol/L ({results['uric_acid_assessment']['level']})", file=sys.stderr)
    print(f"风险等级: {results['overall_risk']['risk_level']}", file=sys.stderr)

    # JSON output to stdout only (for pipeline)
    # Build structured_result (merged from template_manager)
    overall_risk = results.get('risk_stratification', {})
    health_metrics = results.get('cardiovascular_risk', {})
    structured_result = _build_structured_result(results, overall_risk, health_metrics, data)
    results['structured_result'] = structured_result

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
