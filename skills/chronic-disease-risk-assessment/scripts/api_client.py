#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三方健康平台API客户端

功能：
1. 从健康平台/体检系统API获取健康数据
2. 处理API鉴权（API Key）
3. 数据格式转换
4. 错误处理与重试机制

授权方式: ApiKey
凭证Key: COZE_health_api_7619143034713702452
"""

import json
import sys
import argparse
import os
from datetime import datetime
from typing import Dict, Any, Optional

# 必须使用 coze_workload_identity 的 requests
from coze_workload_identity import requests


class HealthAPIClient:
    """健康平台API客户端"""
    
    # Skill ID 和凭证配置
    SKILL_ID = "7619143034713702452"
    CREDENTIAL_KEY = f"COZE_HEALTH_API_{SKILL_ID}"
    
    def __init__(self):
        self.api_key = None
        self.endpoint = None
    
    def fetch_patient_data(
        self,
        endpoint: str,
        patient_id: str,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从API获取患者健康数据
        
        Args:
            endpoint: API基础地址
            patient_id: 患者ID
            api_key: API密钥（可选，从环境变量获取）
            
        Returns:
            标准化的健康数据
        """
        # 获取API密钥（优先使用环境变量中的凭证）
        if api_key:
            self.api_key = api_key
        else:
            # 从环境变量获取（由skill_credentials配置）
            self.api_key = os.getenv(self.CREDENTIAL_KEY)
        
        if not self.api_key:
            raise ValueError(
                "缺少API密钥。请配置健康平台API凭证：\n"
                "1. 系统将引导您配置API凭证\n"
                "2. 或通过 --api-key 参数提供"
            )
        
        self.endpoint = endpoint.rstrip('/')
        
        # 构建请求URL
        url = f"{self.endpoint}/patient/{patient_id}"
        
        # 请求头
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            # 检查HTTP状态码
            if response.status_code >= 400:
                error_msg = f"HTTP请求失败: 状态码 {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f", {error_data['message']}"
                except:
                    error_msg += f", 响应内容: {response.text[:200]}"
                
                if response.status_code == 401:
                    raise ValueError(f"API认证失败，请检查API密钥是否正确。{error_msg}")
                elif response.status_code == 404:
                    raise ValueError(f"未找到患者ID: {patient_id}")
                else:
                    raise Exception(error_msg)
            
            data = response.json()
            
            # 转换为标准格式
            return self._normalize_api_data(data, patient_id)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求异常: {str(e)}")
    
    def _normalize_api_data(self, api_data: Dict[str, Any], patient_id: str) -> Dict[str, Any]:
        """
        将API数据转换为标准健康数据格式
        
        不同API的数据结构可能不同，需要根据实际情况映射
        """
        # 标准输出格式
        normalized = {
            'patient_info': {},
            'health_metrics': {},
            'source': {
                'type': 'api',
                'endpoint': self.endpoint,
                'patient_id': patient_id,
                'fetched_at': datetime.now().isoformat()
            }
        }
        
        # 尝试从API数据中提取患者信息
        if 'patient_info' in api_data:
            normalized['patient_info'] = api_data['patient_info']
        elif 'patient' in api_data:
            patient = api_data['patient']
            normalized['patient_info'] = {
                'name': patient.get('name', patient.get('patient_name', '未知')),
                'age': patient.get('age'),
                'gender': patient.get('gender', patient.get('sex'))
            }
        else:
            normalized['patient_info'] = {
                'name': api_data.get('name', api_data.get('patient_name', '未知')),
                'age': api_data.get('age'),
                'gender': api_data.get('gender', api_data.get('sex'))
            }
        
        # 提取健康指标
        metrics_data = api_data.get('health_metrics', api_data.get('metrics', api_data))
        
        # 血压
        if 'blood_pressure' in metrics_data:
            bp = metrics_data['blood_pressure']
            normalized['health_metrics']['blood_pressure'] = {
                'systolic': bp.get('systolic', bp.get('sbp')),
                'diastolic': bp.get('diastolic', bp.get('dbp'))
            }
        
        # 血糖
        if 'blood_glucose' in metrics_data:
            bg = metrics_data['blood_glucose']
            normalized['health_metrics']['blood_glucose'] = {
                'fasting': bg.get('fasting', bg.get('fpg')),
                'hba1c': bg.get('hba1c'),
                'postprandial': bg.get('postprandial', bg.get('2hpg'))
            }
        
        # 血脂
        if 'blood_lipid' in metrics_data:
            lipid = metrics_data['blood_lipid']
            normalized['health_metrics']['blood_lipid'] = {
                'tc': lipid.get('tc', lipid.get('total_cholesterol')),
                'tg': lipid.get('tg', lipid.get('triglyceride')),
                'ldl_c': lipid.get('ldl_c', lipid.get('ldl_cholesterol')),
                'hdl_c': lipid.get('hdl_c', lipid.get('hdl_cholesterol'))
            }
        
        # 尿酸
        if 'uric_acid' in metrics_data:
            normalized['health_metrics']['uric_acid'] = metrics_data['uric_acid']
        elif 'sua' in metrics_data:
            normalized['health_metrics']['uric_acid'] = metrics_data['sua']
        
        # BMI
        if 'bmi' in metrics_data:
            bmi_data = metrics_data['bmi']
            if isinstance(bmi_data, dict):
                normalized['health_metrics']['bmi'] = bmi_data
            else:
                normalized['health_metrics']['bmi'] = {'value': bmi_data}
        else:
            height = metrics_data.get('height')
            weight = metrics_data.get('weight')
            if height and weight:
                if height > 3:
                    height = height / 100
                bmi = weight / (height ** 2)
                normalized['health_metrics']['bmi'] = {
                    'height': height,
                    'weight': weight,
                    'value': round(bmi, 2)
                }
        
        # 腰围
        if 'waist_circumference' in metrics_data:
            if 'bmi' in normalized['health_metrics']:
                normalized['health_metrics']['bmi']['waist_circumference'] = metrics_data['waist_circumference']
        
        # 额外数据
        additional_data = {}
        optional_fields = ['ultrasound', 'carotid_ultrasound', 'uacr', 'egfr', 'smoking']
        for field in optional_fields:
            if field in api_data or field in metrics_data:
                additional_data[field] = api_data.get(field) or metrics_data.get(field)
        
        if additional_data:
            normalized['additional_data'] = additional_data
        
        return normalized
    
    def save_data(self, data: Dict[str, Any], output_path: str = 'api_health_data.json'):
        """保存获取的数据"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"API数据已保存至: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='第三方健康平台API客户端')
    parser.add_argument('--endpoint', required=True, help='API基础地址')
    parser.add_argument('--patient-id', required=True, help='患者ID')
    parser.add_argument('--api-key', help='API密钥（可选，默认从环境变量获取）')
    parser.add_argument('--output', default='api_health_data.json', help='输出文件路径')
    
    args = parser.parse_args()
    
    client = HealthAPIClient()
    
    try:
        print(f"正在从API获取患者 {args.patient_id} 的健康数据...")
        data = client.fetch_patient_data(
            endpoint=args.endpoint,
            patient_id=args.patient_id,
            api_key=args.api_key
        )
        
        print("\n=== 数据获取成功 ===")
        print(f"患者: {data['patient_info'].get('name', '未知')}")
        print(f"数据来源: {data['source']['endpoint']}")
        
        if 'health_metrics' in data:
            print("\n已获取指标:")
            for key in data['health_metrics'].keys():
                print(f"  - {key}")
        
        client.save_data(data, args.output)
        return 0
        
    except ValueError as e:
        print(f"配置错误: {str(e)}")
        return 1
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
