---
name: hyperglycemia-risk-assessment
description: 高血糖健康风险评估，提供糖代谢状态评估、糖尿病风险预测、并发症筛查；当用户需要进行血糖风险评估、糖尿病筛查、糖代谢异常分析或降糖治疗指导时使用
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

# 高血糖健康风险评估

## 任务目标
- 本 Skill 用于：高血糖健康风险评估与糖尿病管理
- 核心能力：
  - 糖代谢状态评估（正常/糖尿病前期/糖尿病）
  - 糖尿病风险预测（3年转化风险）
  - 胰岛素抵抗评估（HOMA-IR）
  - 糖尿病并发症筛查
  - 降糖治疗建议
- 触发条件：用户需要评估血糖风险、筛查糖尿病、分析糖代谢异常或制定血糖管理方案

## 核心原则

### 数据采集原则
- **真实性**：所有健康指标数据必须基于真实检测值，禁止主观臆断
- **完整性**：必采指标缺失时，引导用户补充，不得进行评估
- **规范性**：数据采集严格遵循 [数据采集清单](references/data_collection_checklist.md)

### 健康评估原则
- **循证医学**：评估标准遵循《中国2型糖尿病防治指南2020年版》
- **证据导向**：所有结论需注明参考标准和证据来源
- **客观严谨**：基于客观数据和循证医学证据，不带主观判断

### 必采指标（高血糖评估）

| 分类 | 指标 | 说明 |
|------|------|------|
| 基础体格 | 身高、体重、腰围、收缩压、舒张压 | 风险分层基础 |
| 糖代谢 | 空腹血糖、HbA1c | 糖代谢评估核心 |
| 脂代谢 | TC、TG、LDL-C、HDL-C | 代谢综合征评估 |
| 尿酸 | 血尿酸 | 代谢综合征评估 |

### 推荐指标
- OGTT 2小时血糖：隐性糖尿病筛查
- 空腹胰岛素：HOMA-IR计算
- eGFR、UACR：糖尿病肾病筛查
- 眼底检查：糖尿病视网膜病变筛查
