#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高血压风险评估计算脚本

功能：
1. 血压水平分类
2. 心血管风险分层
3. 靶器官损害评估
4. H型高血压筛查
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple


class HypertensionRiskCalculator:
    """高血压风险评估计算器"""
    
    # 血压水平分类标准（《中国高血压防治指南2018》）
    BP_LEVELS = {
        'normal': {'systolic': (0, 119), 'diastolic': (0, 79), 'level': '正常血压', 'score': 1},
        'high_normal': {'systolic': (120, 139), 'diastolic': (80, 89), 'level': '正常高值', 'score': 2},
        'grade_1': {'systolic': (140, 159), 'diastolic': (90, 99), 'level': '高血压1级(轻度)', 'score': 3},
        'grade_2': {'systolic': (160, 179), 'diastolic': (100, 109), 'level': '高血压2级(中度)', 'score': 4},
        'grade_3': {'systolic': (180, 300), 'diastolic': (110, 200), 'level': '高血压3级(重度)', 'score': 5}
    }
    
    # 评估标准来源
    STANDARD_SOURCE = {
        'standard': '《中国高血压防治指南2018年修订版》',
        'organization': '中国高血压联盟',
        'type': '国家标准'
    }
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行高血压风险评估"""
        self.results = {
            'patient_info': data.get('patient_info', {}),
            'assessment_date': datetime.now().strftime('%Y-%m-%d'),
            'assessment_type': 'hypertension',
            'standard': self.STANDARD_SOURCE
        }
        
        metrics = data.get('health_metrics', {})
        
        # 1. 血压水平评估
        bp_assessment = self._assess_blood_pressure(metrics)
        self.results['blood_pressure'] = bp_assessment
        
        # 2. 心血管风险因素评估
        cv_risk = self._assess_cardiovascular_risk(data)
        self.results['cardiovascular_risk'] = cv_risk
        
        # 3. 靶器官损害评估
        organ_damage = self._assess_organ_damage(data)
        self.results['organ_damage'] = organ_damage
        
        # 4. H型高血压筛查
        h_type = self._assess_h_type_hypertension(data)
        self.results['h_type_hypertension'] = h_type
        
        # 5. 综合风险分层
        risk_stratification = self._risk_stratification(bp_assessment, cv_risk, organ_damage)
        self.results['risk_stratification'] = risk_stratification
        
        return self.results
    
    def _assess_blood_pressure(self, metrics: Dict) -> Dict:
        """评估血压水平"""
        bp = metrics.get('blood_pressure', {})
        systolic = bp.get('systolic', 0)
        diastolic = bp.get('diastolic', 0)
        
        # 确定血压级别（取较高的级别）
        level = 'normal'
        level_info = self.BP_LEVELS['normal']
        
        for key, info in self.BP_LEVELS.items():
            sys_range = info['systolic']
            dia_range = info['diastolic']
            
            # 收缩压或舒张压任一达标即判定
            if (sys_range[0] <= systolic <= sys_range[1]) or \
               (dia_range[0] <= diastolic <= dia_range[1]):
                if info['score'] > level_info['score']:
                    level = key
                    level_info = info
        
        return {
            'systolic': systolic,
            'diastolic': diastolic,
            'level': level_info['level'],
            'level_code': level,
            'score': level_info['score'],
            'description': self._get_bp_description(level_info['level'], systolic, diastolic)
        }
    
    def _get_bp_description(self, level: str, systolic: float, diastolic: float) -> str:
        """获取血压描述"""
        descriptions = {
            '正常血压': f'血压水平正常（{systolic}/{diastolic}mmHg）',
            '正常高值': f'血压偏高，需注意监测（{systolic}/{diastolic}mmHg）',
            '高血压1级(轻度)': f'轻度高血压，建议改善生活方式（{systolic}/{diastolic}mmHg）',
            '高血压2级(中度)': f'中度高血压，需要药物治疗（{systolic}/{diastolic}mmHg）',
            '高血压3级(重度)': f'重度高血压，需立即就医（{systolic}/{diastolic}mmHg）'
        }
        return descriptions.get(level, '血压评估异常')
    
    def _assess_cardiovascular_risk(self, data: Dict) -> Dict:
        """评估心血管危险因素"""
        risk_factors = []
        patient = data.get('patient_info', {})
        metrics = data.get('health_metrics', {})
        lifestyle = data.get('lifestyle', {})
        
        # 年龄
        age = patient.get('age', 0)
        gender = patient.get('gender', 'male')
        if (gender in ['male', '男'] and age >= 55) or (gender in ['female', '女'] and age >= 65):
            risk_factors.append({'factor': '年龄', 'value': age, 'risk': '年龄≥55岁(男)/65岁(女)'})
        
        # 吸烟
        smoking = lifestyle.get('smoking', {}).get('history', False)
        if smoking:
            risk_factors.append({'factor': '吸烟', 'value': True, 'risk': '吸烟史'})
        
        # 血脂异常
        lipid = metrics.get('blood_lipid', {})
        if lipid.get('ldl_c', 0) > 3.4 or lipid.get('tc', 0) > 5.2:
            risk_factors.append({'factor': '血脂异常', 'value': lipid, 'risk': 'LDL-C或TC升高'})
        
        # 肥胖
        bmi = metrics.get('bmi', {})
        bmi_value = bmi.get('value', 0) if isinstance(bmi, dict) else bmi
        if bmi_value >= 28:
            risk_factors.append({'factor': '肥胖', 'value': bmi_value, 'risk': 'BMI≥28'})
        
        # 糖代谢异常
        glucose = metrics.get('blood_glucose', {})
        if glucose.get('fasting', 0) >= 6.1 or glucose.get('hba1c', 0) >= 5.7:
            risk_factors.append({'factor': '糖代谢异常', 'value': glucose, 'risk': '空腹血糖或HbA1c异常'})
        
        return {
            'count': len(risk_factors),
            'factors': risk_factors,
            'risk_level': '高危' if len(risk_factors) >= 3 else ('中危' if len(risk_factors) >= 1 else '低危')
        }
    
    def _assess_organ_damage(self, data: Dict) -> Dict:
        """评估靶器官损害"""
        damages = []
        metrics = data.get('health_metrics', {})
        clinical = data.get('clinical_examination', {})
        
        # 左心室肥厚（心电图）
        ecg = clinical.get('ecg', '')
        if '左室肥厚' in ecg or '左室高电压' in ecg:
            damages.append({'organ': '心脏', 'finding': '左心室肥厚', 'evidence': ecg})
        
        # 颈动脉斑块
        carotid = clinical.get('carotid_ultrasound', {})
        if carotid.get('plaque') or carotid.get('imt', 0) > 1.0:
            damages.append({'organ': '血管', 'finding': '颈动脉病变', 'evidence': carotid})
        
        # 肾功能损害
        kidney = metrics.get('kidney', {})
        egfr = kidney.get('egfr', 100)
        uacr = kidney.get('uacr', 0)
        if egfr < 60:
            damages.append({'organ': '肾脏', 'finding': 'eGFR下降', 'evidence': f'eGFR={egfr}'})
        if uacr > 30:
            damages.append({'organ': '肾脏', 'finding': '微量白蛋白尿', 'evidence': f'UACR={uacr}mg/g'})
        
        return {
            'has_damage': len(damages) > 0,
            'damages': damages,
            'summary': f'发现{len(damages)}项靶器官损害' if damages else '未发现明显靶器官损害'
        }
    
    def _assess_h_type_hypertension(self, data: Dict) -> Dict:
        """评估H型高血压"""
        other = data.get('health_metrics', {}).get('other_metabolism', {})
        hcy = other.get('homocysteine', 0)
        
        is_h_type = hcy >= 10
        
        return {
            'homocysteine': hcy,
            'is_h_type': is_h_type,
            'description': f'H型高血压（Hcy={hcy}μmol/L，≥10μmol/L）' if is_h_type else f'非H型高血压（Hcy={hcy}μmol/L）',
            'recommendation': '建议补充叶酸治疗' if is_h_type else None
        }
    
    def _risk_stratification(self, bp: Dict, cv_risk: Dict, organ: Dict) -> Dict:
        """综合风险分层"""
        bp_level = bp.get('level_code', 'normal')
        risk_count = cv_risk.get('count', 0)
        has_damage = organ.get('has_damage', False)
        
        # 风险分层逻辑
        if bp_level == 'grade_3':
            risk_level = '很高危'
        elif bp_level == 'grade_2':
            if has_damage or risk_count >= 3:
                risk_level = '很高危'
            else:
                risk_level = '高危'
        elif bp_level == 'grade_1':
            if has_damage:
                risk_level = '高危'
            elif risk_count >= 3:
                risk_level = '高危'
            elif risk_count >= 1:
                risk_level = '中危'
            else:
                risk_level = '低危'
        else:
            if has_damage:
                risk_level = '高危'
            elif risk_count >= 3:
                risk_level = '中危'
            else:
                risk_level = '低危'
        
        return {
            'risk_level': risk_level,
            'bp_level': bp.get('level'),
            'risk_factors_count': risk_count,
            'has_organ_damage': has_damage,
            'recommendation': self._get_recommendation(risk_level)
        }
    
    def _get_recommendation(self, risk_level: str) -> str:
        """获取干预建议"""
        recommendations = {
            '低危': '定期监测血压，改善生活方式',
            '中危': '加强生活方式干预，定期随访',
            '高危': '建议启动药物治疗，加强生活方式干预',
            '很高危': '立即启动药物治疗，综合干预'
        }
        return recommendations.get(risk_level, '请咨询医生')


def main():
    # 配置 UTF-8 编码输出（Windows 兼容）
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description='高血压风险评估计算')
    parser.add_argument('--input', required=True, help='输入验证后的健康数据文件路径')
    parser.add_argument('--output', default='hypertension_risk.json', help='输出风险评估文件路径')
    
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
    
    calculator = HypertensionRiskCalculator()
    results = calculator.calculate(data)
    
    # 保存结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 输出JSON到stdout（供SkillWorkflowExecutor捕获）
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
