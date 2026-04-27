#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高血糖风险评估计算脚本

功能：
1. 糖代谢状态评估
2. 糖尿病风险预测
3. 胰岛素抵抗评估
4. 并发症风险筛查
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple


class HyperglycemiaRiskCalculator:
    """高血糖风险评估计算器"""
    
    # 空腹血糖分类标准（《中国2型糖尿病防治指南2020》）
    FASTING_GLUCOSE_LEVELS = {
        'normal': {'range': (0, 6.0), 'level': '正常', 'score': 1},
        'ifg': {'range': (6.1, 6.9), 'level': '空腹血糖受损(IFG)', 'score': 2},
        'diabetes': {'range': (7.0, 999), 'level': '糖尿病', 'score': 5}
    }
    
    # HbA1c分类标准
    HBA1C_LEVELS = {
        'normal': {'range': (0, 5.6), 'level': '正常', 'score': 1},
        'prediabetes': {'range': (5.7, 6.4), 'level': '糖尿病前期', 'score': 2},
        'diabetes': {'range': (6.5, 999), 'level': '糖尿病', 'score': 5}
    }
    
    # 评估标准来源
    STANDARD_SOURCE = {
        'standard': '《中国2型糖尿病防治指南2020年版》',
        'organization': '中华医学会糖尿病学分会',
        'type': '国家标准'
    }
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行高血糖风险评估"""
        self.results = {
            'patient_info': data.get('patient_info', {}),
            'assessment_date': datetime.now().strftime('%Y-%m-%d'),
            'assessment_type': 'hyperglycemia',
            'standard': self.STANDARD_SOURCE
        }
        
        metrics = data.get('health_metrics', {})
        
        # 1. 血糖水平评估
        glucose_assessment = self._assess_glucose(metrics)
        self.results['glucose_assessment'] = glucose_assessment
        
        # 2. 糖尿病前期风险评估
        prediabetes_risk = self._assess_prediabetes_risk(glucose_assessment)
        self.results['prediabetes_risk'] = prediabetes_risk
        
        # 3. 胰岛素抵抗评估
        insulin_resistance = self._assess_insulin_resistance(data)
        self.results['insulin_resistance'] = insulin_resistance
        
        # 4. 并发症风险筛查
        complications = self._assess_complications(data)
        self.results['complications'] = complications
        
        # 5. 综合风险评估
        overall_risk = self._overall_risk_assessment(glucose_assessment, prediabetes_risk, complications)
        self.results['overall_risk'] = overall_risk
        
        return self.results
    
    def _assess_glucose(self, metrics: Dict) -> Dict:
        """评估血糖水平"""
        glucose = metrics.get('blood_glucose', {})
        fasting = glucose.get('fasting', 0)
        hba1c = glucose.get('hba1c', 0)
        postprandial = glucose.get('postprandial', 0)
        
        # 空腹血糖评估
        fasting_level = 'normal'
        for key, info in self.FASTING_GLUCOSE_LEVELS.items():
            if info['range'][0] <= fasting <= info['range'][1]:
                fasting_level = key
                break
        
        # HbA1c评估
        hba1c_level = 'normal'
        for key, info in self.HBA1C_LEVELS.items():
            if info['range'][0] <= hba1c <= info['range'][1]:
                hba1c_level = key
                break
        
        # 综合判断
        if fasting_level == 'diabetes' or hba1c_level == 'diabetes':
            status = '糖尿病'
            score = 5
        elif fasting_level == 'ifg' or hba1c_level == 'prediabetes':
            status = '糖尿病前期'
            score = 2
        else:
            status = '正常'
            score = 1
        
        return {
            'fasting_glucose': {
                'value': fasting,
                'level': self.FASTING_GLUCOSE_LEVELS[fasting_level]['level'],
                'status': fasting_level
            },
            'hba1c': {
                'value': hba1c,
                'level': self.HBA1C_LEVELS[hba1c_level]['level'],
                'status': hba1c_level
            },
            'postprandial': {
                'value': postprandial,
                'available': postprandial > 0
            },
            'overall_status': status,
            'overall_score': score
        }
    
    def _assess_prediabetes_risk(self, glucose: Dict) -> Dict:
        """评估糖尿病前期风险"""
        status = glucose.get('overall_status', '正常')
        
        if status == '糖尿病前期':
            # 计算3年糖尿病转化风险（简化模型）
            fasting = glucose['fasting_glucose']['value']
            hba1c = glucose['hba1c']['value']
            
            # 基于FPG和HbA1c的风险估算
            risk_factor = 1.0
            if fasting >= 6.5:
                risk_factor += 0.5
            if hba1c >= 6.0:
                risk_factor += 0.3
            
            three_year_risk = min(50, 15 * risk_factor)  # 简化估算
            
            return {
                'is_prediabetes': True,
                'type': glucose['fasting_glucose']['level'],
                'three_year_risk': round(three_year_risk, 1),
                'recommendation': '强烈建议生活方式干预，可降低58%的糖尿病转化风险'
            }
        elif status == '糖尿病':
            return {
                'is_prediabetes': False,
                'is_diabetes': True,
                'recommendation': '建议规范降糖治疗'
            }
        else:
            return {
                'is_prediabetes': False,
                'is_diabetes': False,
                'three_year_risk': 5.0,
                'recommendation': '保持健康生活方式，定期监测血糖'
            }
    
    def _assess_insulin_resistance(self, data: Dict) -> Dict:
        """评估胰岛素抵抗"""
        glucose = data.get('health_metrics', {}).get('blood_glucose', {})
        other = data.get('health_metrics', {}).get('other_metabolism', {})
        
        fasting_glucose = glucose.get('fasting', 0)
        fasting_insulin = other.get('fasting_insulin', 0)
        
        if fasting_insulin > 0 and fasting_glucose > 0:
            # 计算HOMA-IR
            homa_ir = (fasting_glucose * fasting_insulin) / 22.5
            
            if homa_ir < 2.5:
                level = '正常'
                score = 1
            elif homa_ir < 3.5:
                level = '轻度胰岛素抵抗'
                score = 2
            else:
                level = '明显胰岛素抵抗'
                score = 3
            
            return {
                'available': True,
                'homa_ir': round(homa_ir, 2),
                'level': level,
                'score': score
            }
        else:
            return {
                'available': False,
                'homa_ir': None,
                'level': '数据不足，无法评估',
                'score': 0
            }
    
    def _assess_complications(self, data: Dict) -> Dict:
        """筛查糖尿病并发症风险"""
        complications = []
        metrics = data.get('health_metrics', {})
        clinical = data.get('clinical_examination', {})
        
        # 糖尿病肾病风险
        kidney = metrics.get('kidney', {})
        uacr = kidney.get('uacr', 0)
        egfr = kidney.get('egfr', 100)
        
        if uacr > 30:
            complications.append({
                'type': '糖尿病肾病',
                'finding': '微量白蛋白尿',
                'severity': '早期' if uacr < 300 else '临床期',
                'uacr': uacr
            })
        if egfr < 60:
            complications.append({
                'type': '肾功能下降',
                'finding': f'eGFR={egfr}',
                'severity': '中度' if egfr >= 30 else '重度'
            })
        
        # 视网膜病变风险
        fundus = clinical.get('fundus_photography', '')
        if '糖尿病视网膜' in fundus or '视网膜病变' in fundus:
            complications.append({
                'type': '糖尿病视网膜病变',
                'finding': fundus
            })
        
        # 神经病变风险（简化评估）
        glucose = metrics.get('blood_glucose', {})
        hba1c = glucose.get('hba1c', 0)
        if hba1c > 8.0:
            complications.append({
                'type': '神经病变风险',
                'finding': f'HbA1c={hba1c}%，长期高血糖增加神经病变风险',
                'severity': '高风险'
            })
        
        return {
            'has_complications': len(complications) > 0,
            'complications': complications,
            'summary': f'发现{len(complications)}项并发症风险' if complications else '未发现明显并发症'
        }
    
    def _overall_risk_assessment(self, glucose: Dict, prediabetes: Dict, complications: Dict) -> Dict:
        """综合风险评估"""
        score = glucose.get('overall_score', 1)
        
        if score >= 5:
            risk_level = '高风险'
            recommendation = '建议规范治疗，定期监测血糖和并发症'
        elif score >= 2:
            risk_level = '中风险'
            recommendation = '建议生活方式干预，定期随访'
        else:
            risk_level = '低风险'
            recommendation = '保持健康生活方式'
        
        if complications.get('has_complications'):
            risk_level = '高风险'
            recommendation = '建议积极治疗并发症'
        
        return {
            'risk_level': risk_level,
            'glucose_status': glucose.get('overall_status'),
            'prediabetes_risk': prediabetes.get('three_year_risk'),
            'recommendation': recommendation
        }


def main():
    # UTF-8 encoding fix for Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    parser = argparse.ArgumentParser(description='高血糖风险评估计算')
    parser.add_argument('--input', required=True, help='输入验证后的健康数据文件路径')
    parser.add_argument('--output', default='hyperglycemia_risk.json', help='输出风险评估文件路径')
    
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
    
    calculator = HyperglycemiaRiskCalculator()
    results = calculator.calculate(data)
    
    # 保存结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Human-readable output to stderr (for logging)
    print(f"患者: {results['patient_info'].get('name', '未知')}", file=sys.stderr)
    print(f"评估日期: {results['assessment_date']}", file=sys.stderr)
    print(f"血糖状态: {results['glucose_assessment']['overall_status']}", file=sys.stderr)
    print(f"风险等级: {results['overall_risk']['risk_level']}", file=sys.stderr)

    # JSON output to stdout (for pipeline)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
