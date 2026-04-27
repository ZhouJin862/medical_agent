#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
肥胖风险评估计算脚本

功能：
1. BMI评估与分级
2. 中心型肥胖评估
3. 代谢综合征评估
4. 肥胖相关疾病风险评估
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple


class ObesityRiskCalculator:
    """肥胖风险评估计算器"""
    
    # BMI分类标准（《中国成人超重和肥胖症预防控制指南》）
    BMI_LEVELS = {
        'underweight': {'range': (0, 18.4), 'level': '体重过低', 'score': 2},
        'normal': {'range': (18.5, 23.9), 'level': '正常', 'score': 1},
        'overweight': {'range': (24.0, 27.9), 'level': '超重', 'score': 2},
        'obesity_1': {'range': (28.0, 32.9), 'level': '肥胖I级', 'score': 3},
        'obesity_2': {'range': (33.0, 37.9), 'level': '肥胖II级', 'score': 4},
        'obesity_3': {'range': (38.0, 999), 'level': '肥胖III级', 'score': 5}
    }
    
    # 腰围标准
    WAIST_STANDARDS = {
        'male': {'normal': 85, 'elevated': 90},
        'female': {'normal': 80, 'elevated': 85}
    }
    
    # 评估标准来源
    STANDARD_SOURCE = {
        'standard': '《中国成人超重和肥胖症预防控制指南》',
        'organization': '中国营养学会',
        'type': '国家标准'
    }
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行肥胖风险评估"""
        self.results = {
            'patient_info': data.get('patient_info', {}),
            'assessment_date': datetime.now().strftime('%Y-%m-%d'),
            'assessment_type': 'obesity',
            'standard': self.STANDARD_SOURCE
        }
        
        metrics = data.get('health_metrics', {})
        
        # 1. BMI评估
        bmi_assessment = self._assess_bmi(metrics, data)
        self.results['bmi_assessment'] = bmi_assessment
        
        # 2. 中心型肥胖评估
        central_obesity = self._assess_central_obesity(data)
        self.results['central_obesity'] = central_obesity
        
        # 3. 代谢综合征评估
        metabolic_syndrome = self._assess_metabolic_syndrome(data)
        self.results['metabolic_syndrome'] = metabolic_syndrome
        
        # 4. 体脂评估（如有数据）
        body_fat = self._assess_body_fat(data)
        self.results['body_fat'] = body_fat
        
        # 5. 肥胖相关疾病风险
        related_diseases = self._assess_related_diseases(data, bmi_assessment)
        self.results['related_diseases'] = related_diseases
        
        # 6. 综合风险评估
        overall_risk = self._overall_risk_assessment(bmi_assessment, central_obesity, metabolic_syndrome)
        self.results['overall_risk'] = overall_risk
        
        return self.results
    
    def _assess_bmi(self, metrics: Dict, data: Dict) -> Dict:
        """评估BMI"""
        bmi_data = metrics.get('bmi', {})
        
        # 获取BMI值
        if isinstance(bmi_data, dict):
            bmi_value = bmi_data.get('value', 0)
            height = bmi_data.get('height', 0)
            weight = bmi_data.get('weight', 0)
            
            # 如果没有BMI值但有身高体重，则计算
            if bmi_value == 0 and height > 0 and weight > 0:
                # 身高单位可能是cm
                if height > 3:
                    height = height / 100
                bmi_value = weight / (height ** 2)
        else:
            bmi_value = bmi_data
            height = 0
            weight = 0
        
        # 确定BMI级别
        level = 'normal'
        level_info = self.BMI_LEVELS['normal']
        
        for key, info in self.BMI_LEVELS.items():
            if info['range'][0] <= bmi_value <= info['range'][1]:
                level = key
                level_info = info
                break
        
        return {
            'value': round(bmi_value, 2),
            'level': level_info['level'],
            'level_code': level,
            'score': level_info['score'],
            'height': height,
            'weight': weight
        }
    
    def _assess_central_obesity(self, data: Dict) -> Dict:
        """评估中心型肥胖"""
        patient = data.get('patient_info', {})
        gender = patient.get('gender', 'male')
        is_male = gender in ['male', '男']
        
        waist = patient.get('waist', 0)
        
        gender_key = 'male' if is_male else 'female'
        normal_threshold = self.WAIST_STANDARDS[gender_key]['normal']
        elevated_threshold = self.WAIST_STANDARDS[gender_key]['elevated']
        
        if waist >= elevated_threshold:
            level = '中心型肥胖'
            score = 3
        elif waist >= normal_threshold:
            level = '腰围超标'
            score = 2
        else:
            level = '正常'
            score = 1
        
        return {
            'waist': waist,
            'gender': gender_key,
            'normal_threshold': normal_threshold,
            'elevated_threshold': elevated_threshold,
            'level': level,
            'score': score
        }
    
    def _assess_metabolic_syndrome(self, data: Dict) -> Dict:
        """评估代谢综合征"""
        criteria = []
        metrics = data.get('health_metrics', {})
        patient = data.get('patient_info', {})
        gender = patient.get('gender', 'male')
        is_male = gender in ['male', '男']
        
        # 1. 中心型肥胖（腰围）
        waist = patient.get('waist', 0)
        waist_threshold = 90 if is_male else 85
        if waist >= waist_threshold:
            criteria.append({'criterion': '中心型肥胖', 'value': f'腰围{waist}cm', 'threshold': f'≥{waist_threshold}cm'})
        
        # 2. 高血糖
        fasting = metrics.get('blood_glucose', {}).get('fasting', 0)
        if fasting >= 6.1:
            criteria.append({'criterion': '高血糖', 'value': f'空腹血糖{fasting}mmol/L', 'threshold': '≥6.1mmol/L'})
        
        # 3. 高血压
        bp = metrics.get('blood_pressure', {})
        systolic = bp.get('systolic', 0)
        diastolic = bp.get('diastolic', 0)
        if systolic >= 130 or diastolic >= 85:
            criteria.append({'criterion': '高血压', 'value': f'血压{systolic}/{diastolic}mmHg', 'threshold': '≥130/85mmHg'})
        
        # 4. 高甘油三酯
        tg = metrics.get('blood_lipid', {}).get('tg', 0)
        if tg >= 1.7:
            criteria.append({'criterion': '高甘油三酯', 'value': f'TG={tg}mmol/L', 'threshold': '≥1.7mmol/L'})
        
        # 5. 低HDL-C
        hdl_c = metrics.get('blood_lipid', {}).get('hdl_c', 0)
        hdl_threshold = 1.04 if is_male else 1.30
        if hdl_c < hdl_threshold:
            criteria.append({'criterion': '低HDL-C', 'value': f'HDL-C={hdl_c}mmol/L', 'threshold': f'<{hdl_threshold}mmol/L'})
        
        has_metabolic_syndrome = len(criteria) >= 3
        
        return {
            'has_metabolic_syndrome': has_metabolic_syndrome,
            'criteria_count': len(criteria),
            'criteria': criteria,
            'diagnosis': '代谢综合征' if has_metabolic_syndrome else f'满足{len(criteria)}项标准（需≥3项）'
        }
    
    def _assess_body_fat(self, data: Dict) -> Dict:
        """评估体脂率"""
        metrics = data.get('health_metrics', {})
        basic = metrics.get('basic', {})
        patient = data.get('patient_info', {})
        gender = patient.get('gender', 'male')
        is_male = gender in ['male', '男']
        
        body_fat_rate = basic.get('body_fat_rate', 0)
        visceral_fat = basic.get('visceral_fat_level', 0)
        
        if body_fat_rate > 0:
            # 体脂率评估
            if is_male:
                if body_fat_rate < 10:
                    bf_level = '偏低'
                elif body_fat_rate <= 20:
                    bf_level = '正常'
                elif body_fat_rate <= 25:
                    bf_level = '偏高'
                else:
                    bf_level = '肥胖'
            else:
                if body_fat_rate < 20:
                    bf_level = '偏低'
                elif body_fat_rate <= 30:
                    bf_level = '正常'
                elif body_fat_rate <= 35:
                    bf_level = '偏高'
                else:
                    bf_level = '肥胖'
        else:
            bf_level = '数据不足'
        
        # 内脏脂肪评估
        if visceral_fat > 0:
            if visceral_fat < 10:
                vf_level = '正常'
            elif visceral_fat < 15:
                vf_level = '偏高'
            else:
                vf_level = '明显升高'
        else:
            vf_level = '数据不足'
        
        return {
            'body_fat_rate': body_fat_rate,
            'body_fat_level': bf_level,
            'visceral_fat': visceral_fat,
            'visceral_fat_level': vf_level,
            'available': body_fat_rate > 0
        }
    
    def _assess_related_diseases(self, data: Dict, bmi: Dict) -> Dict:
        """评估肥胖相关疾病风险"""
        diseases = []
        bmi_value = bmi['value']
        metrics = data.get('health_metrics', {})
        
        # 高血压风险
        bp = metrics.get('blood_pressure', {})
        if bp.get('systolic', 0) >= 140 or bp.get('diastolic', 0) >= 90:
            diseases.append({'disease': '高血压', 'status': '已存在'})
        elif bmi_value >= 28:
            diseases.append({'disease': '高血压', 'status': '高风险'})
        
        # 糖尿病风险
        glucose = metrics.get('blood_glucose', {})
        if glucose.get('fasting', 0) >= 7.0:
            diseases.append({'disease': '糖尿病', 'status': '已存在'})
        elif bmi_value >= 28 or glucose.get('fasting', 0) >= 6.1:
            diseases.append({'disease': '糖尿病', 'status': '高风险'})
        
        # 高血脂风险
        lipid = metrics.get('blood_lipid', {})
        if lipid.get('ldl_c', 0) >= 4.1 or lipid.get('tg', 0) >= 2.3:
            diseases.append({'disease': '高血脂', 'status': '已存在'})
        elif bmi_value >= 28:
            diseases.append({'disease': '高血脂', 'status': '高风险'})
        
        # 脂肪肝风险
        clinical = data.get('clinical_examination', {})
        fatty_liver = clinical.get('abdominal_ultrasound', {}).get('fatty_liver', '')
        if fatty_liver:
            diseases.append({'disease': '脂肪肝', 'status': fatty_liver})
        elif bmi_value >= 28:
            diseases.append({'disease': '脂肪肝', 'status': '高风险'})
        
        return {
            'diseases': diseases,
            'high_risk_count': len([d for d in diseases if d['status'] == '高风险']),
            'existing_count': len([d for d in diseases if d['status'] not in ['高风险', '']])
        }
    
    def _overall_risk_assessment(self, bmi: Dict, central: Dict, metabolic: Dict) -> Dict:
        """综合风险评估"""
        total_score = bmi['score'] + central['score']
        
        if metabolic['has_metabolic_syndrome']:
            total_score += 2
        
        if total_score >= 8:
            risk_level = '高风险'
        elif total_score >= 5:
            risk_level = '中风险'
        else:
            risk_level = '低风险'
        
        # 治疗建议
        if bmi['value'] >= 32.5:
            treatment = '建议考虑减重手术评估'
        elif bmi['value'] >= 28:
            treatment = '建议药物治疗+生活方式干预'
        elif bmi['value'] >= 24:
            treatment = '建议生活方式干预'
        else:
            treatment = '保持健康生活方式'
        
        return {
            'risk_level': risk_level,
            'total_score': total_score,
            'treatment_recommendation': treatment,
            'target_weight': self._calculate_target_weight(bmi)
        }
    
    def _calculate_target_weight(self, bmi: Dict) -> Dict:
        """计算目标体重"""
        height = bmi.get('height', 0)
        if height == 0:
            return {'available': False}
        
        # 目标BMI为24（正常高限）
        target_bmi = 24.0
        target_weight = target_bmi * (height ** 2)
        current_weight = bmi.get('weight', 0)
        weight_to_lose = current_weight - target_weight
        
        return {
            'available': True,
            'current_weight': round(current_weight, 1),
            'target_weight': round(target_weight, 1),
            'weight_to_lose': round(weight_to_lose, 1) if weight_to_lose > 0 else 0
        }


def main():
    # UTF-8 encoding fix for Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    parser = argparse.ArgumentParser(description='肥胖风险评估计算')
    parser.add_argument('--input', required=True, help='输入验证后的健康数据文件路径')
    parser.add_argument('--output', default='obesity_risk.json', help='输出风险评估文件路径')
    
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
    
    calculator = ObesityRiskCalculator()
    results = calculator.calculate(data)
    
    # 保存结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Human-readable output to stderr (for logging)
    print(f"BMI: {results['bmi_assessment']['value']} kg/m² ({results['bmi_assessment']['level']})", file=sys.stderr)
    print(f"风险等级: {results['overall_risk']['risk_level']}", file=sys.stderr)

    # JSON output to stdout only (for pipeline)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
