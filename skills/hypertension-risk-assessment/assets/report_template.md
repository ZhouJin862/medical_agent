---
template_name: 高血压健康风险评估报告
template_version: 1.0
assessment_type: hypertension
---

# 高血压健康风险评估报告

报告编号： {{report_number}} | 评估日期： {{assessment_date}}

## 一、血压水平评估

### 血压测量值
| 项目 | 测量值 | 参考标准 |
|------|--------|---------|
| 收缩压 | {{systolic}} mmHg | <140 mmHg |
| 舒张压 | {{diastolic}} mmHg | <90 mmHg |

### 血压分级
**{{bp_level}}**

{{bp_description}}

**参考标准**：《中国高血压防治指南2018年修订版》

---

## 二、心血管风险分层

### 危险因素评估
{{risk_factors_summary}}

### 风险分层结果
**{{risk_stratification}}**

| 项目 | 结果 |
|------|------|
| 血压级别 | {{bp_grade}} |
| 危险因素数量 | {{risk_factors_count}}项 |
| 靶器官损害 | {{organ_damage_status}} |
| 综合风险 | {{risk_stratification}} |

---

## 三、靶器官损害评估

{{organ_damage_section}}

---

## 四、H型高血压筛查

{{h_type_assessment}}

---

## 五、干预建议

### 血压控制目标
{{bp_target}}

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

> 评估标准来源：《中国高血压防治指南2018年修订版》（中国高血压联盟）
