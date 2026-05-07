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

---

## 前置准备

### 依赖说明
```
pyyaml==6.0.1
requests==2.31.0
```

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

### 步骤2：肥胖风险评估
```bash
python scripts/risk_calculator.py --input validated_data.json
```

**评估内容**：
- BMI计算与分级
- 中心型肥胖评估（腰围）
- 代谢综合征筛查
- 肥胖相关疾病风险评估
- 体脂分析（如有数据）

### 步骤3：报告生成
```bash
python scripts/template_manager.py --template report --render --format modules
```

**报告内容**：
- BMI评估与分级
- 中心型肥胖评估
- 代谢综合征评估
- 肥胖相关疾病风险
- 减重治疗建议（生活方式+药物+手术）
- 随访计划

---

## 资源索引

### 脚本
- [scripts/health_data_validator.py](scripts/health_data_validator.py)：数据验证
- [scripts/risk_calculator.py](scripts/risk_calculator.py)：风险评估计算

### 参考文档
- [references/data_collection_checklist.md](references/data_collection_checklist.md)：数据采集清单
- [references/assessment_standards.md](references/assessment_standards.md)：肥胖评估标准
- [references/template_format_spec.md](references/template_format_spec.md)：数据格式规范

### 报告模板
- [assets/report_template.md](assets/report_template.md)：肥胖评估报告模板

---

## 改善建议生成规则

根据评估结果生成个性化改善建议，输出 JSON 数组，每项格式：
```json
{"type": "diet|exercise|sleep|monitoring|medication", "title": "处方标题", "content": ["建议1", "建议2"], "priority": "high|medium|low"}
```

### 生成规则

1. **饮食处方** (type: diet)
   - 超重(BMI 24-27.9) → 控制总热量，减少高脂高糖食物
   - 肥胖(BMI ≥28) → 严格热量控制，每日减少500-750kcal
   - 增加膳食纤维、蔬菜水果摄入
   - 避免暴饮暴食，细嚼慢咽

2. **运动处方** (type: exercise)
   - 超重 → 中等强度有氧运动，每周150分钟
   - 肥胖 → 逐步增加至每周300分钟
   - 结合抗阻训练，每周2-3次
   - 体重过大 → 从低冲击运动开始（游泳、骑车），保护关节

3. **睡眠处方** (type: sleep)
   - 保证7-8小时规律睡眠
   - 睡眠不足可影响食欲激素，导致体重增加
   - 关注OSAHS风险（打鼾、白天嗜睡）

4. **监测处方** (type: monitoring)
   - 超重 → 每周测量体重，每月测量腰围
   - 肥胖 → 每周测量体重+腰围，每3个月评估代谢指标
   - 关注血压、血糖、血脂变化

5. **药物/手术处方** (type: medication)
   - BMI ≥27+合并症 → 可考虑减重药物（医生评估）
   - BMI ≥32 → 可考虑减重手术评估
   - 所有药物建议附"请在医生指导下使用"提示

## 注意事项

- BMI不适用于运动员、孕妇、老年人
- 腰围是评估中心型肥胖的关键指标
- 代谢综合征需满足3项及以上异常
- 评估结论仅供参考，不能替代医生诊断

## 协同工作

本Skill可与其他专项评估Skill协同使用：
- `hypertension-risk-assessment`：高血压评估
- `hyperglycemia-risk-assessment`：高血糖评估
- `hyperlipidemia-risk-assessment`：高血脂评估
- `hyperuricemia-risk-assessment`：高尿酸评估

多Skill评估结果可合并生成综合健康报告。
