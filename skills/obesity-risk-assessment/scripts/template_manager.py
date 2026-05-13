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
    """从 risk_calculator 输出中提取模板变量"""
    patient_info = data.get('patient_info', {})
    bmi = data.get('bmi_assessment', {})
    central = data.get('central_obesity', {})
    metabolic = data.get('metabolic_syndrome', {})
    body_fat = data.get('body_fat', {})
    related = data.get('related_diseases', {})
    overall = data.get('overall_risk', {})

    # BMI相关
    height = bmi.get('height', 0)
    weight = bmi.get('weight', 0)
    bmi_value = bmi.get('value', '')
    bmi_level = bmi.get('level', '')

    # 腰围
    waist = central.get('waist', '')
    waist_threshold = central.get('elevated_threshold', 90)
    central_level = central.get('level', '正常')

    # 代谢综合征
    criteria = metabolic.get('criteria', [])
    met_count = metabolic.get('met_count', 0)

    def _get_criterion_result(name):
        for c in criteria:
            if c.get('name') == name:
                return c.get('value', ''), '是' if c.get('met') else '否'
        return '未提供', '否'

    waist_result, waist_met = _get_criterion_result('中心型肥胖')
    glucose_result, glucose_met = _get_criterion_result('高血糖')
    bp_result, bp_met = _get_criterion_result('高血压')
    tg_result, tg_met = _get_criterion_result('高甘油三酯')
    hdl_result, hdl_met = _get_criterion_result('低HDL-C')

    metabolic_diagnosis = metabolic.get('diagnosis', '未诊断代谢综合征')

    # 体脂评估
    if body_fat.get('available'):
        body_fat_section = f"体脂率: {body_fat.get('percentage', '未提供')}%\n评估: {body_fat.get('level', '未知')}"
    else:
        body_fat_section = "未提供体脂数据"

    # 相关疾病风险
    diseases = related.get('diseases', [])
    if diseases:
        related_section = "### 肥胖相关疾病风险\n"
        for d in diseases:
            related_section += f"- **{d.get('name', '')}**: {d.get('risk_level', '')}\n"
    else:
        related_section = "暂无明显肥胖相关疾病风险"

    # 目标体重和减重目标
    risk_level = overall.get('risk_level', '')
    if bmi_value and height:
        normal_bmi = 22.0
        if height > 3:
            height_m = height / 100
        else:
            height_m = height
        target_w = round(normal_bmi * height_m * height_m, 1)
        target_weight = f"{target_w} kg（BMI 22.0）"
        loss = round(weight - target_w, 1) if weight > target_w else 0
        weight_loss_goal = f"减重 {loss} kg（至正常BMI范围）" if loss > 0 else "维持当前体重"
    else:
        target_weight = "请咨询医生"
        weight_loss_goal = "请咨询医生"

    # 生活方式干预
    lifestyle_map = {
        '高风险': '1. 严格控制饮食热量\n2. 每日60分钟以上中等强度运动\n3. 行为疗法辅助\n4. 减少久坐时间',
        '中风险': '1. 适当控制饮食热量\n2. 每周≥150分钟中等强度运动\n3. 减少久坐\n4. 规律作息',
        '低风险': '1. 保持均衡饮食\n2. 规律运动\n3. 维持健康体重'
    }
    lifestyle_intervention = lifestyle_map.get(risk_level, lifestyle_map['低风险'])

    # 治疗建议
    treatment_map = {
        '高风险': '建议在医生指导下考虑药物或手术治疗',
        '中风险': '以生活方式干预为主，必要时药物治疗',
        '低风险': '保持健康生活方式即可'
    }
    treatment_recommendation = treatment_map.get(risk_level, '请咨询医生')

    # 随访计划
    follow_up_map = {
        '高风险': '每月随访一次，监测体重和相关指标',
        '中风险': '每1-3个月随访一次',
        '低风险': '每6-12个月随访一次'
    }
    follow_up_plan = follow_up_map.get(risk_level, '每6-12个月随访一次')

    return {
        'assessment_date': data.get('assessment_date', ''),
        'report_number': patient_info.get('report_number', ''),
        'height': height,
        'weight': weight,
        'bmi': bmi_value,
        'bmi_level': bmi_level,
        'waist': waist,
        'waist_threshold': waist_threshold,
        'central_obesity_level': central_level,
        'waist_result': waist_result,
        'waist_met': waist_met,
        'glucose_result': glucose_result,
        'glucose_met': glucose_met,
        'bp_result': bp_result,
        'bp_met': bp_met,
        'tg_result': tg_result,
        'tg_met': tg_met,
        'hdl_result': hdl_result,
        'hdl_met': hdl_met,
        'metabolic_syndrome_diagnosis': metabolic_diagnosis,
        'body_fat_section': body_fat_section,
        'related_diseases_section': related_section,
        'target_weight': target_weight,
        'weight_loss_goal': weight_loss_goal,
        'lifestyle_intervention': lifestyle_intervention,
        'treatment_recommendation': treatment_recommendation,
        'follow_up_plan': follow_up_plan,
    }


def _build_structured_result(risk_data, overall_risk, health_metrics, input_data):
    """Build structured result for unified assessment JSON schema."""
    risk_grade = overall_risk.get('risk_grade', '') or overall_risk.get('risk_level', '')
    category = _map_risk_to_category(risk_grade)

    # 1. Population classification
    primary = "健康"
    if "高危" in risk_grade or "很高危" in risk_grade:
        primary = "重症"
    elif "中危" in risk_grade or "中" in risk_grade:
        primary = "慢病"
    elif "低" in risk_grade:
        primary = "亚健康"

    # Grouping basis
    disease_risks = []
    bmi = risk_data.get('bmi')
    waist = risk_data.get('waist_circumference')
    if bmi:
        try:
            bv = float(bmi)
            if bv >= 32:
                disease_risks.append("重度肥胖")
            elif bv >= 28:
                disease_risks.append("肥胖")
            elif bv >= 24:
                disease_risks.append("超重")
        except (ValueError, TypeError):
            pass
    if waist:
        try:
            wv = float(waist)
            if wv >= 90:
                disease_risks.append("中心性肥胖")
        except (ValueError, TypeError):
            pass

    disease_staging = ""
    if bmi:
        try:
            bv = float(bmi)
            if bv >= 32:
                disease_staging = "重度肥胖"
            elif bv >= 28:
                disease_staging = "肥胖"
            elif bv >= 24:
                disease_staging = "超重"
        except (ValueError, TypeError):
            pass

    population_classification = {
        "primary_category": primary,
        "grouping_basis": [{
            "disease": "肥胖",
            "type": disease_staging or "",
            "level": risk_grade or "",
            "note": f"{disease_staging}{risk_grade or ''}" if disease_staging else (risk_grade or ""),
        }],
    }

    # 2. Recommended data collection (check for missing vitals)
    recommended = []
    if not risk_data.get('bmi'):
        recommended.append({"item": "BMI计算(身高/体重)", "reason": "缺少BMI数据"})
    if not risk_data.get('waist'):
        recommended.append({"item": "腰围测量", "reason": "缺少腰围数据"})
    body_fat = input_data.get('body_fat', {})
    if not body_fat.get('available'):
        recommended.append({"item": "体脂率检测", "reason": "需要评估体脂率"})

    # 3. Abnormal indicators
    abnormal = []
    bmi_val = risk_data.get('bmi')
    if bmi_val:
        try:
            bv = float(bmi_val)
            if bv >= 28:
                abnormal.append({"indicator": "BMI", "value": f"{bmi_val} kg/m²", "reference": "18.5-23.9 kg/m²"})
            elif bv >= 24:
                abnormal.append({"indicator": "BMI", "value": f"{bmi_val} kg/m²", "reference": "18.5-23.9 kg/m²"})
        except (ValueError, TypeError):
            pass
    waist_val = risk_data.get('waist')
    waist_threshold = risk_data.get('waist_threshold', 90)
    if waist_val:
        try:
            wv = float(waist_val)
            wt = float(waist_threshold)
            if wv >= wt:
                abnormal.append({"indicator": "腰围", "value": f"{waist_val} cm", "reference": f"<{waist_threshold} cm"})
        except (ValueError, TypeError):
            pass

    # 4. Disease prediction
    disease_prediction = []
    risk_level = overall_risk.get('risk_level', '')
    metabolic_diag = risk_data.get('metabolic_syndrome_diagnosis', '')
    if '代谢综合征' in metabolic_diag and '未' not in metabolic_diag:
        disease_prediction.append({"disease": "代谢综合征", "risk": "高", "description": "多种代谢异常聚集，心血管风险显著增加"})
    if risk_level in ('高风险',):
        disease_prediction.append({"disease": "代谢综合征风险", "risk": "高", "description": "肥胖相关代谢异常风险增加"})
    if bmi_val:
        try:
            bv = float(bmi_val)
            if bv >= 28:
                disease_prediction.append({"disease": "肥胖相关疾病", "risk": "高", "description": "2型糖尿病、高血压、冠心病等风险显著增加"})
        except (ValueError, TypeError):
            pass

    # 5. Intervention prescriptions
    prescriptions = []
    prescriptions.append({"type": "饮食", "content": ["控制每日总热量摄入", "减少高热量食物", "增加蔬果和膳食纤维"], "priority": "高"})
    prescriptions.append({"type": "运动", "content": ["每周150分钟以上中等强度有氧运动", "减少久坐"], "priority": "高"})
    prescriptions.append({"type": "睡眠", "content": ["保证充足睡眠，规律作息", "避免熬夜"], "priority": "中"})
    if risk_level in ('高风险',):
        prescriptions.append({"type": "体重管理", "content": ["建议在医生指导下进行系统体重管理"], "priority": "高"})

    # Risk warnings
    risk_warnings = []

    # Build prediction data
    metabolic_diag = risk_data.get('metabolic_syndrome_diagnosis', '')
    has_metabolic = '代谢综合征' in metabolic_diag and '未' not in metabolic_diag
    target_weight = risk_data.get('target_weight', '')
    risk_level = overall_risk.get('risk_level', '')

    follow_up_map = {
        '高风险': '每月', '中风险': '每1-3个月', '低风险': '每6-12个月',
    }
    follow_up = follow_up_map.get(risk_level, '每3-6个月')

    key_factors = []
    if bmi:
        try:
            bv = float(bmi)
            if bv >= 32:
                key_factors.append("重度肥胖")
            elif bv >= 28:
                key_factors.append("肥胖")
            elif bv >= 24:
                key_factors.append("超重")
        except (ValueError, TypeError):
            pass
    if has_metabolic:
        key_factors.append("代谢综合征")
    if risk_level in ('高风险',):
        key_factors.append("多种代谢异常聚集")

    prediction = None
    if key_factors:
        prediction = {
            "risk_type": "metabolic",
            "timeframe": "长期",
            "risk_level": risk_level or risk_grade,
            "key_factors": key_factors,
            "follow_up": follow_up,
        }
        if target_weight:
            prediction["target_weight"] = str(target_weight)

    if bmi:
        try:
            bv = float(bmi)
            if bv >= 32:
                desc = f"BMI {bmi}，属于重度肥胖，需医学干预"
                if prediction:
                    desc += f"；建议{follow_up}随访"
                risk_warnings.append({"title": "重度肥胖", "description": desc, "level": "high", "prediction": prediction})
            elif bv >= 28:
                desc = f"BMI {bmi}，属于肥胖，建议减重"
                if prediction:
                    desc += f"；建议{follow_up}随访"
                risk_warnings.append({"title": "肥胖预警", "description": desc, "level": "medium", "prediction": prediction})
            elif bv >= 24:
                desc = f"BMI {bmi}，属于超重，建议控制体重"
                risk_warnings.append({"title": "超重提醒", "description": desc, "level": "low", "prediction": prediction})
        except (ValueError, TypeError):
            pass

    return {
        "population_classification": population_classification,
        "recommended_data_collection": recommended,
        "abnormal_indicators": abnormal,
        "disease_prediction": disease_prediction,
        "intervention_prescriptions": prescriptions,
        "risk_warnings": risk_warnings,
    }


def _map_risk_to_category(risk_grade):
    if not risk_grade:
        return "健康"
    grade = risk_grade.lower()
    if "很高危" in grade or "极高" in grade:
        return "重症"
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
                overall_risk = input_data.get('overall_risk', {})
                health_metrics = input_data.get('bmi_assessment', {})
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
