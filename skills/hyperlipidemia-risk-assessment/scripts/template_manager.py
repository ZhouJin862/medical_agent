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
    lipid = data.get('lipid_assessment', {})
    disorder = data.get('lipid_disorder_type', {})
    ldl_strat = data.get('ldl_stratification', {})
    residual = data.get('residual_risk', {})
    overall = data.get('overall_risk', {})

    # 血脂值和水平
    tc_info = lipid.get('tc', {})
    tg_info = lipid.get('tg', {})
    ldl_info = lipid.get('ldl_c', {})
    hdl_info = lipid.get('hdl_c', {})

    # 残余风险评估章节
    residual_risks = residual.get('risks', [])
    if residual.get('has_residual_risk') and residual_risks:
        residual_section = "### 残余风险因素\n"
        for r in residual_risks:
            residual_section += f"- {r.get('factor', '')}: {r.get('value', '')}\n"
        non_hdl_c = residual.get('non_hdl_c')
        if non_hdl_c:
            residual_section += f"\nnon-HDL-C: {non_hdl_c:.2f} mmol/L（参考标准：<3.4 mmol/L）\n"
    else:
        residual_section = "未发现显著残余风险因素。"

    # 心血管风险评估章节
    risk_level = overall.get('risk_level', '')
    cvd_section = f"### 综合风险等级\n**{risk_level}**\n\n"
    cvd_section += f"- LDL-C目标: {overall.get('ldl_target', '')}\n"
    cvd_section += f"- 是否达标: {'是' if overall.get('ldl_at_target') else '否'}\n"
    cvd_section += f"\n建议: {overall.get('recommendation', '请咨询医生')}"

    # LDL-C控制目标
    ldl_target = ldl_strat.get('ldl_target', '')
    ldl_control_target = f"LDL-C目标值: {ldl_target}" if ldl_target else "请咨询医生确定目标值"

    # 生活方式干预
    risk_tier = ldl_strat.get('risk_tier', '低危')
    lifestyle_map = {
        '极高危': '1. 严格低脂低盐饮食\n2. 增加膳食纤维摄入\n3. 规律运动，每周≥150分钟\n4. 控制体重\n5. 完全戒烟\n6. 严格限酒',
        '高危': '1. 低脂饮食，限制饱和脂肪\n2. 增加蔬果摄入\n3. 规律有氧运动\n4. 控制体重，BMI<24\n5. 戒烟限酒',
        '中危': '1. 均衡饮食，减少高脂食物\n2. 适量运动\n3. 控制体重\n4. 戒烟限酒',
        '低危': '1. 保持健康饮食\n2. 规律运动\n3. 定期监测血脂'
    }
    lifestyle_intervention = lifestyle_map.get(risk_tier, lifestyle_map['低危'])

    # 药物治疗建议
    medication_map = {
        '极高危': '建议立即启动强化降脂治疗（他汀类药物为基础，必要时联合依折麦布或PCSK9抑制剂）',
        '高危': '建议启动降脂药物治疗（中等强度他汀类药物）',
        '中危': '建议生活方式干预，必要时考虑药物治疗',
        '低危': '以生活方式干预为主，定期监测'
    }
    medication_recommendation = medication_map.get(risk_tier, '请咨询医生')

    # 随访计划
    follow_up_map = {
        '极高危': '每1-3个月随访一次，监测血脂和肝功能',
        '高危': '每1-3个月随访一次',
        '中危': '每3-6个月随访一次',
        '低危': '每6-12个月随访一次'
    }
    follow_up_plan = follow_up_map.get(risk_tier, '每6-12个月随访一次')

    return {
        # 基本信息
        'assessment_date': data.get('assessment_date', ''),
        'report_number': patient_info.get('report_number', ''),

        # 血脂测量值
        'tc': tc_info.get('value', ''),
        'tc_level': tc_info.get('level', ''),
        'tg': tg_info.get('value', ''),
        'tg_level': tg_info.get('level', ''),
        'ldl_c': ldl_info.get('value', ''),
        'ldl_c_level': ldl_info.get('level', ''),
        'hdl_c': hdl_info.get('value', ''),
        'hdl_c_level': hdl_info.get('level', ''),

        # 血脂异常分类
        'lipid_disorder_type': disorder.get('primary_type', ''),

        # LDL-C危险分层
        'risk_tier': risk_tier,
        'ldl_target': ldl_target,
        'at_target': '是' if ldl_strat.get('at_target') else '否',

        # 残余风险
        'residual_risk_section': residual_section,

        # 心血管风险
        'cardiovascular_risk_section': cvd_section,

        # 干预建议
        'ldl_control_target': ldl_control_target,
        'lifestyle_intervention': lifestyle_intervention,
        'medication_recommendation': medication_recommendation,
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
    tc = risk_data.get('tc')
    tg = risk_data.get('tg')
    ldl = risk_data.get('ldl_c')
    hdl = risk_data.get('hdl_c')
    if tc:
        try:
            if float(tc) >= 6.2:
                disease_risks.append("高胆固醇血症")
            elif float(tc) >= 5.2:
                disease_risks.append("边缘升高胆固醇")
        except (ValueError, TypeError):
            pass
    if tg:
        try:
            if float(tg) >= 2.3:
                disease_risks.append("高甘油三酯血症")
            elif float(tg) >= 1.7:
                disease_risks.append("边缘升高甘油三酯")
        except (ValueError, TypeError):
            pass
    if ldl:
        try:
            if float(ldl) >= 4.1:
                disease_risks.append("高低密度脂蛋白血症")
            elif float(ldl) >= 3.4:
                disease_risks.append("边缘升高低密度脂蛋白")
        except (ValueError, TypeError):
            pass
    if hdl:
        try:
            if float(hdl) < 1.0:
                disease_risks.append("低高密度脂蛋白血症")
        except (ValueError, TypeError):
            pass

    disease_staging = ""
    if tc:
        try:
            if float(tc) >= 6.2:
                disease_staging = "高胆固醇血症"
            elif float(tc) >= 5.2:
                disease_staging = "边缘升高"
        except (ValueError, TypeError):
            pass

    population_classification = {
        "primary_category": primary,
        "grouping_basis": [{
            "disease": "高血脂",
            "type": disease_staging or "",
            "level": risk_grade or "",
            "note": f"{disease_staging}{risk_grade or ''}" if disease_staging else (risk_grade or ""),
        }],
    }

    # 2. Recommended data collection (check for missing vitals)
    recommended = []
    if not risk_data.get('tc'):
        recommended.append({"item": "总胆固醇(TC)", "reason": "缺少总胆固醇数据"})
    if not risk_data.get('tg'):
        recommended.append({"item": "甘油三酯(TG)", "reason": "缺少甘油三酯数据"})
    if not risk_data.get('ldl_c'):
        recommended.append({"item": "低密度脂蛋白胆固醇(LDL-C)", "reason": "缺少LDL-C数据"})
    if not risk_data.get('hdl_c'):
        recommended.append({"item": "高密度脂蛋白胆固醇(HDL-C)", "reason": "缺少HDL-C数据"})

    # 3. Abnormal indicators
    abnormal = []
    tc = risk_data.get('tc')
    tg = risk_data.get('tg')
    ldl_c = risk_data.get('ldl_c')
    hdl_c = risk_data.get('hdl_c')
    if tc:
        try:
            tv = float(tc)
            if tv >= 5.2:
                abnormal.append({"indicator": "总胆固醇(TC)", "value": f"{tc} mmol/L", "reference": "<5.2 mmol/L"})
        except (ValueError, TypeError):
            pass
    if tg:
        try:
            tv = float(tg)
            if tv >= 1.7:
                abnormal.append({"indicator": "甘油三酯(TG)", "value": f"{tg} mmol/L", "reference": "<1.7 mmol/L"})
        except (ValueError, TypeError):
            pass
    if ldl_c:
        try:
            lv = float(ldl_c)
            if lv >= 3.4:
                abnormal.append({"indicator": "低密度脂蛋白胆固醇(LDL-C)", "value": f"{ldl_c} mmol/L", "reference": "<3.4 mmol/L"})
        except (ValueError, TypeError):
            pass
    if hdl_c:
        try:
            hv = float(hdl_c)
            if hv < 1.0:
                abnormal.append({"indicator": "高密度脂蛋白胆固醇(HDL-C)", "value": f"{hdl_c} mmol/L", "reference": ">=1.0 mmol/L"})
        except (ValueError, TypeError):
            pass

    # 4. Disease prediction
    disease_prediction = []
    risk_tier = risk_data.get('risk_tier', '')
    if risk_tier in ('极高危', '高危'):
        disease_prediction.append({"disease": "动脉粥样硬化性心血管病(ASCVD)", "risk": "高", "description": "心血管事件风险显著增加"})
    elif risk_tier == '中危':
        disease_prediction.append({"disease": "动脉粥样硬化性心血管病(ASCVD)", "risk": "中", "description": "存在血脂异常相关心血管风险"})
    disorder_type = risk_data.get('lipid_disorder_type', '')
    if disorder_type:
        disease_prediction.append({"disease": f"血脂异常({disorder_type})", "risk": "中", "description": "血脂代谢异常需持续关注"})

    # 5. Intervention prescriptions
    prescriptions = []
    prescriptions.append({"type": "饮食", "content": ["低脂饮食", "减少饱和脂肪和反式脂肪摄入", "增加膳食纤维"], "priority": "高"})
    prescriptions.append({"type": "运动", "content": ["每周150分钟以上中等强度有氧运动"], "priority": "高"})
    if risk_tier in ('极高危', '高危'):
        prescriptions.append({"type": "药物治疗", "content": ["建议在医生指导下进行降脂药物治疗"], "priority": "高"})

    # Risk warnings
    risk_warnings = []

    # Build prediction data
    risk_tier = risk_data.get('risk_tier', '')
    ldl_target = risk_data.get('ldl_target', '')
    at_target = risk_data.get('at_target', False)
    ldl_strat = input_data.get('ldl_stratification', {})

    follow_up_map = {
        '极高危': '每1-3个月', '高危': '每1-3个月',
        '中危': '每3-6个月', '低危': '每6-12个月',
    }
    follow_up = follow_up_map.get(risk_tier, '每3-6个月')

    key_factors = []
    if ldl_c:
        try:
            lv = float(ldl_c)
            if lv >= 4.1:
                key_factors.append("LDL-C显著升高")
            elif lv >= 3.4:
                key_factors.append("LDL-C边缘升高")
        except (ValueError, TypeError):
            pass
    if risk_tier:
        key_factors.append(f"ASCVD风险{risk_tier}")
    if not at_target:
        key_factors.append("LDL-C未达标")

    prediction = None
    if key_factors:
        prediction = {
            "risk_type": "ascvd",
            "timeframe": "10年",
            "risk_level": risk_tier or risk_grade,
            "key_factors": key_factors,
            "follow_up": follow_up,
        }

    if tc:
        try:
            if float(tc) >= 6.2:
                desc = f"总胆固醇{tc}mmol/L，提示高胆固醇血症"
                if prediction:
                    desc += f"；ASCVD风险分层为{risk_tier}，建议{follow_up}复查"
                risk_warnings.append({"title": "胆固醇严重偏高", "description": desc, "level": "high", "prediction": prediction})
            elif float(tc) >= 5.2:
                desc = f"总胆固醇{tc}mmol/L，边缘升高"
                if prediction:
                    desc += f"；建议{follow_up}复查"
                risk_warnings.append({"title": "胆固醇偏高", "description": desc, "level": "medium", "prediction": prediction})
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
                health_metrics = input_data.get('lipid_assessment', {})
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
