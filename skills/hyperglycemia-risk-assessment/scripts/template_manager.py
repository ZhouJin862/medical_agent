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


def _extract_template_vars_from_risk_assessment(data: Dict[str, Any]) -> Dict[str, Any]:
    """从 risk_calculator 输出中提取模板变量"""
    patient_info = data.get('patient_info', {})
    glucose = data.get('glucose_assessment', {})
    prediabetes = data.get('prediabetes_risk', {})
    insulin = data.get('insulin_resistance', {})
    complications = data.get('complications', {})
    overall = data.get('overall_risk', {})

    # 血糖值和状态
    fasting_info = glucose.get('fasting_glucose', {})
    hba1c_info = glucose.get('hba1c', {})
    status = glucose.get('overall_status', '正常')

    # 糖代谢描述
    status_desc_map = {
        '糖尿病': f'已达到糖尿病诊断标准（空腹血糖{fasting_info.get("value", 0)} mmol/L，HbA1c {hba1c_info.get("value", 0)}%）',
        '糖尿病前期': '血糖水平高于正常但未达到糖尿病标准，需积极干预',
        '正常': '血糖水平在正常范围内'
    }
    glucose_description = status_desc_map.get(status, '')

    # 糖尿病前期评估
    if status == '糖尿病':
        prediabetes_assessment = '已确诊糖尿病'
    elif prediabetes.get('is_prediabetes'):
        prediabetes_assessment = f"处于糖尿病前期，{prediabetes.get('description', '建议积极干预')}"
    else:
        prediabetes_assessment = '未发现糖尿病前期迹象'

    # 3年转化风险
    three_year_risk = prediabetes.get('three_year_risk', 0)
    if status == '糖尿病':
        three_year_risk = 100

    # 胰岛素抵抗评估
    if insulin.get('has_resistance'):
        insulin_section = f"存在胰岛素抵抗风险\n\n评估结果：{insulin.get('description', '请进一步检查')}"
    else:
        insulin_section = "未发现明显胰岛素抵抗迹象"

    # 并发症风险
    comp_items = complications.get('complications', [])
    if comp_items:
        complications_section = "### 并发症风险筛查结果\n"
        for c in comp_items:
            complications_section += f"- **{c.get('name', '')}**: {c.get('level', '')} - {c.get('description', '')}\n"
    else:
        complications_section = "暂无足够数据进行并发症风险评估"

    # 血糖控制目标
    risk_level = overall.get('risk_level', '')
    target_map = {
        '高风险': '空腹血糖: 4.4-7.0 mmol/L，HbA1c <7.0%',
        '中风险': '空腹血糖: <6.1 mmol/L，HbA1c <5.7%',
        '低风险': '保持正常血糖水平'
    }
    glucose_target = target_map.get(risk_level, '请咨询医生确定控制目标')

    # 生活方式干预
    lifestyle_map = {
        '高风险': '1. 糖尿病饮食，控制总热量\n2. 规律运动，每周≥150分钟中等强度\n3. 自我血糖监测\n4. 控制体重\n5. 戒烟限酒',
        '中风险': '1. 均衡饮食，减少精制糖摄入\n2. 规律有氧运动\n3. 控制体重\n4. 定期监测血糖',
        '低风险': '1. 保持健康饮食习惯\n2. 规律运动\n3. 定期体检'
    }
    lifestyle_intervention = lifestyle_map.get(risk_level, lifestyle_map['低风险'])

    # 药物治疗建议
    medication_map = {
        '高风险': '建议积极降糖治疗，全面并发症筛查',
        '中风险': '建议生活方式干预，必要时考虑药物治疗',
        '低风险': '以生活方式干预为主'
    }
    medication_recommendation = medication_map.get(risk_level, '请咨询医生')

    # 随访计划
    follow_up_map = {
        '高风险': '每1-3个月随访一次，监测血糖和并发症',
        '中风险': '每3-6个月随访一次',
        '低风险': '每年随访一次'
    }
    follow_up_plan = follow_up_map.get(risk_level, '每6-12个月随访一次')

    return {
        'assessment_date': data.get('assessment_date', ''),
        'report_number': patient_info.get('report_number', ''),
        'fasting_glucose': fasting_info.get('value', ''),
        'hba1c': hba1c_info.get('value', ''),
        'glucose_status': status,
        'glucose_description': glucose_description,
        'prediabetes_assessment': prediabetes_assessment,
        'three_year_risk': three_year_risk,
        'insulin_resistance_section': insulin_section,
        'complications_section': complications_section,
        'glucose_target': glucose_target,
        'lifestyle_intervention': lifestyle_intervention,
        'medication_recommendation': medication_recommendation,
        'follow_up_plan': follow_up_plan,
    }


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

        # 准备模板变量 - 从 risk_calculator 的嵌套结构中提取
        template_vars = _extract_template_vars_from_risk_assessment(input_data)

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
