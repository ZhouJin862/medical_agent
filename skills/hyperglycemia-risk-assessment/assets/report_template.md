---
template_name: 高血糖健康风险评估报告
template_version: 1.0
assessment_type: hyperglycemia
---

# 高血糖健康风险评估报告

报告编号： {{report_number}} | 评估日期： {{assessment_date}}

## 一、糖代谢状态评估

### 血糖测量值
| 项目 | 测量值 | 参考标准 |
|------|--------|---------|
| 空腹血糖 | {{fasting_glucose}} mmol/L | <6.1 mmol/L |
| 糖化血红蛋白 | {{hba1c}} % | <5.7% |

### 糖代谢状态
**{{glucose_status}}**

{{glucose_description}}

**参考标准**：《中国2型糖尿病防治指南2020年版》

---

## 二、糖尿病风险评估

### 糖尿病前期评估
{{prediabetes_assessment}}

### 3年糖尿病转化风险
**{{three_year_risk}}%**

---

## 三、胰岛素抵抗评估

{{insulin_resistance_section}}

---

## 四、并发症风险筛查

{{complications_section}}

---

## 五、干预建议

### 血糖控制目标
{{glucose_target}}

### 生活方式干预
{{lifestyle_intervention}}

### 药物治疗建议
{{medication_recommendation}}

### 随访计划
{{follow_up_plan}}

---

## 免责声明

本报告由AI辅助生成，评估结果仅供参考，不能替代专业医生的诊断和治疗建议。如有健康问题，请及时就医。

---

> 评估标准来源：《中国2型糖尿病防治指南2020年版》（中华医学会糖尿病学分会）
