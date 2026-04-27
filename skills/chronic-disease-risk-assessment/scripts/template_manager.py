#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告模板管理器

功能：
1. 加载和解析报告模板
2. 提取模板变量
3. 支持自定义模板
"""

import json
import sys
import argparse
import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import yaml
except ImportError:
    print("警告: yaml模块未安装，使用简化解析")
    yaml = None


class TemplateManager:
    """报告模板管理器"""
    
    # 模板目录
    TEMPLATE_DIR = Path(__file__).parent.parent / 'assets'
    
    # 内置模板
    BUILTIN_TEMPLATES = {
        'default': 'default_template.md',
        'simple': 'simple_template.md',
        'insurance': 'insurance_template.md',
        'clinical': 'clinical_template.md',
        'personal': 'personal_template.md',
        'report': 'report_template.md'
    }
    
    def __init__(self):
        self.template_content = ""
        self.template_vars = []
        self.template_meta = {}
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """
        加载报告模板
        
        Args:
            template_name: 模板名称（default/simple）或自定义模板路径
            
        Returns:
            模板信息字典
        """
        # 判断是内置模板还是自定义模板
        if template_name in self.BUILTIN_TEMPLATES:
            template_path = self.TEMPLATE_DIR / self.BUILTIN_TEMPLATES[template_name]
        else:
            template_path = Path(template_name)
        
        if not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        
        # 读取模板内容
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template_content = f.read()
        
        # 解析模板
        self._parse_template()
        
        return {
            'template_path': str(template_path),
            'template_name': template_name,
            'template_meta': self.template_meta,
            'template_vars': self.template_vars,
            'content_length': len(self.template_content)
        }
    
    def _parse_template(self):
        """解析模板内容"""
        # 提取YAML Front Matter
        if self.template_content.startswith('---'):
            parts = self.template_content.split('---', 2)
            if len(parts) >= 3:
                yaml_content = parts[1].strip()
                self.template_content = parts[2].strip()
                
                # 解析YAML
                if yaml:
                    try:
                        self.template_meta = yaml.safe_load(yaml_content)
                    except yaml.YAMLError as e:
                        print(f"警告: YAML解析失败: {e}")
                        self.template_meta = {}
                else:
                    # 简化解析
                    self.template_meta = self._simple_yaml_parse(yaml_content)
        
        # 提取模板变量 {{variable_name}}
        var_pattern = r'\{\{(\w+)\}\}'
        self.template_vars = list(set(re.findall(var_pattern, self.template_content)))
        
        # 排序变量列表
        self.template_vars.sort()
    
    def _simple_yaml_parse(self, yaml_content: str) -> Dict[str, Any]:
        """简化的YAML解析（无需yaml模块时使用）"""
        result = {}
        for line in yaml_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 处理列表
                if value.startswith('[') and value.endswith(']'):
                    value = [item.strip() for item in value[1:-1].split(',')]
                
                result[key] = value
        
        return result
    
    def get_template_structure(self) -> Dict[str, Any]:
        """获取模板结构信息"""
        return {
            'meta': self.template_meta,
            'variables': self.template_vars,
            'sections': self._extract_sections()
        }
    
    def _extract_sections(self) -> List[str]:
        """提取模板章节"""
        sections = []
        lines = self.template_content.split('\n')
        
        for line in lines:
            if line.startswith('##'):
                section_name = line.strip('#').strip()
                sections.append(section_name)
        
        return sections
    
    def validate_variables(self, provided_vars: Dict[str, Any]) -> List[str]:
        """
        验证提供的变量是否满足模板需求
        
        Args:
            provided_vars: 提供的变量字典
            
        Returns:
            缺失的变量列表
        """
        missing_vars = []
        
        for var in self.template_vars:
            if var not in provided_vars or provided_vars[var] is None:
                missing_vars.append(var)
        
        return missing_vars

    def render_template(self, variables: Dict[str, Any]) -> str:
        """
        渲染模板（仅替换变量占位符）

        Args:
            variables: 变量字典

        Returns:
            渲染后的内容
        """
        rendered = self.template_content

        for var_name, var_value in variables.items():
            placeholder = '{{' + var_name + '}}'
            value = str(var_value) if var_value is not None else ''
            rendered = rendered.replace(placeholder, value)

        return rendered

    def render_template_by_section(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        按章节渲染模板，返回每个章节的渲染内容

        Args:
            variables: 变量字典

        Returns:
            章节名称到渲染内容的字典
        """
        # 先渲染完整模板
        rendered = self.render_template(variables)

        # 提取 header 部分（报告编号、评估日期等）
        sections = {}
        lines = rendered.split('\n')

        # 收集所有章节内容
        current_section = 'header'
        current_content = []
        # Only match top-level sections (##) not sub-sections (###)
        section_pattern = re.compile(r'^##\s+(.+)$')

        for line in lines:
            section_match = section_pattern.match(line)

            if section_match:
                # 保存上一个章节
                if current_content:
                    content = '\n'.join(current_content).strip()
                    if content:
                        sections[current_section] = content

                # 开始新章节
                current_section = section_match.group(1).strip()
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        if current_content:
            content = '\n'.join(current_content).strip()
            if content:
                sections[current_section] = content

        return sections

    def list_builtin_templates(self) -> List[Dict[str, Any]]:
        """列出所有内置模板"""
        templates = []
        
        for name, filename in self.BUILTIN_TEMPLATES.items():
            template_path = self.TEMPLATE_DIR / filename
            if template_path.exists():
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取元数据
                    meta = {}
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3 and yaml:
                            try:
                                meta = yaml.safe_load(parts[1].strip())
                            except:
                                pass
                    
                    templates.append({
                        'name': name,
                        'filename': filename,
                        'description': meta.get('template_name', name),
                        'version': meta.get('template_version', '1.0')
                    })
                except Exception as e:
                    print(f"警告: 无法读取模板 {name}: {e}")
        
        return templates


def _format_diabetes_complications(glucose_assessment: Dict[str, Any]) -> str:
    """
    格式化糖尿病并发症风险评估信息（独立函数）

    Args:
        glucose_assessment: 血糖评估结果字典

    Returns:
        格式化的HTML字符串，如果没有风险则返回空字符串
    """
    complications_risk = glucose_assessment.get('complications_risk', '')
    recommendation = glucose_assessment.get('recommendation', '')

    if not complications_risk:
        return ''

    return f"""**糖尿病并发症风险**： {complications_risk}

**糖尿病管理建议**： {recommendation}"""


def main():
    # 配置 UTF-8 编码输出（Windows 兼容）
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description='报告模板管理器')
    parser.add_argument('--template', required=False,
                       help='模板名称（default/simple/report）或自定义模板路径')
    parser.add_argument('--list', action='store_true',
                       help='列出所有内置模板')
    parser.add_argument('--input',
                       help='输入数据文件路径（JSON格式）')
    parser.add_argument('--output', default='template_result.json',
                       help='输出结果文件路径')
    parser.add_argument('--render', action='store_true',
                       help='渲染模式：使用输入数据渲染模板')
    parser.add_argument('--format',
                       choices=['json', 'markdown', 'modules'],
                       default='modules',
                       help='输出格式：json（JSON数据）、markdown（完整报告）、modules（分模块输出）')

    args = parser.parse_args()
    
    manager = TemplateManager()

    # 列出内置模板
    if args.list:
        print("\n可用模板:")
        templates = manager.list_builtin_templates()
        for template in templates:
            print(f"  - {template['name']}: {template['description']}")
        return 0

    # 渲染模式
    if args.render:
        if not args.template:
            print("错误: --template 参数在渲染模式下是必需的")
            return 1

        # 加载输入数据
        input_data = {}
        if args.input:
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)
            except Exception as e:
                print(f"错误: 无法读取输入文件 {args.input}: {e}")
                return 1
        else:
            print("错误: --input 参数在渲染模式下是必需的")
            return 1

        # 加载模板
        try:
            manager.load_template(args.template)
        except Exception as e:
            print(f"错误: 无法加载模板 {args.template}: {e}")
            return 1

        # 准备模板变量 - handle both direct and nested input formats
        # Extract risk_assessment if wrapped (from skill workflow)
        risk_data = input_data.get('risk_assessment', input_data)

        # Extract nested data
        patient_info = risk_data.get('patient_info', {})
        overall_risk = risk_data.get('overall_risk', {})
        risk_assessment = risk_data.get('risk_assessment', {})
        # health_metrics is directly in input_data (from step 1), not in risk_data
        health_metrics = input_data.get('health_metrics', {})

        # Helper to get value from risk_assessment by type
        def get_assessment_value(assessment_type):
            if assessment_type in risk_assessment:
                return risk_assessment[assessment_type]

            # Try to find in nested structure
            for key, value in risk_assessment.items():
                if isinstance(value, dict) and key == assessment_type:
                    return value
            return {}

        # Debug: Write risk_assessment data to file
        try:
            debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_template_risk_assessment.txt")
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(f"risk_assessment keys: {list(risk_assessment.keys())}\n")
                if 'blood_pressure' in risk_assessment:
                    f.write(f"blood_pressure: {risk_assessment['blood_pressure']}\n")
                if 'blood_pressure' not in risk_assessment and 'risk_assessment' in risk_data:
                    f.write(f"Looking in risk_data.risk_assessment: {list(risk_data.get('risk_assessment', {}).keys())}\n")
        except:
            pass

        # Build template variables from risk_calculator output
        bp_assessment = get_assessment_value('blood_pressure') or get_assessment_value('bp') or {}
        bmi_assessment = get_assessment_value('bmi') or {}
        glucose_assessment = get_assessment_value('blood_glucose') or get_assessment_value('glucose') or {}
        lipid_assessment = get_assessment_value('blood_lipid') or get_assessment_value('lipid') or {}
        uric_acid_assessment = get_assessment_value('uric_acid') or {}

        # Get values from nested health_metrics structure
        bp_data = health_metrics.get('blood_pressure', {})
        bg_data = health_metrics.get('blood_glucose', {})
        lipid_data = health_metrics.get('blood_lipid', {})
        basic_data = health_metrics.get('basic', {})
        bmi_data = health_metrics.get('bmi', {})

        # Extract BMI value
        bmi_value = bmi_assessment.get('values', {}).get('bmi', '')
        if not bmi_value and isinstance(bmi_data, dict):
            h = bmi_data.get('height', basic_data.get('height', 0))
            w = bmi_data.get('weight', basic_data.get('weight', 0))
            if h > 0 and w > 0:
                bmi_value = round(w / (h * h), 2)

        template_vars = {
            # 基本信息
            'report_number': input_data.get('report_date', '').replace('年', '').replace('月', '').replace('日', '') + '-001',
            'assessment_date': risk_data.get('assessment_date', ''),
            'patient_age': patient_info.get('age', ''),
            'patient_name': patient_info.get('name', '患者'),
            'core_logic': f"基于{len(risk_assessment)}项健康指标的综合风险评估",

            # 综合风险评分
            'health_score': overall_risk.get('total_score', ''),
            'risk_level': overall_risk.get('risk_grade', ''),
            'metabolic_label': overall_risk.get('risk_grade', ''),
            'medical_comment': overall_risk.get('priority', ''),

            # BMI相关
            'bmi_value': bmi_value,
            'waist_circumference': basic_data.get('waist_circumference', health_metrics.get('waist', '')),
            'ultrasound_evidence': '未提供超声检查数据',
            'obesity_assessment': bmi_assessment.get('description', ''),

            # 血压相关
            'bp_value': f"{bp_data.get('systolic', '')}/{bp_data.get('diastolic', '')}",
            'bp_interpretation': bp_assessment.get('description', ''),
            'bp_target': '<140/90 mmHg',

            # 血糖相关
            'glucose_value': f"空腹血糖 {bg_data.get('fasting', '')} mmol/L" + (f"，糖化血红蛋白 {bg_data.get('hba1c', '')}%" if bg_data.get('hba1c') else ''),
            'glucose_interpretation': glucose_assessment.get('description', ''),
            'glucose_target': '<6.1 mmol/L',
            'diabetes_complications_risk': glucose_assessment.get('complications_risk', ''),
            'diabetes_recommendation': glucose_assessment.get('recommendation', ''),
            # 糖尿病并发症风险评估章节（仅在有风险时显示）
            'diabetes_complications_section': _format_diabetes_complications(glucose_assessment),

            # 血脂相关
            'lipid_value': f"TC:{lipid_data.get('tc', '')}, TG:{lipid_data.get('tg', '')}, LDL-C:{lipid_data.get('ldl_c', '')}, HDL-C:{lipid_data.get('hdl_c', '')}",
            'lipid_interpretation': lipid_assessment.get('description', ''),
            'lipid_target': 'TC<5.17, TG<1.69, LDL-C<3.37, HDL-C>1.04',

            # 尿酸相关
            'uric_acid_value': f"{health_metrics.get('uric_acid', '')} μmol/L",
            'uric_acid_interpretation': uric_acid_assessment.get('description', ''),
            'uric_acid_target': '<420 μmol/L (男性) / <360 μmol/L (女性)',

            # 风险预测
            'ascvd_risk_10year': '未计算（需要更多参数）',
            'diabetes_risk_3year': '未计算（需要更多参数）',
            'residual_risk_note': '建议定期复查，关注残余风险',

            # 器官损害
            'vascular_evidence': '未提供血管检查数据',
            'vascular_conclusion': '建议进行颈动脉彩超等检查评估血管状况',
            'kidney_evidence': '未提供肾功能检查数据',
            'kidney_conclusion': '建议进行肾功能检查评估肾脏状况',

            # 干预建议
            'clinical_treatment': overall_risk.get('priority', '请咨询专业医生'),
            'lifestyle_intervention': '建议改善生活方式：低盐低脂饮食、规律运动、控制体重、戒烟限酒',
            'expert_summary': f"患者{patient_info.get('age', '')}岁，{overall_risk.get('risk_grade', '')}，{overall_risk.get('priority', '')}。"
        }

        # 渲染模板
        try:
            sections = manager.render_template_by_section(template_vars)

            if args.format == 'modules':
                # 分模块输出
                result = {
                    "success": True,
                    "template": args.template,
                    "modules": sections,
                    "total_modules": len(sections)
                }
            elif args.format == 'markdown':
                # 完整 markdown 输出
                result = {
                    "success": True,
                    "template": args.template,
                    "markdown": '\n\n'.join(sections.values())
                }
            else:
                # JSON 格式
                result = {
                    "success": True,
                    "template": args.template,
                    "format": args.format,
                    "data": sections
                }

            # 输出结果
            if args.format == 'markdown':
                # 直接输出 markdown 内容
                if hasattr(sys.stdout, 'buffer'):
                    sys.stdout.buffer.write(result['markdown'].encode('utf-8'))
                else:
                    print(result['markdown'])
            else:
                # 输出 JSON
                if hasattr(sys.stdout, 'buffer'):
                    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'))
                else:
                    print(json.dumps(result, ensure_ascii=False, indent=2))

            return 0

        except Exception as e:
            print(f"错误: 模板渲染失败: {e}")
            return 1

    # 默认模式：加载指定模板并显示信息
    if not args.template:
        print("错误: 请指定 --template 或使用 --list 列出可用模板")
        return 1

    try:
        template_info = manager.load_template(args.template)

        print(f"\n=== 模板信息 ===")
        print(f"模板名称: {template_info['template_name']}")
        print(f"模板路径: {template_info['template_path']}")
        print(f"内容长度: {template_info['content_length']} 字符")

        if template_info['template_meta']:
            print(f"\n元数据:")
            for key, value in template_info['template_meta'].items():
                print(f"  - {key}: {value}")

        print(f"\n模板变量 ({len(template_info['template_vars'])}个):")
        for var in template_info['template_vars']:
            print(f"  - {var}")

        # 获取章节信息
        sections = manager._extract_sections()
        if sections:
            print(f"\n模板章节:")
            for i, section in enumerate(sections, 1):
                print(f"  {i}. {section}")

        # 保存模板信息
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(template_info, f, ensure_ascii=False, indent=2)
        print(f"\n模板信息已保存至: {args.output}")

        return 0

    except Exception as e:
        print(f"错误: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
