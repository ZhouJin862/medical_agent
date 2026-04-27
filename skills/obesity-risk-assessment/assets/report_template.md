---
template_name: 肥胖健康风险评估报告
template_version: 1.0
assessment_type: obesity
---

# 肥胖健康风险评估报告

报告编号： {{report_number}} | 评估日期： {{assessment_date}}

## 一、BMI评估

### 体格测量值
| 项目 | 测量值 |
|------|--------|
| 身高 | {{height}} cm |
| 体重 | {{weight}} kg |
| BMI | {{bmi}} kg/m² |

### BMI分级
**{{bmi_level}}**

| 分类 | BMI范围(kg/m²) |
|------|---------------|
| 体重过低 | <18.5 |
| 正常 | 18.5-23.9 |
| 超重 | 24.0-27.9 |
| 肥胖I级 | 28.0-32.9 |
| 肥胖II级 | 33.0-37.9 |
| 肥胖III级 | ≥38.0 |

**参考标准**：《中国成人超重和肥胖症预防控制指南》

---

## 二、中心型肥胖评估

### 腰围测量
| 项目 | 测量值 | 参考标准 |
|------|--------|---------|
| 腰围 | {{waist}} cm | <{{waist_threshold}} cm |

### 中心型肥胖判定
**{{central_obesity_level}}**

---

## 三、代谢综合征评估

### 诊断标准（满足≥3项）

| 标准 | 结果 | 是否满足 |
|------|------|---------|
| 中心型肥胖 | {{waist_result}} | {{waist_met}} |
| 高血糖 | {{glucose_result}} | {{glucose_met}} |
| 高血压 | {{bp_result}} | {{bp_met}} |
| 高甘油三酯 | {{tg_result}} | {{tg_met}} |
| 低HDL-C | {{hdl_result}} | {{hdl_met}} |

### 代谢综合征诊断
**{{metabolic_syndrome_diagnosis}}**

---

## 四、体脂评估

{{body_fat_section}}

---

## 五、肥胖相关疾病风险

{{related_diseases_section}}

---

## 六、干预建议

### 目标体重
{{target_weight}}

### 减重目标
{{weight_loss_goal}}

### 生活方式干预
{{lifestyle_intervention}}

### 药物/手术治疗建议
{{treatment_recommendation}}

### 随访计划
{{follow_up_plan}}

---

## 免责声明

本报告由AI辅助生成，评估结果仅供参考，不能替代专业医生的诊断和治疗建议。如有健康问题，请及时就医。

---

> 评估标准来源：《中国成人超重和肥胖症预防控制指南》（中国营养学会）
