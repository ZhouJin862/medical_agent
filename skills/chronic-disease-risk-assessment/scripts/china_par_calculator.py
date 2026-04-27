#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
China-PAR心血管风险预测计算器

基于《中国心血管病风险评估和管理指南》的China-PAR模型
预测10年ASCVD（动脉粥样硬化性心血管疾病）发病风险

参考文献：
- 中国心血管病风险评估和管理指南（2019）
- Prediction for ASCVD Risk in China (China-PAR) Project
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Tuple


class ChinaPARCalculator:
    """China-PAR风险预测计算器"""
    
    # China-PAR模型系数（男性）
    # 基于中国心血管病风险评估和管理指南（2019）
    MALE_COEFFICIENTS = {
        'age': 0.5048,
        'sbp_treated': 0.7116,
        'sbp_untreated': 0.5252,
        'tc': 0.2396,
        'hdl_c': -0.1658,
        'diabetes': 0.6968,
        'smoking': 0.5273,
        'bmi': 0.0647,
        'waist': 0.0285
    }
    
    # China-PAR模型系数（女性）
    FEMALE_COEFFICIENTS = {
        'age': 0.5552,
        'sbp_treated': 0.7343,
        'sbp_untreated': 0.5462,
        'tc': 0.2039,
        'hdl_c': -0.2593,
        'diabetes': 0.7842,
        'smoking': 0.3356,
        'bmi': 0.0379,
        'waist': 0.0355
    }
    
    # 基础生存率（10年）
    BASELINE_SURVIVAL = {
        'male': 0.9573,
        'female': 0.9830
    }
    
    # 平均风险得分
    MEAN_SCORE = {
        'male': 3.8508,
        'female': 3.4295
    }
    
    # 风险分层标准
    RISK_LEVELS = {
        'low': {'threshold': 5.0, 'label': '低风险', 'color': '绿色'},
        'medium': {'threshold': 9.9, 'label': '中风险', 'color': '黄色'},
        'high': {'threshold': 100.0, 'label': '高风险', 'color': '红色'}
    }
    
    def __init__(self):
        self.result = {}
    
    def calculate_risk(
        self,
        age: int,
        gender: str,
        systolic_bp: float,
        bp_treated: bool,
        tc: float,
        hdl_c: float,
        diabetes: bool,
        smoking: bool,
        bmi: float,
        waist_circumference: float = None
    ) -> Dict[str, Any]:
        """
        计算10年ASCVD风险
        
        Args:
            age: 年龄（岁）
            gender: 性别（male/female）
            systolic_bp: 收缩压（mmHg）
            bp_treated: 是否接受降压治疗
            tc: 总胆固醇（mmol/L）
            hdl_c: 高密度脂蛋白胆固醇（mmol/L）
            diabetes: 是否有糖尿病
            smoking: 是否吸烟
            bmi: 体重指数（kg/m²）
            waist_circumference: 腰围（cm），可选
            
        Returns:
            风险评估结果字典
        """
        # 选择系数
        is_male = gender.lower() in ['male', '男']
        coeffs = self.MALE_COEFFICIENTS if is_male else self.FEMALE_COEFFICIENTS
        baseline_survival = self.BASELINE_SURVIVAL['male' if is_male else 'female']
        mean_score = self.MEAN_SCORE['male' if is_male else 'female']
        
        # 计算风险得分
        # 注意：China-PAR模型的风险得分计算较为复杂
        # 这里使用简化版本进行演示
        
        risk_score = (
            coeffs['age'] * (age / 10 - 6) +  # 年龄以10岁为单位
            coeffs['sbp_treated' if bp_treated else 'sbp_untreated'] * (systolic_bp - 120) / 10 +  # 血压以10mmHg为单位
            coeffs['tc'] * (tc - 5.0) +
            coeffs['hdl_c'] * (hdl_c - 1.3) +
            coeffs['diabetes'] * (1 if diabetes else 0) +
            coeffs['smoking'] * (1 if smoking else 0) +
            coeffs['bmi'] * (bmi - 24.0) / 5  # BMI缩放
        )
        
        # 如果有腰围数据，加入计算
        if waist_circumference:
            risk_score += coeffs['waist'] * (waist_circumference - 85)
        
        # 计算10年风险概率
        # 公式：1 - S0(t)^exp(个人风险得分 - 平均风险得分)
        import math
        
        # 限制风险得分范围，避免计算异常
        adjusted_score = risk_score - mean_score
        adjusted_score = max(-10, min(10, adjusted_score))  # 限制范围
        
        risk_probability = 1 - math.pow(
            baseline_survival,
            math.exp(adjusted_score)
        )
        
        # 转换为百分比
        risk_percentage = risk_probability * 100
        
        # 确定风险等级
        risk_level = self._get_risk_level(risk_percentage)
        
        # 计算同龄人平均风险（简化计算）
        avg_risk = self._get_age_average_risk(age, gender)
        
        # 构建结果
        self.result = {
            'risk_percentage': round(risk_percentage, 1),
            'risk_level': risk_level,
            'risk_score': round(risk_score, 2),
            'comparison': {
                'age_average_risk': avg_risk,
                'difference': round(risk_percentage - avg_risk, 1),
                'relative_risk': round(risk_percentage / avg_risk, 2) if avg_risk > 0 else 0
            },
            'input_data': {
                'age': age,
                'gender': gender,
                'systolic_bp': systolic_bp,
                'bp_treated': bp_treated,
                'tc': tc,
                'hdl_c': hdl_c,
                'diabetes': diabetes,
                'smoking': smoking,
                'bmi': bmi,
                'waist_circumference': waist_circumference
            },
            'calculated_at': datetime.now().isoformat()
        }
        
        return self.result
    
    def _get_risk_level(self, percentage: float) -> Dict[str, Any]:
        """确定风险等级"""
        if percentage < self.RISK_LEVELS['low']['threshold']:
            level = 'low'
        elif percentage < self.RISK_LEVELS['medium']['threshold']:
            level = 'medium'
        else:
            level = 'high'
        
        return {
            'level': level,
            'label': self.RISK_LEVELS[level]['label'],
            'threshold': self.RISK_LEVELS[level]['threshold']
        }
    
    def _get_age_average_risk(self, age: int, gender: str) -> float:
        """
        获取同龄人平均风险（简化估算）
        基于年龄的粗略估算，实际应参考流行病学数据
        """
        is_male = gender.lower() in ['male', '男']
        
        # 简化的年龄-风险对照表（10年ASCVD风险百分比）
        # 数据来源：China-PAR研究
        age_risk_table = {
            'male': {
                40: 2.0, 45: 3.0, 50: 4.5, 55: 6.5, 60: 9.0, 65: 12.0, 70: 16.0, 75: 21.0
            },
            'female': {
                40: 1.0, 45: 1.5, 50: 2.5, 55: 4.0, 60: 6.0, 65: 9.0, 70: 13.0, 75: 18.0
            }
        }
        
        gender_key = 'male' if is_male else 'female'
        risk_table = age_risk_table[gender_key]
        
        # 找到最接近的年龄组
        age_groups = sorted(risk_table.keys())
        lower_age = max([a for a in age_groups if a <= age])
        upper_age = min([a for a in age_groups if a >= age])
        
        if lower_age == upper_age:
            return risk_table[lower_age]
        
        # 线性插值
        lower_risk = risk_table[lower_age]
        upper_risk = risk_table[upper_age]
        ratio = (age - lower_age) / (upper_age - lower_age)
        
        return lower_risk + ratio * (upper_risk - lower_risk)
    
    def calculate_from_file(self, input_path: str) -> Dict[str, Any]:
        """从文件读取数据并计算风险"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {input_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {str(e)}")
        
        # 提取计算所需数据
        patient_info = data.get('patient_info', {})
        metrics = data.get('health_metrics', {})
        risk_assessment = data.get('risk_assessment', {})
        
        # 判断是否有糖尿病
        diabetes = False
        if 'blood_glucose' in risk_assessment:
            diabetes = risk_assessment['blood_glucose'].get('level') in ['糖尿病', 'diabetes']
        elif 'blood_glucose' in metrics:
            bg = metrics['blood_glucose']
            fasting = bg.get('fasting', 0)
            diabetes = fasting >= 7.0
        
        # 判断是否降压治疗
        bp_treated = False
        if 'blood_pressure' in risk_assessment:
            bp_treated = risk_assessment['blood_pressure'].get('level', '').startswith('高血压')
        
        # 判断是否吸烟（默认为否，可从additional_data获取）
        smoking = data.get('additional_data', {}).get('smoking', False)
        
        return self.calculate_risk(
            age=patient_info.get('age', 50),
            gender=patient_info.get('gender', 'male'),
            systolic_bp=metrics.get('blood_pressure', {}).get('systolic', 120),
            bp_treated=bp_treated,
            tc=metrics.get('blood_lipid', {}).get('tc', 5.0),
            hdl_c=metrics.get('blood_lipid', {}).get('hdl_c', 1.3),
            diabetes=diabetes,
            smoking=smoking,
            bmi=metrics.get('bmi', {}).get('value', 24.0),
            waist_circumference=metrics.get('bmi', {}).get('waist_circumference')
        )
    
    def save_result(self, output_path: str = 'china_par_result.json'):
        """保存计算结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.result, f, ensure_ascii=False, indent=2)
        print(f"China-PAR计算结果已保存至: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='China-PAR心血管风险预测计算')
    parser.add_argument('--input', help='输入健康数据文件路径')
    parser.add_argument('--output', default='china_par_result.json', help='输出结果文件路径')
    parser.add_argument('--age', type=int, help='年龄')
    parser.add_argument('--gender', choices=['male', 'female', '男', '女'], help='性别')
    parser.add_argument('--systolic', type=float, help='收缩压(mmHg)')
    parser.add_argument('--bp-treated', action='store_true', help='是否降压治疗')
    parser.add_argument('--tc', type=float, help='总胆固醇(mmol/L)')
    parser.add_argument('--hdl-c', type=float, help='HDL-C(mmol/L)')
    parser.add_argument('--diabetes', action='store_true', help='是否有糖尿病')
    parser.add_argument('--smoking', action='store_true', help='是否吸烟')
    parser.add_argument('--bmi', type=float, help='BMI(kg/m²)')
    parser.add_argument('--waist', type=float, help='腰围(cm)')
    
    args = parser.parse_args()
    
    calculator = ChinaPARCalculator()
    
    try:
        if args.input:
            # 从文件计算
            result = calculator.calculate_from_file(args.input)
        elif args.age and args.gender:
            # 从参数计算
            result = calculator.calculate_risk(
                age=args.age,
                gender=args.gender,
                systolic_bp=args.systolic or 120,
                bp_treated=args.bp_treated,
                tc=args.tc or 5.0,
                hdl_c=args.hdl_c or 1.3,
                diabetes=args.diabetes,
                smoking=args.smoking,
                bmi=args.bmi or 24.0,
                waist_circumference=args.waist
            )
        else:
            print("请提供--input文件路径或完整的参数（--age, --gender等）")
            return 1
        
        print("\n=== China-PAR风险评估结果 ===")
        print(f"10年ASCVD发病风险: {result['risk_percentage']}%")
        print(f"风险等级: {result['risk_level']['label']}")
        print(f"同龄人平均风险: {result['comparison']['age_average_risk']:.1f}%")
        print(f"相对风险: {result['comparison']['relative_risk']}倍")
        
        calculator.save_result(args.output)
        return 0
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
