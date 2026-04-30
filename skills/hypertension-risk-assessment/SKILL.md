---
name: hypertension-risk-assessment
description: 高血压健康风险评估，提供血压水平分层、靶器官损害评估、心血管风险预测；当用户需要进行高血压风险评估、血压异常分析、心血管风险筛查或降压治疗指导时使用
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

# 高血压健康风险评估

## 任务目标
- 本 Skill 用于：高血压健康风险评估与血压管理
- 核心能力：
  - 血压水平分层（正常/正常高值/1-3级高血压）
  - 心血管风险预测（China-PAR 10年ASCVD风险）
  - 靶器官损害评估（心脏、血管、肾脏、眼底）
  - H型高血压筛查（同型半胱氨酸评估）
  - 降压治疗建议
- 触发条件：用户需要评估血压风险、分析血压异常、制定降压方案或进行高血压相关健康咨询

## 核心原则

### 数据采集原则
- **真实性**：所有健康指标数据必须基于真实检测值，禁止主观臆断
- **完整性**：必采指标缺失时，引导用户补充，不得进行评估
- **规范性**：数据采集严格遵循 [数据采集清单](references/data_collection_checklist.md)

### 健康评估原则
- **循证医学**：评估标准遵循《中国高血压防治指南2018年修订版》
- **证据导向**：所有结论需注明参考标准和证据来源
- **客观严谨**：基于客观数据和循证医学证据，不带主观判断

---

## 前置准备

### 依赖说明
```
pyyaml==6.0.1
requests==2.31.0
```

### 必采指标（高血压评估）

| 分类 | 指标 | 说明 |
|------|------|------|
| 基础体格 | 身高、体重、腰围、收缩压、舒张压 | 风险分层基础 |
| 糖代谢 | 空腹血糖、HbA1c | 糖代谢状态评估 |
| 脂代谢 | TC、TG、LDL-C、HDL-C | 心血管风险评估 |
| 尿酸 | 血尿酸 | 代谢综合征评估 |

### 推荐指标
- 同型半胱氨酸：H型高血压筛查
- 颈动脉超声：靶器官损害评估
- eGFR、UACR：肾功能评估
- 心电图/超声心动图：心脏评估

### 输入方式

#### 方式一：文件输入
```bash
python scripts/health_data_validator.py --input health_data.json
```

#### 方式二：图片识别
用户上传体检报告图片，智能体识别并整理为标准格式

#### 方式三：手动录入
用户告知健康指标，智能体整理为标准格式

---

## 操作步骤

### 步骤1：数据验证
```bash
python scripts/health_data_validator.py --input <健康数据文件>
```

### 步骤2：血压风险评估
```bash
python scripts/risk_calculator.py --input validated_data.json
```

**评估内容**：
- 血压水平分类（正常/正常高值/高血压1-3级）
- 心血管风险分层（低危/中危/高危/很高危）
- China-PAR 10年ASCVD风险预测
- 靶器官损害评估
- H型高血压判定

### 步骤3：报告生成
```bash
python scripts/template_manager.py --template report --render --format modules
```

**报告内容**：
- 血压水平评估与分级
- 心血管风险预测
- 靶器官损害评估（如有数据）
- 降压治疗建议（生活方式+药物）
- 随访计划

---

## 资源索引

### 脚本
- [scripts/health_data_validator.py](scripts/health_data_validator.py)：数据验证
- [scripts/risk_calculator.py](scripts/risk_calculator.py)：风险评估计算

### 参考文档
- [references/data_collection_checklist.md](references/data_collection_checklist.md)：数据采集清单
- [references/assessment_standards.md](references/assessment_standards.md)：高血压评估标准
- [references/template_format_spec.md](references/template_format_spec.md)：数据格式规范

### 报告模板
- [assets/report_template.md](assets/report_template.md)：高血压评估报告模板

---

## 注意事项

- 血压测量应在安静休息至少5分钟后进行
- 建议非同日测量3次以上确诊
- 家庭自测血压诊断标准：≥135/85mmHg
- 评估结论仅供参考，不能替代医生诊断

## 协同工作

本Skill可与其他专项评估Skill协同使用：
- `hyperglycemia-risk-assessment`：高血糖评估
- `hyperlipidemia-risk-assessment`：高血脂评估
- `hyperuricemia-risk-assessment`：高尿酸评估
- `obesity-risk-assessment`：肥胖评估

多Skill评估结果可合并生成综合健康报告。
