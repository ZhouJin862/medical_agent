---
template_name: 高血脂健康风险评估报告
template_version: 1.0
assessment_type: hyperlipidemia
---

# 高血脂健康风险评估报告

报告编号： {{report_number}} | 评估日期： {{assessment_date}}

## 一、血脂水平评估

### 血脂测量值
| 项目 | 测量值 | 参考标准 | 评估 |
|------|--------|---------|------|
| 总胆固醇(TC) | {{tc}} mmol/L | <5.18 mmol/L | {{tc_level}} |
| 甘油三酯(TG) | {{tg}} mmol/L | <1.70 mmol/L | {{tg_level}} |
| LDL-C | {{ldl_c}} mmol/L | <3.35 mmol/L | {{ldl_c_level}} |
| HDL-C | {{hdl_c}} mmol/L | ≥1.04 mmol/L | {{hdl_c_level}} |

### 血脂异常分类
**{{lipid_disorder_type}}**

**参考标准**：《中国成人血脂异常防治指南2016年修订版》

---

## 二、LDL-C危险分层

### 危险分层结果
**{{risk_tier}}**

| 项目 | 结果 |
|------|------|
| LDL-C水平 | {{ldl_c}} mmol/L |
| 危险分层 | {{risk_tier}} |
| LDL-C目标值 | {{ldl_target}} |
| 是否达标 | {{at_target}} |

---

## 三、残余风险评估

{{residual_risk_section}}

---

## 四、心血管风险评估

{{cardiovascular_risk_section}}

---

## 五、干预建议

### LDL-C控制目标
{{ldl_control_target}}

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

> 评估标准来源：《中国成人血脂异常防治指南2016年修订版》（中国成人血脂异常防治指南修订联合委员会）
