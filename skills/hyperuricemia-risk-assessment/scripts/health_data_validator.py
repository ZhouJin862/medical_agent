#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康数据验证与标准化脚本

功能：
1. 验证健康指标数据的完整性
2. 检查数值范围的合理性
3. 标准化单位转换
4. 标记异常值
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional


class HealthDataValidator:
    """健康数据验证器"""
    
    # 正常值范围参考
    NORMAL_RANGES = {
        'blood_pressure': {
            'systolic': (90, 180),      # mmHg
            'diastolic': (60, 120)      # mmHg
        },
        'blood_glucose': {
            'fasting': (3.9, 11.1),     # mmol/L
            'postprandial': (3.9, 16.7) # mmol/L
        },
        'blood_lipid': {
            'tc': (2.8, 7.8),           # mmol/L 总胆固醇
            'tg': (0.45, 5.6),          # mmol/L 甘油三酯
            'ldl_c': (1.0, 5.0),        # mmol/L 低密度脂蛋白
            'hdl_c': (0.8, 2.2)         # mmol/L 高密度脂蛋白
        },
        'uric_acid': {
            'male': (208, 428),         # μmol/L 男性
            'female': (155, 357)        # μmol/L 女性
        },
        'bmi': {
            'value': (15, 40)           # kg/m²
        }
    }
    
    # 必填字段（最小评估数据集 - 12项必采指标）
    REQUIRED_FIELDS = {
        'patient_info': ['age'],
        'health_metrics': {
            'basic': ['height', 'weight', 'waist_circumference'],  # 基础体格3项
            'blood_pressure': ['systolic', 'diastolic'],  # 血压2项
            'blood_glucose': ['fasting_glucose', 'hba1c'],  # 糖代谢2项（含HbA1c）
            'blood_lipid': ['tc', 'tg', 'ldl_c', 'hdl_c'],  # 脂代谢4项
            'kidney': ['uric_acid']  # 尿酸1项
        }
    }
    
    # 推荐采集字段（标准评估数据集）
    RECOMMENDED_FIELDS = {
        'health_metrics': {
            'kidney': ['egfr', 'uacr']  # 肾功能评估
        },
        'lifestyle': {
            'smoking': ['history']  # China-PAR模型核心因子
        }
    }
    
    # 可选字段（完整评估数据集）
    OPTIONAL_FIELDS = {
        'health_metrics': {
            'basic': ['body_fat_rate', 'visceral_fat_level'],
            'blood_pressure': ['heart_rate'],
            'blood_glucose': ['ogtt_2h'],
            'blood_lipid': ['non_hdl_c', 'lp_a'],
            'kidney': ['serum_creatinine', 'bun'],
            'other_metabolism': ['homocysteine', 'alt', 'ast']
        },
        'clinical_examination': {
            'carotid_ultrasound': ['imt', 'plaque'],
            'abdominal_ultrasound': ['fatty_liver'],
            'ecg': None,
            'echocardiography': None,
            'fundus_photography': None
        },
        'lifestyle': {
            'smoking': ['amount', 'quit_years'],
            'alcohol': ['history', 'frequency'],
            'exercise': ['weekly_minutes', 'frequency', 'type'],
            'diet': ['salt_intake', 'sugary_drink_frequency', 'dietary_fiber'],
            'sleep': ['duration', 'snoring', 'quality'],
            'medication': ['antihypertensive', 'lipid_lowering', 'glucose_lowering', 'mpr']
        }
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validated_data = {}
    
    def validate_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        验证健康数据文件
        
        Args:
            file_path: JSON格式的健康数据文件路径
            
        Returns:
            (验证是否成功, 标准化后的数据)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.errors.append(f"文件不存在: {file_path}")
            return False, {}
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON格式错误: {str(e)}")
            return False, {}
        
        return self.validate_data(data)
    
    def validate_data(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        验证健康数据
        
        Args:
            data: 健康数据字典
            
        Returns:
            (验证是否成功, 标准化后的数据)
        """
        self.errors = []
        self.warnings = []
        self.validated_data = {}
        
        # 验证患者信息
        if not self._validate_patient_info(data):
            return False, {}
        
        # 验证健康指标
        if not self._validate_health_metrics(data):
            return False, {}
        
        # 标准化数据
        self._standardize_data(data)
        
        # 保存验证结果
        self.validated_data['validation_info'] = {
            'validated_at': datetime.now().isoformat(),
            'errors': self.errors,
            'warnings': self.warnings,
            'is_valid': len(self.errors) == 0
        }
        
        return len(self.errors) == 0, self.validated_data
    
    def _validate_patient_info(self, data: Dict[str, Any]) -> bool:
        """验证患者基本信息"""
        if 'patient_info' not in data:
            self.errors.append("缺少患者信息(patient_info)")
            return False
        
        patient_info = data['patient_info']
        
        for field in self.REQUIRED_FIELDS['patient_info']:
            if field not in patient_info:
                self.errors.append(f"患者信息缺少必填字段: {field}")
            elif patient_info[field] is None:
                self.warnings.append(f"患者信息字段未提供: {field}，将使用默认值")
            elif not patient_info[field]:
                self.errors.append(f"患者信息字段不能为空: {field}")

        # 验证年龄范围
        if 'age' in patient_info:
            age = patient_info['age']
            try:
                age = float(age)
            except (TypeError, ValueError):
                self.errors.append(f"年龄值不合理: {age}")
                age = None
            if age is not None and (age < 0 or age > 150):
                self.errors.append(f"年龄值不合理: {age}")

        # 验证性别
        if 'gender' in patient_info and patient_info['gender'] is not None:
            gender = patient_info['gender'].lower()
            if gender not in ['male', 'female', '男', '女']:
                self.warnings.append(f"性别值异常: {patient_info['gender']}")
        elif 'gender' in patient_info:
            self.warnings.append("性别未提供，将使用默认值进行评估")
        
        self.validated_data['patient_info'] = patient_info.copy()
        return len(self.errors) == 0
    
    def _validate_health_metrics(self, data: Dict[str, Any]) -> bool:
        """验证健康指标数据"""
        if 'health_metrics' not in data:
            self.errors.append("缺少健康指标数据(health_metrics)")
            return False
        
        metrics = data['health_metrics']
        
        # 验证血压
        if 'blood_pressure' in metrics:
            bp = metrics['blood_pressure']
            if not self._validate_dict_fields(bp, ['systolic', 'diastolic'], '血压'):
                pass
            else:
                self._check_range(bp['systolic'], 'systolic', '血压-收缩压')
                self._check_range(bp['diastolic'], 'diastolic', '血压-舒张压')
        else:
            self.errors.append("缺少血压数据(blood_pressure)")
        
        # 验证血糖
        if 'blood_glucose' in metrics:
            bg = metrics['blood_glucose']
            if 'fasting' not in bg:
                self.errors.append("缺少空腹血糖数据(fasting)")
            else:
                self._check_range(bg['fasting'], 'fasting', '空腹血糖')
                if 'postprandial' in bg:
                    self._check_range(bg['postprandial'], 'postprandial', '餐后血糖')
        else:
            self.errors.append("缺少血糖数据(blood_glucose)")
        
        # 验证血脂
        if 'blood_lipid' in metrics:
            lipid = metrics['blood_lipid']
            required_lipid = ['tc', 'tg', 'ldl_c', 'hdl_c']
            if self._validate_dict_fields(lipid, required_lipid, '血脂'):
                for field in required_lipid:
                    self._check_range(lipid[field], field, f'血脂-{field}')
        else:
            self.errors.append("缺少血脂数据(blood_lipid)")
        
        # 验证尿酸
        if 'uric_acid' in metrics:
            ua = metrics['uric_acid']
            gender = data.get('patient_info', {}).get('gender', 'male')
            gender_key = 'male' if gender in ['male', '男'] else 'female'
            range_key = gender_key
            self._check_uric_acid(ua, range_key)
        else:
            self.errors.append("缺少尿酸数据(uric_acid)")
        
        # 验证BMI
        if 'bmi' in metrics:
            bmi_data = metrics['bmi']
            # 支持三种格式：数值、字典{value}、字典{height, weight}
            if isinstance(bmi_data, dict):
                if 'value' in bmi_data and bmi_data['value'] is not None:
                    bmi_val = bmi_data['value']
                    if isinstance(bmi_val, (int, float)) and (bmi_val < 10 or bmi_val > 50):
                        self.warnings.append(f"BMI值异常: {bmi_val}")
                elif 'height' in bmi_data and 'weight' in bmi_data:
                    self._validate_bmi(bmi_data['height'], bmi_data['weight'])
                else:
                    self.warnings.append("BMI数据不完整，缺少value或height/weight字段")
            elif isinstance(bmi_data, (int, float)):
                # 直接提供BMI数值，验证合理性
                if bmi_data < 10 or bmi_data > 50:
                    self.errors.append(f"BMI值异常: {bmi_data}")
            else:
                self.errors.append(f"BMI数据格式错误: {type(bmi_data)}")
        else:
            self.errors.append("缺少BMI数据(bmi)")
        
        return len(self.errors) == 0
    
    def _validate_dict_fields(self, data: Dict, required: List[str], field_name: str) -> bool:
        """验证字典字段完整性"""
        for field in required:
            if field not in data:
                self.errors.append(f"{field_name}缺少字段: {field}")
                return False
        return True
    
    def _check_range(self, value: float, range_key: str, field_name: str):
        """检查数值范围"""
        try:
            value = float(value)
        except (TypeError, ValueError):
            self.errors.append(f"{field_name}值无效: {value}")
            return
        
        # 特殊处理不同指标的范围
        if range_key in ['systolic', 'diastolic']:
            min_val, max_val = self.NORMAL_RANGES['blood_pressure'][range_key]
        elif range_key == 'fasting':
            min_val, max_val = self.NORMAL_RANGES['blood_glucose']['fasting']
        elif range_key == 'postprandial':
            min_val, max_val = self.NORMAL_RANGES['blood_glucose']['postprandial']
        elif range_key in ['tc', 'tg', 'ldl_c', 'hdl_c']:
            min_val, max_val = self.NORMAL_RANGES['blood_lipid'][range_key]
        else:
            return
        
        if value < min_val or value > max_val:
            self.warnings.append(f"{field_name}值超出正常范围: {value} (正常范围: {min_val}-{max_val})")
    
    def _check_uric_acid(self, value: float, gender_key: str):
        """检查尿酸值"""
        try:
            value = float(value)
        except (TypeError, ValueError):
            self.errors.append(f"尿酸值无效: {value}")
            return
        
        min_val, max_val = self.NORMAL_RANGES['uric_acid'][gender_key]
        
        if value < min_val or value > max_val:
            self.warnings.append(f"尿酸值超出正常范围: {value} μmol/L (正常范围: {min_val}-{max_val})")
    
    def _validate_bmi(self, height: float, weight: float):
        """验证BMI相关数据"""
        try:
            height = float(height)
            weight = float(weight)
        except (TypeError, ValueError):
            self.errors.append("身高或体重值无效")
            return
        
        # 检查身高范围（单位：米）
        if height < 1.0 or height > 2.5:
            self.errors.append(f"身高值不合理: {height}米 (正常范围: 1.0-2.5米)")
        
        # 检查体重范围（单位：千克）
        if weight < 20 or weight > 200:
            self.errors.append(f"体重值不合理: {weight}千克 (正常范围: 20-200千克)")
        
        # 计算BMI
        if height > 0:
            bmi = weight / (height ** 2)
            if bmi < 15 or bmi > 40:
                self.warnings.append(f"BMI值异常: {bmi:.2f} kg/m² (正常范围: 15-40 kg/m²)")
    
    def _standardize_data(self, data: Dict[str, Any]):
        """标准化数据"""
        self.validated_data['health_metrics'] = {}
        metrics = data['health_metrics']
        
        # 标准化血压
        if 'blood_pressure' in metrics:
            self.validated_data['health_metrics']['blood_pressure'] = {
                'systolic': float(metrics['blood_pressure']['systolic']),
                'diastolic': float(metrics['blood_pressure']['diastolic'])
            }
        
        # 标准化血糖
        if 'blood_glucose' in metrics:
            bg_data = {
                'fasting': float(metrics['blood_glucose']['fasting'])
            }
            if 'postprandial' in metrics['blood_glucose']:
                bg_data['postprandial'] = float(metrics['blood_glucose']['postprandial'])
            self.validated_data['health_metrics']['blood_glucose'] = bg_data
        
        # 标准化血脂
        if 'blood_lipid' in metrics:
            lipid = metrics['blood_lipid']
            self.validated_data['health_metrics']['blood_lipid'] = {
                'tc': float(lipid['tc']),
                'tg': float(lipid['tg']),
                'ldl_c': float(lipid['ldl_c']),
                'hdl_c': float(lipid['hdl_c'])
            }
        
        # 标准化尿酸
        if 'uric_acid' in metrics:
            self.validated_data['health_metrics']['uric_acid'] = float(metrics['uric_acid'])
        
        # 标准化BMI
        if 'bmi' in metrics:
            bmi_value = metrics['bmi']
            # 支持三种格式：数值、字典{value}、字典{height, weight}
            if isinstance(bmi_value, dict):
                if 'value' in bmi_value and bmi_value['value'] is not None:
                    bmi_data = {'value': float(bmi_value['value'])}
                    if 'waist_circumference' in bmi_value:
                        bmi_data['waist_circumference'] = float(bmi_value['waist_circumference'])
                    if 'height' in bmi_value and bmi_value.get('height'):
                        bmi_data['height'] = float(bmi_value['height'])
                    if 'weight' in bmi_value and bmi_value.get('weight'):
                        bmi_data['weight'] = float(bmi_value['weight'])
                    self.validated_data['health_metrics']['bmi'] = bmi_data
                else:
                    height = float(bmi_value.get('height', 0))
                    weight = float(bmi_value.get('weight', 0))
                    if height > 0 and weight > 0:
                        bmi = weight / (height ** 2)
                        bmi_data = {
                            'height': height,
                            'weight': weight,
                            'value': round(bmi, 2)
                        }
                        if 'waist_circumference' in bmi_value:
                            bmi_data['waist_circumference'] = float(bmi_value['waist_circumference'])
                        self.validated_data['health_metrics']['bmi'] = bmi_data
                    else:
                        self.warnings.append("BMI数据不完整，缺少有效的value或height/weight")
            elif isinstance(bmi_value, (int, float)):
                # 直接提供BMI数值
                self.validated_data['health_metrics']['bmi'] = {
                    'value': float(bmi_value),
                    'height': None,
                    'weight': None
                }
            else:
                self.errors.append(f"BMI数据格式错误: {type(bmi_value)}")
        
        # 标准化血糖时添加HbA1c（如有）
        if 'blood_glucose' in self.validated_data['health_metrics']:
            if 'hba1c' in metrics['blood_glucose']:
                self.validated_data['health_metrics']['blood_glucose']['hba1c'] = float(metrics['blood_glucose']['hba1c'])
        
        # 保存额外数据（用于HE-Report增强评估）
        if 'additional_data' in data:
            self.validated_data['additional_data'] = {}
            for key, value in data['additional_data'].items():
                if value is not None:
                    self.validated_data['additional_data'][key] = value
        
        # 保存模板信息
        if 'template' in data:
            self.validated_data['template'] = data['template']
        else:
            self.validated_data['template'] = 'default'
    
    def save_validated_data(self, output_path: str = 'validated_data.json'):
        """保存验证后的数据"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.validated_data, f, ensure_ascii=False, indent=2)
        print(f"验证后的数据已保存至: {output_path}", file=sys.stderr)


def main():
    # UTF-8 encoding fix for Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    parser = argparse.ArgumentParser(description='健康数据验证与标准化')
    parser.add_argument('--input', required=True, help='输入健康数据文件路径(JSON格式)')
    parser.add_argument('--output', default='validated_data.json', help='输出文件路径')
    
    args = parser.parse_args()
    
    validator = HealthDataValidator()
    is_valid, validated_data = validator.validate_file(args.input)
    
    if is_valid:
        validator.save_validated_data(args.output)

        # 输出JSON到stdout（供SkillWorkflowExecutor捕获）
        print(json.dumps(validated_data, ensure_ascii=False, indent=2))
        return 0
    else:
        # 验证失败，返回错误信息
        error_result = {
            "success": False,
            "errors": validator.errors
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
