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
from pathlib import Path
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
            # 支持三种格式：
            # 1. 字典{value, height, weight} - 完整数据，可计算验证
            # 2. 字典{value} - 只有BMI值
            # 3. 数值 - 直接的BMI值
            if isinstance(bmi_data, dict):
                # 检查是否有value字段（直接BMI值）
                if 'value' in bmi_data:
                    bmi_value = bmi_data['value']
                    if bmi_value < 10 or bmi_value > 50:
                        self.warnings.append(f"BMI值异常: {bmi_value} (正常范围: 10-50)")
                # 检查是否有height和 weight（可验证计算）
                elif 'height' in bmi_data and 'weight' in bmi_data:
                    self._validate_bmi(bmi_data['height'], bmi_data['weight'])
                # 只有height或weight其中一个，但不完整 - 接受但不警告
                elif 'height' in bmi_data or 'weight' in bmi_data:
                    # 部分数据，不算错误，继续处理
                    pass
                else:
                    self.warnings.append("BMI数据格式不完整，缺少value或height/weight字段")
            elif isinstance(bmi_data, (int, float)):
                # 直接提供BMI数值，验证合理性
                if bmi_data < 10 or bmi_data > 50:
                    self.warnings.append(f"BMI值异常: {bmi_data} (正常范围: 10-50)")
            else:
                self.warnings.append(f"BMI数据格式无法识别: {type(bmi_data)}")
        else:
            self.errors.append("缺少BMI数据(bmi)")
        
        return len(self.errors) == 0
    
    def _validate_dict_fields(self, data: Dict, required: List[str], field_name: str) -> bool:
        """验证字典字段完整性"""
        missing = []
        for field in required:
            if field not in data:
                missing.append(field)

        if missing:
            self.errors.append(f"{field_name}缺少字段: {', '.join(missing)}")
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
                # 优先使用已计算的 value
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
        print(f"验证后的数据已保存至: {output_path}")

    def get_missing_fields(self) -> List[str]:
        """
        从错误列表中提取缺失的必填字段名称

        Returns:
            缺失字段列表（用于SKILL返回incomplete状态）
        """
        missing_fields = []

        # 先检查是否完全缺少health_metrics
        for error in self.errors:
            if "缺少健康指标数据" in error or "health_metrics" in error:
                # 返回所有必采字段
                missing_fields = [
                    "systolic_bp", "diastolic_bp",
                    "fasting_glucose",
                    "total_cholesterol", "ldl_c", "hdl_c", "tg",
                    "uric_acid",
                    "bmi"
                ]
                return missing_fields

        # 否则映射具体缺失字段
        for error in self.errors:
            # 患者信息字段
            if "患者信息缺少必填字段" in error:
                if "name" in error:
                    missing_fields.append("name")
                elif "age" in error:
                    missing_fields.append("age")
                elif "gender" in error:
                    missing_fields.append("gender")

            # 血压字段
            elif "血压缺少字段" in error:
                if "systolic" in error:
                    missing_fields.append("systolic_bp")
                if "diastolic" in error:
                    missing_fields.append("diastolic_bp")

            # 血糖字段
            elif "缺少空腹血糖" in error or "fasting" in error:
                if "fasting_glucose" not in missing_fields:
                    missing_fields.append("fasting_glucose")

            # 血脂字段
            elif "血脂缺少字段" in error or "缺少血脂数据" in error:
                lipid_fields = ["total_cholesterol", "ldl_c", "hdl_c", "tg"]
                for f in lipid_fields:
                    if f in error:
                        if f == "tc" and "total_cholesterol" not in missing_fields:
                            missing_fields.append("total_cholesterol")
                        elif f == "ldl_c" and "ldl_c" not in missing_fields:
                            missing_fields.append("ldl_c")
                        elif f == "hdl_c" and "hdl_c" not in missing_fields:
                            missing_fields.append("hdl_c")
                        elif f == "tg" and "tg" not in missing_fields:
                            missing_fields.append("tg")
                # 如果是完全缺少血脂数据，添加所有血脂字段
                if "缺少血脂数据" in error:
                    for f in lipid_fields:
                        if f not in missing_fields:
                            missing_fields.append(f)

            # 尿酸字段
            elif "缺少尿酸数据" in error:
                if "uric_acid" not in missing_fields:
                    missing_fields.append("uric_acid")

            # BMI字段 - 处理各种组合
            elif "BMI缺少字段" in error or "缺少BMI数据" in error:
                # BMI相关错误不需要添加额外字段，因为BMI值已经提供了
                # 只有当完全没有BMI数据时才需要
                if "缺少BMI数据" in error and "bmi" not in missing_fields:
                    missing_fields.append("bmi")

        # 去重并保持顺序
        seen = set()
        result = []
        for field in missing_fields:
            if field not in seen:
                seen.add(field)
                result.append(field)

        return result

    def validate_for_skill(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为SKILL执行验证数据（支持简化的输入格式）

        当数据不完整时返回incomplete状态，供agent提示用户补充

        Args:
            input_data: 从agent传入的数据，可能包含vital_signs, patient_data, medical_history

        Returns:
            {
                "success": True/False,
                "data": {
                    "status": "incomplete" / "success",
                    "message": "...",
                    "required_fields": [...],
                    "validated_data": {...}
                }
            }
        """
        # 转换输入格式到验证器期望的格式
        validator_input = self._convert_input_format(input_data)

        # 执行验证
        is_valid, validated_data = self.validate_data(validator_input)

        if not is_valid:
            # 数据不完整，返回incomplete状态
            missing_fields = self.get_missing_fields()

            # 构建当前数据展示
            current_data_parts = []
            if 'patient_info' in validator_input:
                patient_info = validator_input['patient_info']
                name = patient_info.get('name', '患者')
                age = patient_info.get('age', '?')
                gender = patient_info.get('gender', '?')
                current_data_parts.append(f"**基本信息**: {name}, {age}岁, {gender}")

            # 显示已有的体征数据
            if 'health_metrics' in validator_input:
                metrics = validator_input['health_metrics']
                existing_data = []

                if 'blood_pressure' in metrics:
                    bp = metrics['blood_pressure']
                    if 'systolic' in bp and 'diastolic' in bp:
                        existing_data.append(f"血压: {bp['systolic']}/{bp['diastolic']} mmHg")

                if 'blood_glucose' in metrics:
                    bg = metrics['blood_glucose']
                    if 'fasting' in bg:
                        existing_data.append(f"空腹血糖: {bg['fasting']} mmol/L")

                if 'blood_lipid' in metrics:
                    lipid = metrics['blood_lipid']
                    lipid_parts = []
                    if 'tc' in lipid:
                        lipid_parts.append(f"TC:{lipid['tc']}")
                    if 'tg' in lipid:
                        lipid_parts.append(f"TG:{lipid['tg']}")
                    if lipid_parts:
                        existing_data.append(f"血脂: {', '.join(lipid_parts)} mmol/L")

                if 'uric_acid' in metrics:
                    existing_data.append(f"尿酸: {metrics['uric_acid']} μmol/L")

                if 'bmi' in metrics:
                    bmi = metrics['bmi']
                    if isinstance(bmi, dict) and 'value' in bmi:
                        existing_data.append(f"BMI: {bmi['value']}")
                    elif isinstance(bmi, (int, float)):
                        existing_data.append(f"BMI: {bmi}")

                if existing_data:
                    current_data_parts.append(f"**已有数据**: {', '.join(existing_data)}")

            current_data_display = "\n\n".join(current_data_parts) if current_data_parts else "暂无数据"

            return {
                "success": True,
                "skill_name": "chronic-disease-risk-assessment",
                "data": {
                    "status": "incomplete",
                    "current_data": current_data_display,
                    "message": f"需要补充健康数据才能进行评估\n\n{current_data_display}",
                    "required_fields": missing_fields
                }
            }

        # 验证通过，返回标准化数据
        return {
            "success": True,
            "skill_name": "chronic-disease-risk-assessment",
            "data": {
                "status": "validated",
                "validated_data": validated_data,
                "message": "数据验证通过"
            }
        }

    def _convert_input_format(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换agent输入格式到验证器期望的格式

        Agent输入格式:
        - 格式1: {vital_signs: {...}, patient_data: {...}, medical_history: {...}}
        - 格式2: {patient_info: {...}, health_metrics: {...}} (ms_agent_executor格式)

        验证器期望格式: {patient_info: {...}, health_metrics: {...}}
        """
        converted = {}

        # 转换患者基本信息 - 支持两种格式
        patient_info = input_data.get('patient_info') or input_data.get('patient_data', {})
        if patient_info:
            # Convert age to int if it's a string
            age = patient_info.get('age')
            if age is not None:
                try:
                    age = int(age)
                except (ValueError, TypeError):
                    age = None

            converted['patient_info'] = {
                'name': patient_info.get('name', '患者'),
                'age': age,
                'gender': patient_info.get('gender', 'male')
            }

        # 转换体征数据到health_metrics格式 - 支持两种格式
        # 格式1: vital_signs (原始体征数据)
        # 格式2: health_metrics (已转换的健康指标)
        vital_signs = input_data.get('vital_signs', {})
        health_metrics_input = input_data.get('health_metrics', {})

        # 如果已有health_metrics，直接使用
        if health_metrics_input:
            converted['health_metrics'] = health_metrics_input
        elif vital_signs:
            health_metrics = {}

            # 血压
            if 'systolic_bp' in vital_signs or 'diastolic_bp' in vital_signs:
                health_metrics['blood_pressure'] = {
                    'systolic': vital_signs.get('systolic_bp'),
                    'diastolic': vital_signs.get('diastolic_bp')
                }

            # 血糖
            glucose_data = {}
            if 'fasting_glucose' in vital_signs:
                glucose_data['fasting'] = vital_signs['fasting_glucose']
            if 'postprandial_glucose' in vital_signs:
                glucose_data['postprandial'] = vital_signs['postprandial_glucose']
            if 'hba1c' in vital_signs:
                glucose_data['hba1c'] = vital_signs['hba1c']
            if glucose_data:
                health_metrics['blood_glucose'] = glucose_data

            # 血脂
            lipid_data = {}
            if 'total_cholesterol' in vital_signs:
                lipid_data['tc'] = vital_signs['total_cholesterol']
            if 'tg' in vital_signs:
                lipid_data['tg'] = vital_signs['tg']
            if 'ldl_c' in vital_signs:
                lipid_data['ldl_c'] = vital_signs['ldl_c']
            if 'hdl_c' in vital_signs:
                lipid_data['hdl_c'] = vital_signs['hdl_c']
            if lipid_data:
                health_metrics['blood_lipid'] = lipid_data

            # 尿酸
            if 'uric_acid' in vital_signs:
                health_metrics['uric_acid'] = vital_signs['uric_acid']

            # BMI (支持直接值或身高体重计算)
            if 'bmi' in vital_signs:
                # 如果直接有BMI值，检查是否需要添加腰围
                if 'waist' in vital_signs:
                    if isinstance(vital_signs['bmi'], (int, float)):
                        health_metrics['bmi'] = {
                            'value': vital_signs['bmi'],
                            'waist_circumference': vital_signs['waist']
                        }
                    else:
                        health_metrics['bmi'] = vital_signs['bmi']
                        if isinstance(health_metrics['bmi'], dict):
                            health_metrics['bmi']['waist_circumference'] = vital_signs['waist']
                else:
                    health_metrics['bmi'] = vital_signs['bmi']
            elif 'height' in vital_signs and 'weight' in vital_signs:
                # 从身高体重计算BMI，并添加腰围（如果有）
                bmi_data = {
                    'height': vital_signs['height'] / 100 if vital_signs['height'] > 10 else vital_signs['height'],  # cm转m
                    'weight': vital_signs['weight']
                }
                if 'waist' in vital_signs:
                    bmi_data['waist_circumference'] = vital_signs['waist']
                health_metrics['bmi'] = bmi_data
            elif 'height' in vital_signs or 'weight' in vital_signs:
                # 部分数据 - 添加腰围（如果有）
                bmi_data = {
                    'height': vital_signs.get('height', 0) / 100 if vital_signs.get('height', 0) > 10 else vital_signs.get('height', 0),
                    'weight': vital_signs.get('weight', 0)
                }
                if 'waist' in vital_signs:
                    bmi_data['waist_circumference'] = vital_signs['waist']
                health_metrics['bmi'] = bmi_data

            converted['health_metrics'] = health_metrics

        # 如果没有任何数据，返回空字典让验证器检测缺失
        return converted


def main():
    # UTF-8 encoding fix for Windows
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description='健康数据验证与标准化')
    parser.add_argument('--input', required=True, help='输入健康数据文件路径(JSON格式)')
    parser.add_argument('--output', default='validated_data.json', help='输出文件路径')
    parser.add_argument('--mode', default='standalone', choices=['standalone', 'skill'],
                        help='运行模式: standalone=独立运行返回JSON, skill=SKILL集成模式')

    args = parser.parse_args()

    # 读取输入数据
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except FileNotFoundError:
        result = {
            "success": False,
            "error": f"文件不存在: {args.input}"
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    except json.JSONDecodeError as e:
        result = {
            "success": False,
            "error": f"JSON格式错误: {str(e)}"
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    validator = HealthDataValidator()

    # SKILL模式：返回JSON格式的incomplete状态
    if args.mode == 'skill':
        result = validator.validate_for_skill(input_data)

        # Debug: Write validation details with UTF-8 encoding
        try:
            debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_validator_skill_mode.json")
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "mode": args.mode,
                    "input_file": args.input,
                    "input_data_keys": list(input_data.keys()),
                    "validation_errors": validator.errors,
                    "validation_warnings": validator.warnings,
                    "missing_fields_from_get_missing_fields": validator.get_missing_fields(),
                    "result_status": result.get('data', {}).get('status'),
                    "result_required_fields": result.get('data', {}).get('required_fields', [])
                }, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            pass  # Ignore debug write errors

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['success'] else 1

    # 独立模式：返回标准输出和退出码
    is_valid, validated_data = validator.validate_file(args.input)

    if is_valid:
        print("✓ 数据验证通过")
        if validator.warnings:
            print("\n警告信息:")
            for warning in validator.warnings:
                print(f"  - {warning}")

        validator.save_validated_data(args.output)
        return 0
    else:
        print("✗ 数据验证失败")
        print("\n错误信息:")
        for error in validator.errors:
            print(f"  - {error}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
