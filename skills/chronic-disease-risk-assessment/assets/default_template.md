---
template_name: 个人健康风险评估报告
template_version: 1.0
sections:
  - 健康综合画像与风险分层
  - 四高一重循证证据链
  - 靶器官损害与残余风险
  - 疾病爆发概率预测
  - 阶梯式干预处方
  - 专家综述
variables:
  - report_number
  - assessment_date
  - patient_age
  - core_logic
  - health_score
  - risk_level
  - metabolic_label
  - medical_comment
  - bmi_value
  - waist_circumference
  - ultrasound_evidence
  - obesity_assessment
  - bp_value
  - bp_interpretation
  - bp_target
  - glucose_value
  - glucose_interpretation
  - glucose_target
  - diabetes_complications_risk
  - diabetes_recommendation
  - lipid_value
  - lipid_interpretation
  - lipid_target
  - uric_acid_value
  - uric_acid_interpretation
  - uric_acid_target
  - vascular_evidence
  - vascular_conclusion
  - kidney_evidence
  - kidney_conclusion
  - ascvd_risk_10year
  - diabetes_risk_3year
  - residual_risk_note
  - clinical_treatment
  - lifestyle_intervention
  - expert_summary
---

# 个人健康风险评估报告 (HE-Report)

报告编号： {{report_number}} | 评估日期： {{assessment_date}} | 患者年龄： {{patient_age}}

**核心逻辑**： {{core_logic}}

## 一、 健康综合画像与风险分层 (Risk Stratification)

基于多维数据加权生成的全局风险视图。

|综合健康评分|风险预警级别|临床代谢标签|
|---|---|---|
|{{health_score}}|{{risk_level}}|{{metabolic_label}}|

**【严肃医疗简评】** {{medical_comment}}

## 二、 "四高一重"循证证据链 (Evidence-Based Matrix)

不只是列出数值，而是通过证据映射行业标准。

### 1. 形态与代谢基础（风险源头）

指征： 身体质量指数 (BMI) {{bmi_value}} kg/m² / 腰围 {{waist_circumference}} cm。

关键证据： {{ultrasound_evidence}}。

评估结果： {{obesity_assessment}}。

参考标准： 《中国成人超重和肥胖症预防控制指南》。

### 2. 三高关键指标对照（临床路径）

|检测项目|测量值|循证医学解读 (Evidence)|行业控制靶标 (Standards)|
|---|---|---|---|
|血压 (BP)|{{bp_value}}|{{bp_interpretation}}|{{bp_target}}|
|糖代谢|{{glucose_value}}|{{glucose_interpretation}}|{{glucose_target}}|

{{diabetes_complications_section}}
|血脂谱|{{lipid_value}}|{{lipid_interpretation}}|{{lipid_target}}|
|尿酸 (SUA)|{{uric_acid_value}}|{{uric_acid_interpretation}}|{{uric_acid_target}}|

## 三、 靶器官损害与残余风险 (Organ Damage & Residual Risk)

重点检视长期慢病对心脏、血管、肾脏的器质性改变。

### 1. 血管内皮与斑块评估 (Structural)

影像证据： {{vascular_evidence}}。

深度结论： {{vascular_conclusion}}。

### 2. 微血管与肾功能评估 (Functional)

生化证据： {{kidney_evidence}}。

深度结论： {{kidney_conclusion}}。

## 四、 疾病爆发概率预测 (Predictive Models)

基于中国人群专项模型（China-PAR）的量化评估。

- 10年 ASCVD (心血管病) 发病风险： {{ascvd_risk_10year}}

- 未来 3 年糖尿病转化风险： {{diabetes_risk_3year}}

**残余风险提示**： {{residual_risk_note}}

## 五、 阶梯式干预处方 (Clinical Prescription)

遵循"药物治疗-营养干预-运动处方"的三位一体逻辑。

### 1. 临床治疗建议 (Level A 证据)

{{clinical_treatment}}

### 2. 治疗性生活方式改变 (TLC)

{{lifestyle_intervention}}

## 专家综述

{{expert_summary}}

---

> （注：文档部分内容可能由 AI 生成）
