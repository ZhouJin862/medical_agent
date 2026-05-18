---
name: obesity-risk-assessment
description: 肥胖健康风险评估，提供BMI评估、中心型肥胖筛查、代谢综合征评估、肥胖相关疾病风险预测；当用户需要进行体重管理、肥胖评估、代谢综合征筛查或减重治疗指导时使用
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

# 肥胖健康风险评估

## 任务目标
- 本 Skill 用于：肥胖健康风险评估与体重管理
- 核心能力：
  - BMI评估与分级（低体重/正常/超重/肥胖I-III级）
  - 中心型肥胖筛查（腰围评估）
  - 代谢综合征评估
  - 肥胖相关疾病风险预测
  - 减重治疗建议
- 触发条件：用户需要评估体重风险、分析肥胖程度、制定减重方案或进行代谢综合征筛查

## 核心原则

### 数据采集原则
- **真实性**：所有健康指标数据必须基于真实检测值，禁止主观臆断
- **完整性**：必采指标缺失时，引导用户补充，不得进行评估
- **规范性**：数据采集严格遵循 [数据采集清单](references/data_collection_checklist.md)

### 健康评估原则
- **循证医学**：评估标准遵循《中国成人超重和肥胖症预防控制指南》
- **证据导向**：所有结论需注明参考标准和证据来源
- **客观严谨**：基于客观数据和循证医学证据，不带主观判断

### 必采指标（肥胖评估）

| 分类 | 指标 | 说明 |
|------|------|------|
| 基础体格 | 身高、体重、腰围、收缩压、舒张压 | 肥胖评估核心 |
| 糖代谢 | 空腹血糖、HbA1c | 代谢综合征评估 |
| 脂代谢 | TC、TG、LDL-C、HDL-C | 代谢综合征评估 |
| 尿酸 | 血尿酸 | 代谢综合征评估 |

### 推荐指标
- 体脂率：身体成分评估
- 内脏脂肪等级：内脏脂肪评估
- 腹部超声：脂肪肝评估
- 颈围：OSAHS风险评估