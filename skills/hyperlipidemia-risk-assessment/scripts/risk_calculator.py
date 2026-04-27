#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高血脂风险评估计算脚本

功能：
1. 血脂水平评估
2. LDL-C危险分层
3. 残余风险评估
4. 心血管风险评估
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple


class HyperlipidemiaRiskCalculator:
    """高血脂风险评估计算器"""
    
    # 血脂水平分类标准（《中国成人血脂异常防治指南2016》）
    TC_LEVELS = {
        'normal': {'range': (0, 5.17), 'level': '合适水平'},
        'borderline': {'range': (5.18, 6.18), 'level': '边缘升高'},
        'elevated': {'range': (6.19, 999), 'level': '升高'}
    }
    
    TG_LEVELS = {
        'normal': {'range': (0, 1.69), 'level': '合适水平'},
        'borderline': {'range': (1.70, 2.25), 'level': '边缘升高'},
        'elevated': {'range': (2.26, 999), 'level': '升高'}
    }
    
    LDL_C_LEVELS = {
        'optimal': {'range': (0, 2.58), 'level': '理想水平'},
        'near_optimal': {'range': (2.59, 3.34), 'level': '较佳水平'},
        'borderline': {'range': (3.35, 4.12), 'level': '边缘升高'},
        'elevated': {'range': (4.13, 4.89), 'level': '升高'},
        'very_high': {'range': (4.90, 999), 'level': '极高'}
    }
    
    HDL_C_LEVELS = {
        'low': {'male_range': (0, 1.03), 'female_range': (0, 1.29), 'level': '降低'},
        'normal': {'male_range': (1.04, 1.55), 'female_range': (1.30, 1.55), 'level': '正常'},
        'high': {'range': (1.56, 999), 'level': '升高（保护性）'}
    }
    
    # 评估标准来源
    STANDARD_SOURCE = {
        'standard': '《中国成人血脂异常防治指南2016年修订版》',
        'organization': '中国成人血脂异常防治指南修订联合委员会',
        'type': '行业标准'
    }
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行高血脂风险评估"""
        self.results = {
            'patient_info': data.get('patient_info', {}),
            'assessment_date': datetime.now().strftime('%Y-%m-%d'),
            'assessment_type': 'hyperlipidemia',
            'standard': self.STANDARD_SOURCE
        }
        
        metrics = data.get('health_metrics', {})
        
        # 1. 血脂水平评估
        lipid_assessment = self._assess_lipid(metrics)
        self.results['lipid_assessment'] = lipid_assessment
        
        # 2. 血脂异常分类
        lipid_type = self._classify_lipid_disorder(lipid_assessment)
        self.results['lipid_disorder_type'] = lipid_type
        
        # 3. LDL-C危险分层
        ldl_stratification = self._ldl_risk_stratification(data, lipid_assessment)
        self.results['ldl_stratification'] = ldl_stratification
        
        # 4. 残余风险评估
        residual_risk = self._assess_residual_risk(metrics)
        self.results['residual_risk'] = residual_risk
        
        # 5. 综合风险评估
        overall_risk = self._overall_risk_assessment(lipid_assessment, ldl_stratification)
        self.results['overall_risk'] = overall_risk
        
        return self.results
    
    def _assess_lipid(self, metrics: Dict) -> Dict:
        """评估血脂水平"""
        lipid = metrics.get('blood_lipid', {})
        tc = lipid.get('tc', 0)
        tg = lipid.get('tg', 0)
        ldl_c = lipid.get('ldl_c', 0)
        hdl_c = lipid.get('hdl_c', 0)
        
        gender = metrics.get('patient_info', {}).get('gender', 'male')
        is_male = gender in ['male', '男']
        
        # 评估各项血脂
        tc_level = self._get_level(tc, self.TC_LEVELS)
        tg_level = self._get_level(tg, self.TG_LEVELS)
        ldl_level = self._get_level(ldl_c, self.LDL_C_LEVELS)
        hdl_level = self._get_hdl_level(hdl_c, is_male)
        
        return {
            'tc': {'value': tc, 'level': tc_level},
            'tg': {'value': tg, 'level': tg_level},
            'ldl_c': {'value': ldl_c, 'level': ldl_level},
            'hdl_c': {'value': hdl_c, 'level': hdl_level}
        }
    
    def _get_level(self, value: float, levels: Dict) -> str:
        """获取血脂水平"""
        for key, info in levels.items():
            if 'range' in info:
                if info['range'][0] <= value <= info['range'][1]:
                    return info['level']
            elif 'male_range' in info:
                continue
        return '异常'
    
    def _get_hdl_level(self, value: float, is_male: bool) -> str:
        """获取HDL-C水平"""
        for key, info in self.HDL_C_LEVELS.items():
            if 'range' in info:
                if info['range'][0] <= value <= info['range'][1]:
                    return info['level']
            elif is_male and 'male_range' in info:
                if info['male_range'][0] <= value <= info['male_range'][1]:
                    return info['level']
            elif not is_male and 'female_range' in info:
                if info['female_range'][0] <= value <= info['female_range'][1]:
                    return info['level']
        return '异常'
    
    def _classify_lipid_disorder(self, lipid: Dict) -> Dict:
        """血脂异常分类"""
        tc_elevated = '升高' in lipid['tc']['level']
        tg_elevated = '升高' in lipid['tg']['level']
        hdl_low = '降低' in lipid['hdl_c']['level']
        
        disorders = []
        if tc_elevated and tg_elevated:
            disorders.append('混合型高脂血症')
        elif tc_elevated:
            disorders.append('高胆固醇血症')
        elif tg_elevated:
            disorders.append('高甘油三酯血症')
        
        if hdl_low:
            disorders.append('低高密度脂蛋白血症')
        
        return {
            'has_disorder': len(disorders) > 0,
            'types': disorders if disorders else ['血脂正常'],
            'primary_type': disorders[0] if disorders else '血脂正常'
        }
    
    def _ldl_risk_stratification(self, data: Dict, lipid: Dict) -> Dict:
        """LDL-C危险分层"""
        ldl_c = lipid['ldl_c']['value']
        
        # 评估危险因素
        risk_factors = self._count_risk_factors(data)
        has_diabetes = data.get('health_metrics', {}).get('blood_glucose', {}).get('fasting', 0) >= 7.0
        has_ascvd = False  # 需要临床诊断
        
        # 确定危险分层
        if has_ascvd or (has_diabetes and risk_factors >= 3):
            risk_tier = '极高危'
            target = '<1.8'
        elif has_diabetes or risk_factors >= 3 or ldl_c >= 4.9:
            risk_tier = '高危'
            target = '<2.6'
        elif risk_factors >= 1:
            risk_tier = '中危'
            target = '<3.4'
        else:
            risk_tier = '低危'
            target = '<4.1'
        
        return {
            'ldl_c_value': ldl_c,
            'risk_tier': risk_tier,
            'ldl_target': f'{target}mmol/L',
            'risk_factors_count': risk_factors,
            'at_target': self._check_ldl_target(ldl_c, target)
        }
    
    def _count_risk_factors(self, data: Dict) -> int:
        """计算危险因素数量"""
        count = 0
        patient = data.get('patient_info', {})
        metrics = data.get('health_metrics', {})
        
        # 年龄
        age = patient.get('age', 0)
        gender = patient.get('gender', 'male')
        if (gender in ['male', '男'] and age >= 45) or (gender in ['female', '女'] and age >= 55):
            count += 1
        
        # 吸烟
        if data.get('lifestyle', {}).get('smoking', {}).get('history', False):
            count += 1
        
        # 高血压
        bp = metrics.get('blood_pressure', {})
        if bp.get('systolic', 0) >= 140 or bp.get('diastolic', 0) >= 90:
            count += 1
        
        # 低HDL-C
        if metrics.get('blood_lipid', {}).get('hdl_c', 0) < 1.0:
            count += 1
        
        return count
    
    def _check_ldl_target(self, ldl_c: float, target: str) -> bool:
        """检查LDL-C是否达标"""
        target_value = float(target.replace('<', '').replace('mmol/L', ''))
        return ldl_c < target_value
    
    def _assess_residual_risk(self, metrics: Dict) -> Dict:
        """残余风险评估"""
        lipid = metrics.get('blood_lipid', {})
        tc = lipid.get('tc', 0)
        hdl_c = lipid.get('hdl_c', 0)
        
        non_hdl_c = tc - hdl_c if tc and hdl_c else None
        lp_a = lipid.get('lp_a', 0)
        
        risks = []
        
        if non_hdl_c and non_hdl_c >= 3.4:
            risks.append({'factor': 'non-HDL-C升高', 'value': non_hdl_c})
        
        if lp_a and lp_a >= 300:
            risks.append({'factor': 'Lp(a)升高', 'value': lp_a})
        
        return {
            'non_hdl_c': non_hdl_c,
            'lp_a': lp_a,
            'has_residual_risk': len(risks) > 0,
            'risks': risks
        }
    
    def _overall_risk_assessment(self, lipid: Dict, ldl: Dict) -> Dict:
        """综合风险评估"""
        # 基于LDL-C分层确定风险等级
        risk_tier = ldl['risk_tier']
        
        risk_map = {
            '极高危': '高风险',
            '高危': '高风险',
            '中危': '中风险',
            '低危': '低风险'
        }
        
        risk_level = risk_map.get(risk_tier, '中风险')
        
        return {
            'risk_level': risk_level,
            'ldl_target': ldl['ldl_target'],
            'ldl_at_target': ldl['at_target'],
            'recommendation': self._get_recommendation(risk_level, ldl['at_target'])
        }
    
    def _get_recommendation(self, risk_level: str, at_target: bool) -> str:
        """获取建议"""
        if risk_level == '高风险':
            if at_target:
                return 'LDL-C已达标，继续维持治疗'
            else:
                return 'LDL-C未达标，建议加强降脂治疗'
        elif risk_level == '中风险':
            return '建议生活方式干预，必要时药物治疗'
        else:
            return '定期监测血脂，保持健康生活方式'


def main():
    # UTF-8 encoding fix for Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    parser = argparse.ArgumentParser(description='高血脂风险评估计算')
    parser.add_argument('--input', required=True, help='输入验证后的健康数据文件路径')
    parser.add_argument('--output', default='hyperlipidemia_risk.json', help='输出风险评估文件路径')
    
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
    
    calculator = HyperlipidemiaRiskCalculator()
    results = calculator.calculate(data)
    
    # 保存结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Human-readable output to stderr (for logging)
    print(f"血脂异常类型: {results['lipid_disorder_type']['primary_type']}", file=sys.stderr)
    print(f"风险等级: {results['overall_risk']['risk_level']}", file=sys.stderr)

    # JSON output to stdout only (for pipeline)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
