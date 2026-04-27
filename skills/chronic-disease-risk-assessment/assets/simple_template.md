---
template_name: 简化版评估报告
template_version: 1.0
sections:
  - 基本信息
  - 风险等级
  - 健康建议
variables:
  - patient_name
  - assessment_date
  - risk_grade
  - total_score
  - max_score
  - recommendations
---

# 健康风险评估简报

## 基本信息

**姓名**: {{patient_name}}  
**评估日期**: {{assessment_date}}  

---

## 风险等级

**总体风险**: {{risk_grade}}  
**风险评分**: {{total_score}}/{{max_score}}

---

## 健康建议

{{recommendations}}

---

*本报告仅供参考，请咨询专业医生*
