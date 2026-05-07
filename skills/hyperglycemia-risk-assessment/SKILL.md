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

---

## 前置准备

### 依赖说明
```
pyyaml==6.0.1
requests==2.31.0
```

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

### 步骤2：血糖风险评估
```bash
python scripts/risk_calculator.py --input validated_data.json
```

**评估内容**：
- 糖代谢状态分类（正常/IFG/IGT/糖尿病）
- 糖尿病前期风险评估
- 3年糖尿病转化风险预测
- 胰岛素抵抗评估（如有胰岛素数据）
- 糖尿病并发症风险筛查

### 步骤3：报告生成
```bash
python scripts/template_manager.py --template report --render --format modules
```

**报告内容**：
- 糖代谢状态评估
- 糖尿病风险预测
- 胰岛素抵抗评估（如有数据）
- 并发症风险筛查（如有数据）
- 血糖管理建议（生活方式+药物）
- 随访计划

---

## 资源索引

### 脚本
- [scripts/health_data_validator.py](scripts/health_data_validator.py)：数据验证
- [scripts/risk_calculator.py](scripts/risk_calculator.py)：风险评估计算

### 参考文档
- [references/data_collection_checklist.md](references/data_collection_checklist.md)：数据采集清单
- [references/assessment_standards.md](references/assessment_standards.md)：高血糖评估标准
- [references/template_format_spec.md](references/template_format_spec.md)：数据格式规范

### 报告模板
- [assets/report_template.md](assets/report_template.md)：高血糖评估报告模板

---

## 改善建议生成规则

根据评估结果生成个性化改善建议，输出 JSON 数组，每项格式：
```json
{"type": "diet|exercise|sleep|monitoring|medication", "title": "处方标题", "content": ["建议1", "建议2"], "priority": "high|medium|low"}
```

### 生成规则

1. **饮食处方** (type: diet)
   - 糖尿病前期 → 控制碳水化合物摄入，选择低GI食物
   - 糖尿病 → 严格控制总热量，分餐制，避免单次大量进食
   - 合并高血脂 → 低脂饮食，限制饱和脂肪
   - 合并高血压 → 限盐<6g/天

2. **运动处方** (type: exercise)
   - 糖尿病前期 → 中等强度有氧运动，每周150分钟，可降低58%发病风险
   - 糖尿病 → 餐后30分钟运动，避免空腹运动防低血糖
   - 合并肥胖 → 增加运动至每周300分钟
   - HbA1c>9% → 避免高强度运动，血糖控制后再增加强度

3. **睡眠处方** (type: sleep)
   - 保证7-8小时规律睡眠
   - 睡眠不足会加重胰岛素抵抗
   - 规律作息有助血糖控制

4. **监测处方** (type: monitoring)
   - 正常血糖 → 每年检测空腹血糖
   - 糖尿病前期 → 每3-6个月检测空腹血糖+HbA1c
   - 糖尿病 → 每月测空腹+餐后血糖，每3个月测HbA1c
   - 关注并发症筛查（眼底、肾功能、足部检查）

5. **药物处方** (type: medication)
   - 糖尿病前期可考虑二甲双胍（需医生评估）
   - 确诊糖尿病 → 遵医嘱规范用药
   - 合并心血管病 → 优先选择SGLT2i或GLP-1RA
   - 所有药物建议附"请在医生指导下使用"提示

## 注意事项

- 空腹血糖需禁食8-10小时后检测
- HbA1c反映近2-3个月血糖控制情况
- IFG和IGT统称为糖尿病前期
- 评估结论仅供参考，不能替代医生诊断

## 协同工作

本Skill可与其他专项评估Skill协同使用：
- `hypertension-risk-assessment`：高血压评估
- `hyperlipidemia-risk-assessment`：高血脂评估
- `hyperuricemia-risk-assessment`：高尿酸评估
- `obesity-risk-assessment`：肥胖评估

多Skill评估结果可合并生成综合健康报告。
