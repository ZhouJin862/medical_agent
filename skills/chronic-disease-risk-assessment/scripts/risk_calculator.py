#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险评估计算引擎

功能：
1. 计算各项健康指标的风险等级
2. 进行综合风险评分
3. 生成风险评估报告数据

评估原则：
- 所有评估必须基于真实健康数据，禁止主观臆断
- 评估标准严格遵循循证医学：国标/行标/临床最佳实践
- 所有结论需注明参考标准和证据来源
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple


class RiskCalculator:
    """风险评估计算器
    
    评估原则：
    1. 真实性：所有评估基于真实健康数据
    2. 循证性：评估标准遵循循证医学
    3. 可追溯：所有结论可追溯至医学标准
    """
    
    # 评估标准来源
    ASSESSMENT_STANDARDS = {
        'blood_pressure': {
            'standard': '《中国高血压防治指南2018年修订版》',
            'organization': '中国高血压联盟',
            'type': '国家标准'
        },
        'blood_glucose': {
            'standard': '《中国2型糖尿病防治指南2020年版》',
            'organization': '中华医学会糖尿病学分会',
            'type': '国家标准'
        },
        'blood_lipid': {
            'standard': '《中国成人血脂异常防治指南2016年修订版》',
            'organization': '中国成人血脂异常防治指南修订联合委员会',
            'type': '行业标准'
        },
        'uric_acid': {
            'standard': '《中国高尿酸血症与痛风诊疗指南2019》',
            'organization': '中华医学会内分泌学分会',
            'type': '行业标准'
        },
        'bmi': {
            'standard': '《中国成人超重和肥胖症预防控制指南》',
            'organization': '中国营养学会',
            'type': '国家标准'
        },
        'china_par': {
            'standard': '《中国心血管病风险评估和管理指南2019》',
            'organization': '中国心血管病风险评估和管理指南编写委员会',
            'type': '临床最佳实践'
        }
    }
    
    # 血压风险分层标准
    BLOOD_PRESSURE_LEVELS = {
        'normal': {
            'range': (0, 0),  # 收缩压<120 且 舒张压<80
            'level': '正常',
            'score': 1,
            'description': '血压水平正常'
        },
        'high_normal': {
            'range': (120, 139),  # 收缩压120-139 或 舒张压80-89
            'level': '正常高值',
            'score': 2,
            'description': '血压偏高，需注意监测'
        },
        'hypertension_1': {
            'range': (140, 159),  # 收缩压140-159 或 舒张压90-99
            'level': '高血压1级',
            'score': 3,
            'description': '轻度高血压，建议改善生活方式'
        },
        'hypertension_2': {
            'range': (160, 179),  # 收缩压160-179 或 舒张压100-109
            'level': '高血压2级',
            'score': 4,
            'description': '中度高血压，需要药物治疗'
        },
        'hypertension_3': {
            'range': (180, 999),  # 收缩压≥180 或 舒张压≥110
            'level': '高血压3级',
            'score': 5,
            'description': '重度高血压，需立即就医'
        }
    }
    
    # 血糖风险分层标准
    BLOOD_GLUCOSE_LEVELS = {
        'normal': {
            'fasting_range': (0, 6.0),
            'hba1c_range': (0, 5.7),
            'level': '正常',
            'score': 1,
            'description': '血糖代谢正常'
        },
        'prediabetes': {
            'fasting_range': (6.1, 6.9),
            'hba1c_range': (5.7, 6.4),
            'level': '糖尿病前期',
            'score': 2,
            'description': '糖尿病前期，建议生活方式干预'
        },
        'diabetes_early': {
            'fasting_range': (7.0, 8.0),
            'hba1c_range': (6.5, 7.0),
            'level': '糖尿病早期',
            'score': 3,
            'description': '糖尿病早期，需要规范治疗'
        },
        'diabetes_moderate': {
            'fasting_range': (8.1, 10.0),
            'hba1c_range': (7.1, 8.5),
            'level': '糖尿病（血糖控制不佳）',
            'score': 4,
            'description': '糖尿病，血糖控制不佳，需调整治疗方案'
        },
        'diabetes_severe': {
            'fasting_range': (10.1, 999),
            'hba1c_range': (8.6, 999),
            'level': '糖尿病（血糖控制很差）',
            'score': 5,
            'description': '糖尿病，血糖控制很差，并发症风险高'
        }
    }

    # 糖尿病并发症风险评估标准
    DIABETES_COMPLICATION_RISK = {
        'low': {
            'hba1c_threshold': 7.0,
            'duration_years': 0,
            'risk_level': '低风险',
            'recommendation': '保持良好的血糖控制，定期复查'
        },
        'moderate': {
            'hba1c_threshold': 8.0,
            'duration_years': 5,
            'risk_level': '中等风险',
            'recommendation': '加强血糖监测，筛查早期并发症'
        },
        'high': {
            'hba1c_threshold': 9.0,
            'duration_years': 10,
            'risk_level': '高风险',
            'recommendation': '积极降糖治疗，全面并发症筛查'
        }
    }
    
    # 血脂风险评估标准
    BLOOD_LIPID_STANDARDS = {
        'tc': {
            'normal': (0, 5.17),
            'borderline': (5.18, 6.18),
            'high': (6.19, 999)
        },
        'tg': {
            'normal': (0, 1.69),
            'borderline': (1.70, 2.25),
            'high': (2.26, 999)
        },
        'ldl_c': {
            'optimal': (0, 2.58),
            'near_optimal': (2.59, 3.34),
            'borderline': (3.35, 4.12),
            'high': (4.13, 4.89),
            'very_high': (4.90, 999)
        },
        'hdl_c': {
            'low': (0, 1.03),  # 男性<1.04为低
            'normal': (1.04, 1.55),
            'high': (1.56, 999)
        }
    }
    
    # 尿酸风险评估标准
    URIC_ACID_LEVELS = {
        'male': {
            'normal': (0, 416),
            'high': (417, 999)
        },
        'female': {
            'normal': (0, 357),
            'high': (358, 999)
        }
    }
    
    # BMI评估标准
    BMI_LEVELS = {
        'underweight': {
            'range': (0, 18.4),
            'level': '体重过低',
            'score': 2,
            'description': 'BMI偏低，需关注营养状况'
        },
        'normal': {
            'range': (18.5, 23.9),
            'level': '正常',
            'score': 1,
            'description': 'BMI正常'
        },
        'overweight': {
            'range': (24.0, 27.9),
            'level': '超重',
            'score': 2,
            'description': 'BMI偏高，建议控制体重'
        },
        'obesity_1': {
            'range': (28.0, 32.9),
            'level': '肥胖I级',
            'score': 3,
            'description': '肥胖，需积极减重'
        },
        'obesity_2': {
            'range': (33.0, 37.9),
            'level': '肥胖II级',
            'score': 4,
            'description': '中度肥胖，需医学干预'
        },
        'obesity_3': {
            'range': (38.0, 999),
            'level': '肥胖III级',
            'score': 5,
            'description': '重度肥胖，需积极治疗'
        }
    }
    
    def __init__(self):
        self.risk_assessment = {}
        self.patient_info = {}
    
    def calculate_from_file(self, input_path: str) -> Dict[str, Any]:
        """从文件读取数据并计算风险"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {input_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {str(e)}")
        
        return self.calculate_risk(data)
    
    def calculate_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算风险评估

        Args:
            data: 包含patient_info和health_metrics的字典

        Returns:
            风险评估结果字典
        """
        # Debug: Write input data
        try:
            debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_risk_calculator_input.txt")
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(f"Input keys: {list(data.keys())}\n")
                hm = data.get('health_metrics', {})
                f.write(f"health_metrics keys: {list(hm.keys()) if isinstance(hm, dict) else 'N/A'}\n")
                if 'blood_pressure' in hm:
                    f.write(f"blood_pressure: {hm['blood_pressure']}\n")
        except:
            pass

        self.patient_info = data.get('patient_info', {})
        health_metrics = data.get('health_metrics', {})
        
        self.risk_assessment = {
            'patient_info': self.patient_info,
            'assessment_date': datetime.now().strftime('%Y-%m-%d'),
            'risk_assessment': {},
            'overall_risk': {}
        }
        
        # 计算各项指标风险
        self.risk_assessment['risk_assessment'] = {
            'blood_pressure': self._assess_blood_pressure(health_metrics.get('blood_pressure', {})),
            'blood_glucose': self._assess_blood_glucose(health_metrics.get('blood_glucose', {})),
            'blood_lipid': self._assess_blood_lipid(health_metrics.get('blood_lipid', {})),
            'uric_acid': self._assess_uric_acid(
                health_metrics.get('uric_acid'),
                self.patient_info.get('gender', 'male')
            ),
            'bmi': self._assess_bmi(health_metrics.get('bmi', {}))
        }
        
        # 计算综合风险
        self.risk_assessment['overall_risk'] = self._calculate_overall_risk()
        
        return self.risk_assessment
    
    def _assess_blood_pressure(self, bp_data: Dict[str, float]) -> Dict[str, Any]:
        """评估血压风险

        根据《中国高血压防治指南2018年修订版》：
        - 当收缩压和舒张压分属不同级别时，以较高的分级为准
        """
        if not bp_data:
            return {'level': '未评估', 'score': 0, 'description': '缺少血压数据'}

        systolic = bp_data.get('systolic', 0)
        diastolic = bp_data.get('diastolic', 0)

        # 分别评估收缩压和舒张压的等级
        def _get_systolic_level(sys_val):
            if sys_val < 120:
                return self.BLOOD_PRESSURE_LEVELS['normal']
            elif sys_val < 140:
                return self.BLOOD_PRESSURE_LEVELS['high_normal']
            elif sys_val < 160:
                return self.BLOOD_PRESSURE_LEVELS['hypertension_1']
            elif sys_val < 180:
                return self.BLOOD_PRESSURE_LEVELS['hypertension_2']
            else:
                return self.BLOOD_PRESSURE_LEVELS['hypertension_3']

        def _get_diastolic_level(dia_val):
            if dia_val < 80:
                return self.BLOOD_PRESSURE_LEVELS['normal']
            elif dia_val < 90:
                return self.BLOOD_PRESSURE_LEVELS['high_normal']
            elif dia_val < 100:
                return self.BLOOD_PRESSURE_LEVELS['hypertension_1']
            elif dia_val < 110:
                return self.BLOOD_PRESSURE_LEVELS['hypertension_2']
            else:
                return self.BLOOD_PRESSURE_LEVELS['hypertension_3']

        systolic_level = _get_systolic_level(systolic)
        diastolic_level = _get_diastolic_level(diastolic)

        # 取较高的等级（分数更高的为准）
        level_info = systolic_level if systolic_level['score'] >= diastolic_level['score'] else diastolic_level

        return {
            'level': level_info['level'],
            'score': level_info['score'],
            'description': level_info['description'],
            'values': {
                'systolic': systolic,
                'diastolic': diastolic
            }
        }
    
    def _assess_blood_glucose(self, bg_data: Dict[str, float]) -> Dict[str, Any]:
        """评估血糖风险

        根据《中国2型糖尿病防治指南2020年版》：
        - 综合评估空腹血糖、餐后血糖和糖化血红蛋白(HbA1c)
        - 以最高风险等级为准
        - HbA1c ≥ 6.5% 可诊断糖尿病
        - HbA1c ≥ 9.0% 表示血糖控制很差
        """
        if not bg_data or ('fasting' not in bg_data and 'hba1c' not in bg_data):
            return {'level': '未评估', 'score': 0, 'description': '缺少血糖数据'}

        fasting = bg_data.get('fasting')
        postprandial = bg_data.get('postprandial')
        hba1c = bg_data.get('hba1c')

        # 初始等级为正常
        max_score = 1
        level_info = self.BLOOD_GLUCOSE_LEVELS['normal']
        descriptions = []

        # 评估空腹血糖
        if fasting is not None:
            if fasting < 6.1:
                fasting_level = self.BLOOD_GLUCOSE_LEVELS['normal']
            elif 6.1 <= fasting < 7.0:
                fasting_level = self.BLOOD_GLUCOSE_LEVELS['prediabetes']
            elif 7.0 <= fasting < 10.0:
                fasting_level = self.BLOOD_GLUCOSE_LEVELS['diabetes_early']
            else:
                fasting_level = self.BLOOD_GLUCOSE_LEVELS['diabetes_severe']

            if fasting_level['score'] > max_score:
                max_score = fasting_level['score']
                level_info = fasting_level

        # 评估餐后血糖
        if postprandial is not None and postprandial >= 7.8:
            if postprandial >= 11.1:
                postprandial_level = self.BLOOD_GLUCOSE_LEVELS['diabetes_early']
            else:
                postprandial_level = self.BLOOD_GLUCOSE_LEVELS['prediabetes']

            if postprandial_level['score'] > max_score:
                max_score = postprandial_level['score']
                level_info = postprandial_level

        # 评估糖化血红蛋白 (HbA1c)
        # 根据《中国2型糖尿病防治指南2020年版》
        if hba1c is not None:
            if hba1c < 5.7:
                hba1c_level = self.BLOOD_GLUCOSE_LEVELS['normal']
                hba1c_desc = f'HbA1c正常（{hba1c}%）'
            elif hba1c < 6.5:
                hba1c_level = self.BLOOD_GLUCOSE_LEVELS['prediabetes']
                hba1c_desc = f'HbA1c偏高（{hba1c}%），糖尿病前期风险'
            elif hba1c < 7.5:
                hba1c_level = self.BLOOD_GLUCOSE_LEVELS['diabetes_early']
                hba1c_desc = f'HbA1c达到糖尿病诊断标准（{hba1c}%），糖尿病早期'
            elif hba1c < 9.0:
                hba1c_level = self.BLOOD_GLUCOSE_LEVELS['diabetes_moderate']
                hba1c_desc = f'HbA1c升高（{hba1c}%），血糖控制不佳'
            else:
                hba1c_level = self.BLOOD_GLUCOSE_LEVELS['diabetes_severe']
                hba1c_desc = f'HbA1c严重升高（{hba1c}%），血糖控制很差'

            if hba1c_level['score'] > max_score:
                max_score = hba1c_level['score']
                level_info = hba1c_level
            descriptions.append(hba1c_desc)

        # 组合描述
        final_description = level_info['description']
        # 如果level_info的description已经包含了HbA1c信息，不再添加
        if descriptions and 'HbA1c' not in level_info.get('description', ''):
            final_description += f"（{'; '.join(descriptions)}）"

        # 评估糖尿病并发症风险（仅对确诊糖尿病患者）
        complications_risk = None
        if hba1c is not None and hba1c >= 6.5:
            if hba1c < 7.5:
                complications_risk = self.DIABETES_COMPLICATION_RISK['low']['risk_level']
                complications_recommendation = self.DIABETES_COMPLICATION_RISK['low']['recommendation']
            elif hba1c < 9.0:
                complications_risk = self.DIABETES_COMPLICATION_RISK['moderate']['risk_level']
                complications_recommendation = self.DIABETES_COMPLICATION_RISK['moderate']['recommendation']
            else:
                complications_risk = self.DIABETES_COMPLICATION_RISK['high']['risk_level']
                complications_recommendation = self.DIABETES_COMPLICATION_RISK['high']['recommendation']
        else:
            complications_recommendation = ''

        return {
            'level': level_info['level'],
            'score': level_info['score'],
            'description': final_description,
            'complications_risk': complications_risk,
            'recommendation': complications_recommendation,
            'values': {
                'fasting': fasting,
                'postprandial': postprandial,
                'hba1c': hba1c
            }
        }
    
    def _assess_blood_lipid(self, lipid_data: Dict[str, float]) -> Dict[str, Any]:
        """评估血脂风险"""
        if not lipid_data:
            return {'level': '未评估', 'score': 0, 'description': '缺少血脂数据'}
        
        tc = lipid_data.get('tc', 0)
        tg = lipid_data.get('tg', 0)
        ldl_c = lipid_data.get('ldl_c', 0)
        hdl_c = lipid_data.get('hdl_c', 0)
        
        # 评估各项血脂指标
        risk_factors = []
        total_score = 0
        
        # TC评估
        if tc >= self.BLOOD_LIPID_STANDARDS['tc']['high'][0]:
            risk_factors.append('TC升高')
            total_score += 2
        elif tc >= self.BLOOD_LIPID_STANDARDS['tc']['borderline'][0]:
            risk_factors.append('TC边缘升高')
            total_score += 1
        
        # TG评估
        if tg >= self.BLOOD_LIPID_STANDARDS['tg']['high'][0]:
            risk_factors.append('TG升高')
            total_score += 2
        elif tg >= self.BLOOD_LIPID_STANDARDS['tg']['borderline'][0]:
            risk_factors.append('TG边缘升高')
            total_score += 1
        
        # LDL-C评估
        if ldl_c >= self.BLOOD_LIPID_STANDARDS['ldl_c']['very_high'][0]:
            risk_factors.append('LDL-C显著升高')
            total_score += 3
        elif ldl_c >= self.BLOOD_LIPID_STANDARDS['ldl_c']['high'][0]:
            risk_factors.append('LDL-C升高')
            total_score += 2
        elif ldl_c >= self.BLOOD_LIPID_STANDARDS['ldl_c']['borderline'][0]:
            risk_factors.append('LDL-C边缘升高')
            total_score += 1
        
        # HDL-C评估
        gender = self.patient_info.get('gender', 'male')
        hdl_threshold = 1.03 if gender in ['male', '男'] else 1.29
        if hdl_c < hdl_threshold:
            risk_factors.append('HDL-C降低')
            total_score += 1
        
        # 确定总体风险等级
        if total_score == 0:
            level = '正常'
            score = 1
            description = '血脂各项指标正常'
        elif total_score <= 2:
            level = '血脂边缘异常'
            score = 2
            description = '部分血脂指标轻度异常'
        elif total_score <= 4:
            level = '血脂异常'
            score = 3
            description = '多项血脂指标异常'
        else:
            level = '血脂显著异常'
            score = 4
            description = '血脂多项指标显著异常'
        
        return {
            'level': level,
            'score': score,
            'description': f"{description}（{', '.join(risk_factors)}）" if risk_factors else description,
            'values': {
                'tc': tc,
                'tg': tg,
                'ldl_c': ldl_c,
                'hdl_c': hdl_c
            }
        }
    
    def _assess_uric_acid(self, uric_acid: float, gender: str) -> Dict[str, Any]:
        """评估尿酸风险"""
        if uric_acid is None:
            return {'level': '未评估', 'score': 0, 'description': '缺少尿酸数据'}
        
        gender_key = 'male' if gender in ['male', '男'] else 'female'
        normal_range = self.URIC_ACID_LEVELS[gender_key]['normal']
        high_range = self.URIC_ACID_LEVELS[gender_key]['high']
        
        if uric_acid <= normal_range[1]:
            level = '正常'
            score = 1
            description = '尿酸水平正常'
        else:
            level = '高尿酸血症'
            score = 2
            description = '尿酸水平升高，需关注痛风风险'
        
        return {
            'level': level,
            'score': score,
            'description': description,
            'values': {
                'uric_acid': uric_acid
            }
        }
    
    def _assess_bmi(self, bmi_data: Dict[str, float]) -> Dict[str, Any]:
        """评估BMI风险"""
        if not bmi_data:
            return {'level': '未评估', 'score': 0, 'description': '缺少BMI数据'}

        # 如果没有预计算的BMI值，从身高体重计算
        bmi = bmi_data.get('value')
        if bmi is None:
            height = bmi_data.get('height', 0)
            weight = bmi_data.get('weight', 0)
            if height > 0 and weight > 0:
                # BMI = kg / m²
                bmi = round(weight / (height * height), 2)
            else:
                return {'level': '未评估', 'score': 0, 'description': '缺少BMI数据'}
        
        # 判断BMI等级
        for level_key, level_info in self.BMI_LEVELS.items():
            if level_info['range'][0] <= bmi <= level_info['range'][1]:
                return {
                    'level': level_info['level'],
                    'score': level_info['score'],
                    'description': f"{level_info['description']}（BMI {bmi:.1f} kg/m²）",
                    'values': {
                        'bmi': bmi,
                        'height': bmi_data.get('height'),
                        'weight': bmi_data.get('weight')
                    }
                }
        
        return {'level': '未评估', 'score': 0, 'description': 'BMI值异常'}
    
    def _calculate_overall_risk(self) -> Dict[str, Any]:
        """计算综合风险"""
        assessments = self.risk_assessment['risk_assessment']
        
        # 计算总分
        total_score = sum(
            assessment.get('score', 0)
            for assessment in assessments.values()
        )
        
        # 确定风险等级
        if total_score <= 5:
            risk_grade = '低风险'
            priority = '定期监测'
        elif total_score <= 10:
            risk_grade = '中低风险'
            priority = '加强监测，改善生活方式'
        elif total_score <= 15:
            risk_grade = '中风险'
            priority = '积极干预，改善生活方式'
        elif total_score <= 20:
            risk_grade = '中高风险'
            priority = '需要积极干预，考虑药物治疗'
        else:
            risk_grade = '高风险'
            priority = '需要立即就医，综合治疗'
        
        # 统计异常项
        abnormal_items = [
            key for key, assessment in assessments.items()
            if assessment.get('score', 0) > 1
        ]
        
        return {
            'total_score': total_score,
            'max_score': 25,
            'risk_grade': risk_grade,
            'priority': priority,
            'abnormal_items': abnormal_items,
            'abnormal_count': len(abnormal_items)
        }
    
    def save_assessment(self, output_path: str = 'risk_assessment.json'):
        """保存风险评估结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.risk_assessment, f, ensure_ascii=False, indent=2)
        print(f"风险评估结果已保存至: {output_path}")


def main():
    # UTF-8 encoding fix for Windows
    import io

    parser = argparse.ArgumentParser(description='健康风险评估计算')
    parser.add_argument('--input', required=True, help='输入验证后的健康数据文件路径')
    parser.add_argument('--output', default='risk_assessment.json', help='输出风险评估文件路径')
    parser.add_argument('--json-output', action='store_true', help='以JSON格式输出到stdout（用于脚本间传递数据）')

    args = parser.parse_args()

    # Only wrap stdout for human-readable output (not json-output mode)
    if not args.json_output and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    calculator = RiskCalculator()

    try:
        result = calculator.calculate_from_file(args.input)

        # If json-output mode, output JSON to stdout for workflow chaining
        if args.json_output:
            output_data = {
                "success": True,
                "risk_assessment": result
            }
            # Reset stdout wrapper for JSON output
            if hasattr(sys, '_original_stdout'):
                sys.stdout = sys._original_stdout
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout.buffer.write(json.dumps(output_data, ensure_ascii=False, indent=2).encode('utf-8'))
            else:
                print(json.dumps(output_data, ensure_ascii=False, indent=2))
            return 0

        # Human-readable output mode (default)
        print("\n=== 风险评估结果 ===")
        print(f"患者: {result['patient_info'].get('name', '未知')}")
        print(f"评估日期: {result['assessment_date']}")
        print(f"\n总体风险: {result['overall_risk']['risk_grade']}")
        print(f"风险评分: {result['overall_risk']['total_score']}/{result['overall_risk']['max_score']}")
        print(f"干预优先级: {result['overall_risk']['priority']}")

        print("\n各项指标评估:")
        for key, assessment in result['risk_assessment'].items():
            print(f"  - {assessment['level']}: {assessment['description']}")

        calculator.save_assessment(args.output)
        return 0
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
