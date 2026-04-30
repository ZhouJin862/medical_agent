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
import re
from typing import Dict, Any, List
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
    """
    从 risk_calculator 的嵌套输出结构中提取模板变量

    Args:
        data: risk_calculator 输出的嵌套结构

    Returns:
        扁平化的模板变量字典
    """
    # 从 patient_info 提取基本信息
    patient_info = data.get('patient_info', {})

    # 从 blood_pressure 提取血压数据
    bp = data.get('blood_pressure', {})

    # 从 risk_stratification 提取风险分层
    risk_strat = data.get('risk_stratification', {})

    # 从 cardiovascular_risk 提取风险因素
    cv_risk = data.get('cardiovascular_risk', {})

    # 从 organ_damage 提取靶器官损害
    organ_damage = data.get('organ_damage', {})

    # 从 h_type_hypertension 提取H型高血压
    h_type = data.get('h_type_hypertension', {})

    # 生成血压描述
    bp_desc_parts = []
    if bp.get('systolic') and bp.get('diastolic'):
        bp_desc_parts.append(f"血压测量值：{bp['systolic']}/{bp['diastolic']} mmHg")
    if bp.get('level'):
        bp_desc_parts.append(f"血压分级：{bp['level']}")
    bp_description = ' | '.join(bp_desc_parts) if bp_desc_parts else '血压数据未提供'

    # 生成风险因素总结
    risk_factors = cv_risk.get('risk_factors', {})
    risk_factors_list = []
    for factor, present in risk_factors.items():
        if present:
            factor_name = {
                'smoking': '吸烟',
                'diabetes': '糖尿病',
                'dyslipidemia': '血脂异常',
                'obesity': '肥胖',
                'family_history': '心血管病家族史',
                'age_over_65': '年龄>65岁',
            }.get(factor, factor)
            risk_factors_list.append(factor_name)

    risk_factors_summary = '、'.join(risk_factors_list) if risk_factors_list else '无明显危险因素'

    # 生成靶器官损害评估
    organ_assessment = organ_damage.get('assessment', '未评估')
    organ_findings = organ_damage.get('findings', [])
    organ_damage_section = f"靶器官损害评估：{organ_assessment}"
    if organ_findings:
        organ_damage_section += "\n" + "\n".join(f"- {f}" for f in organ_findings)

    # 生成H型高血压评估
    h_type_assessment = f"H型高血压：{'是' if h_type.get('is_h_type') else '否'}"
    if h_type.get('description'):
        h_type_assessment += f"（{h_type['description']}）"

    # 生成血压控制目标
    risk_level = risk_strat.get('risk_level', '')
    bp_target_map = {
        '低危': '<140/90 mmHg',
        '中危': '<140/90 mmHg',
        '高危': '<130/80 mmHg（如能耐受）',
        '很高危': '<130/80 mmHg（如能耐受）'
    }
    bp_target = bp_target_map.get(risk_level, '<140/90 mmHg')

    # 生成生活方式干预建议
    lifestyle_map = {
        '低危': '1. 减少钠盐摄入，每人每日<6g\n2. 增加钾盐摄入\n3. 规律运动，每周150分钟中等强度运动\n4. 控制体重，BMI<24 kg/m²\n5. 戒烟限酒',
        '中危': '1. 减少钠盐摄入，每人每日<5g\n2. DASH饮食模式\n3. 规律运动，每周150-300分钟中等强度运动\n4. 减重，BMI<24 kg/m²，腰围男性<90cm，女性<85cm\n5. 戒烟，严格限制酒精',
        '高危': '1. 严格低盐饮食，每人每日<5g\n2. DASH或Mediterranean饮食\n3. 规律运动，每周>150分钟中等强度+抗阻训练\n4. 减重至BMI<24 kg/m²\n5. 完全戒烟，避免二手烟\n6. 限制酒精摄入',
        '很高危': '1. 严格低盐饮食，每人每日<3-5g\n2. DASH或Mediterranean饮食\n3. 规律运动，每周>300分钟\n4. 减重至正常范围\n5. 完全戒烟\n6. 严格限酒或戒酒'
    }
    lifestyle_intervention = lifestyle_map.get(risk_level, lifestyle_map['低危'])

    # 生成药物治疗建议
    medication_recommendation = risk_strat.get('recommendation', '请咨询医生')

    # 生成随访计划
    follow_up_map = {
        '低危': '每3-6个月随访一次',
        '中危': '每1-3个月随访一次',
        '高危': '每2-4周随访一次，直至血压达标',
        '很高危': '每1-2周随访一次，直至血压达标'
    }
    follow_up_plan = follow_up_map.get(risk_level, '每3-6个月随访一次')

    # 统计风险因素数量
    risk_factors_count = len(risk_factors_list)

    # 靶器官损害状态
    organ_damage_status = organ_damage.get('status', '未评估')

    return {
        # 基本信息
        'report_date': data.get('assessment_date', patient_info.get('report_date', '')),
        'assessment_date': data.get('assessment_date', patient_info.get('report_date', '')),  # 添加 assessment_date 别名
        'report_number': patient_info.get('report_number', ''),
        'patient_name': patient_info.get('name', ''),
        'patient_id': patient_info.get('patient_id', ''),
        'age': patient_info.get('age', ''),
        'gender': patient_info.get('gender', ''),

        # 血压数据
        'systolic': bp.get('systolic', ''),
        'diastolic': bp.get('diastolic', ''),
        'bp_grade': bp.get('level_code', ''),
        'bp_level': bp.get('level', ''),
        'bp_description': bp_description,

        # 风险因素
        'risk_factors_count': risk_factors_count,
        'risk_factors_summary': risk_factors_summary,
        'risk_stratification': risk_strat.get('risk_level', ''),
        'risk_level': risk_strat.get('risk_level', ''),

        # 靶器官损害
        'organ_damage_status': organ_damage_status,
        'organ_damage_section': organ_damage_section,

        # H型高血压
        'h_type_assessment': h_type_assessment,

        # 干预建议
        'bp_target': bp_target,
        'lifestyle_intervention': lifestyle_intervention,
        'medication_recommendation': medication_recommendation,
        'follow_up_plan': follow_up_plan,

        # 其他
        'hcy': str(h_type.get('hcy_value', '')),
        'recommendations': [risk_strat.get('recommendation', '')],
    }


def _build_structured_result(risk_data, overall_risk, health_metrics, input_data):
    """Build structured result for unified assessment JSON schema."""
    risk_grade = overall_risk.get('risk_grade', '') or overall_risk.get('risk_level', '')
    category = _map_risk_to_category(risk_grade)

    # 1. Population classification
    population_classification = {
        "categories": [{"category": category, "label": risk_grade or category}],
        "primary_category": category,
        "basis": [],
        "score": 0,
    }

    # 2. Recommended data collection (check for missing vitals)
    recommended = []
    if not risk_data.get('systolic') or not risk_data.get('diastolic'):
        recommended.append({"item": "血压测量", "reason": "缺少血压数据"})
    if not risk_data.get('hcy'):
        recommended.append({"item": "同型半胱氨酸(Hcy)", "reason": "H型高血压评估需要"})
    if not input_data.get('organ_damage', {}).get('assessment'):
        recommended.append({"item": "靶器官损害检查", "reason": "需要评估靶器官损害情况"})

    # 3. Abnormal indicators
    abnormal = []
    systolic = risk_data.get('systolic')
    diastolic = risk_data.get('diastolic')
    if systolic:
        try:
            sv = float(systolic)
            if sv >= 140:
                abnormal.append({"indicator": "收缩压", "value": f"{systolic} mmHg", "reference": "<140 mmHg"})
        except (ValueError, TypeError):
            pass
    if diastolic:
        try:
            dv = float(diastolic)
            if dv >= 90:
                abnormal.append({"indicator": "舒张压", "value": f"{diastolic} mmHg", "reference": "<90 mmHg"})
        except (ValueError, TypeError):
            pass
    hcy_val = risk_data.get('hcy')
    if hcy_val:
        try:
            hv = float(hcy_val)
            if hv >= 10:
                abnormal.append({"indicator": "同型半胱氨酸(Hcy)", "value": f"{hcy_val} μmol/L", "reference": "<10 μmol/L"})
        except (ValueError, TypeError):
            pass

    # 4. Disease prediction
    disease_prediction = []
    risk_level = risk_data.get('risk_level', '')
    if risk_level in ('高危', '很高危'):
        disease_prediction.append({"disease": "高血压并发症", "risk": "高", "description": "心脑血管事件风险显著增加"})
    if risk_data.get('organ_damage_status') and risk_data.get('organ_damage_status') != '未评估':
        disease_prediction.append({"disease": "靶器官损害", "risk": "中高", "description": "心脏、肾脏、血管等靶器官可能受损"})
    if hcy_val:
        try:
            if float(hcy_val) >= 10:
                disease_prediction.append({"disease": "H型高血压", "risk": "中", "description": "伴高同型半胱氨酸血症，脑卒中风险增加"})
        except (ValueError, TypeError):
            pass

    # 5. Intervention prescriptions
    prescriptions = []
    prescriptions.append({"type": "饮食", "content": ["低钠饮食，每日钠盐摄入<5g", "增加钾盐摄入"], "priority": "高"})
    prescriptions.append({"type": "运动", "content": ["每周150分钟以上中等强度有氧运动"], "priority": "高"})
    prescriptions.append({"type": "监测", "content": ["每日监测血压", "定期复查"], "priority": "高"})
    if risk_level in ('高危', '很高危'):
        prescriptions.append({"type": "药物治疗", "content": ["建议在医生指导下进行降压药物治疗"], "priority": "高"})

    return {
        "population_classification": population_classification,
        "recommended_data_collection": recommended,
        "abnormal_indicators": abnormal,
        "disease_prediction": disease_prediction,
        "intervention_prescriptions": prescriptions,
    }


def _map_risk_to_category(risk_grade):
    if not risk_grade:
        return "未知"
    grade = risk_grade.lower()
    if "很高危" in grade or "极高" in grade:
        return "专病"
    if "高危" in grade or "高" in grade:
        return "慢病"
    if "中危" in grade or "中" in grade:
        return "亚健康"
    return "健康"


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
                overall_risk = input_data.get('risk_stratification', {})
                health_metrics = input_data.get('cardiovascular_risk', {})
                structured_result = _build_structured_result(template_vars, overall_risk, health_metrics, input_data)
                result = {
                    "success": True,
                    "template": args.template,
                    "modules": sections,
                    "total_modules": len(sections),
                    "structured_result": structured_result
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
