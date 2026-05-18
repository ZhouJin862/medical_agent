---
name: hyperlipidemia-risk-assessment
description: 高血脂健康风险评估，提供血脂水平分层、心血管风险评估、降脂治疗建议；当用户需要进行血脂评估、血脂异常分析、心血管风险筛查或降脂治疗指导时使用
dependency:
  python:
    - pyyaml==6.0.1
    - requests==2.31.0
tools:
  - script: scripts/health_data_validator.py
    args: ["--input", "$input"]
  - script: scripts/risk_calculator.py
    args: ["--input", "$prev_output"]
  - script: scripts/template_manager.py
    args: ["--template", "report", "--render", "--format", "modules", "--input", "$prev_output"]
---

# 高血脂健康风险评估

## 任务目标
- 本 Skill 用于：高血脂健康风险评估与血脂管理
- 核心能力：
  - 血脂水平分层（TC/TG/LDL-C/HDL-C）
  - 心血管风险评估（ASCVD风险）
  - 残余风险评估（non-HDL-C、Lp(a)）
  - 血脂异常分类（高胆固醇/高甘油三酯/混合型）
  - 降脂治疗建议
- 触发条件：用户需要评估血脂风险、分析血脂异常、制定降脂方案或进行心血管风险筛查

## 核心原则

### 数据采集原则
- **真实性**：所有健康指标数据必须基于真实检测值，禁止主观臆断
- **完整性**：必采指标缺失时，引导用户补充，不得进行评估
- **规范性**：数据采集严格遵循 [数据采集清单](references/data_collection_checklist.md)

### 健康评估原则
- **循证医学**：评估标准遵循《中国成人血脂异常防治指南2016年修订版》
- **证据导向**：所有结论需注明参考标准和证据来源
- **客观严谨**：基于客观数据和循证医学证据，不带主观判断

### 必采指标（高血脂评估）

| 分类 | 指标 | 说明 |
|------|------|------|
| 基础体格 | 身高、体重、腰围、收缩压、舒张压 | 风险分层基础 |
| 糖代谢 | 空腹血糖、HbA1c | 糖代谢状态评估 |
| 脂代谢 | TC、TG、LDL-C、HDL-C | 血脂评估核心 |
| 尿酸 | 血尿酸 | 代谢综合征评估 |

### 推荐指标
- non-HDL-C：残余风险评估
- Lp(a)：残余风险评估
- 颈动脉超声：动脉粥样硬化评估
- eGFR、UACR：肾功能评估