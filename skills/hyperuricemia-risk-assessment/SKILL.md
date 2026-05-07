---
name: hyperuricemia-risk-assessment
description: 高尿酸健康风险评估，提供尿酸水平评估、痛风风险预测、肾脏损害评估；当用户需要进行尿酸评估、痛风风险筛查、高尿酸血症管理或肾功能评估时使用
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

# 高尿酸健康风险评估

## 任务目标
- 本 Skill 用于：高尿酸健康风险评估与痛风管理
- 核心能力：
  - 尿酸水平评估（正常/高尿酸血症）
  - 痛风风险预测
  - 肾脏损害评估（eGFR、UACR）
  - 代谢综合征关联评估
  - 降尿酸治疗建议
- 触发条件：用户需要评估尿酸风险、筛查痛风、分析高尿酸血症或制定尿酸管理方案

## 核心原则

### 数据采集原则
- **真实性**：所有健康指标数据必须基于真实检测值，禁止主观臆断
- **完整性**：必采指标缺失时，引导用户补充，不得进行评估
- **规范性**：数据采集严格遵循 [数据采集清单](references/data_collection_checklist.md)

### 健康评估原则
- **循证医学**：评估标准遵循《中国高尿酸血症与痛风诊疗指南2019》
- **证据导向**：所有结论需注明参考标准和证据来源
- **客观严谨**：基于客观数据和循证医学证据，不带主观判断

---

## 前置准备

### 依赖说明
```
pyyaml==6.0.1
requests==2.31.0
```

### 必采指标（高尿酸评估）

| 分类 | 指标 | 说明 |
|------|------|------|
| 基础体格 | 身高、体重、腰围、收缩压、舒张压 | 风险分层基础 |
| 糖代谢 | 空腹血糖、HbA1c | 代谢综合征评估 |
| 脂代谢 | TC、TG、LDL-C、HDL-C | 代谢综合征评估 |
| 尿酸 | 血尿酸 | 尿酸评估核心 |

### 推荐指标
- 血清肌酐、eGFR：肾功能评估
- UACR：早期肾损害评估
- 关节超声：痛风性关节炎评估
- 24小时尿尿酸：尿酸分型

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

### 步骤2：尿酸风险评估
```bash
python scripts/risk_calculator.py --input validated_data.json
```

**评估内容**：
- 尿酸水平评估（正常/高尿酸血症）
- 痛风风险评估
- 肾功能评估（如有数据）
- 代谢综合征评估
- 心血管风险关联评估

### 步骤3：报告生成
```bash
python scripts/template_manager.py --template report --render --format modules
```

**报告内容**：
- 尿酸水平评估
- 痛风风险预测
- 肾功能评估（如有数据）
- 代谢综合征评估
- 降尿酸治疗建议（生活方式+药物）
- 随访计划

---

## 资源索引

### 脚本
- [scripts/health_data_validator.py](scripts/health_data_validator.py)：数据验证
- [scripts/risk_calculator.py](scripts/risk_calculator.py)：风险评估计算

### 参考文档
- [references/data_collection_checklist.md](references/data_collection_checklist.md)：数据采集清单
- [references/assessment_standards.md](references/assessment_standards.md)：高尿酸评估标准
- [references/template_format_spec.md](references/template_format_spec.md)：数据格式规范

### 报告模板
- [assets/report_template.md](assets/report_template.md)：高尿酸评估报告模板

---

## 改善建议生成规则

根据评估结果生成个性化改善建议，输出 JSON 数组，每项格式：
```json
{"type": "diet|exercise|sleep|monitoring|medication", "title": "处方标题", "content": ["建议1", "建议2"], "priority": "high|medium|low"}
```

### 生成规则

1. **饮食处方** (type: diet)
   - 高尿酸血症 → 低嘌呤饮食，避免内脏、海鲜、浓汤
   - 限制饮酒（尤其啤酒），限制含糖饮料
   - 增加低脂乳制品、蔬菜摄入
   - 避免禁食/快速减重（可诱发痛风）

2. **运动处方** (type: exercise)
   - 规律中等强度运动，控制体重
   - 痛风发作期 → 避免运动，休息
   - 避免剧烈运动和大量出汗（可诱发痛风）

3. **睡眠处方** (type: sleep)
   - 保证充足睡眠，规律作息
   - 避免熬夜，过度疲劳可诱发痛风

4. **监测处方** (type: monitoring)
   - 无症状高尿酸 → 每3-6个月复查尿酸
   - 痛风患者 → 每1-3个月复查尿酸+肾功能
   - 关注血压、血糖、血脂（代谢综合征关联）

5. **饮水建议** (type: monitoring)
   - 每日饮水2000ml以上，促进尿酸排泄
   - 选择白开水或淡茶水

6. **药物处方** (type: medication)
   - 尿酸≥540 → 建议降尿酸治疗
   - 尿酸≥480+合并症 → 建议降尿酸治疗
   - 痛风急性期 → 抗炎止痛（非降尿酸时机）
   - 所有药物建议附"请在医生指导下使用"提示

## 注意事项

- 尿酸检测需空腹，避免高嘌呤饮食3天
- 男性正常上限：416 μmol/L，女性：357 μmol/L
- 高尿酸血症是心血管疾病独立危险因素
- 评估结论仅供参考，不能替代医生诊断

## 协同工作

本Skill可与其他专项评估Skill协同使用：
- `hypertension-risk-assessment`：高血压评估
- `hyperglycemia-risk-assessment`：高血糖评估
- `hyperlipidemia-risk-assessment`：高血脂评估
- `obesity-risk-assessment`：肥胖评估

多Skill评估结果可合并生成综合健康报告。
