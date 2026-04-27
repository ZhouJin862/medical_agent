---
name: cvd-risk-assessment
description: 心血管病风险评估、心血管风险评估、CVD风险、心血管病一级预防、心脏病风险评估、中风风险评估、Chinese adult cardiovascular disease primary prevention risk assessment. Use when Claude needs to: (1) Assess cardiovascular risk level for Chinese adults (评估心血管风险等级), (2) Provide lifestyle and medical intervention recommendations (提供生活方式和药物干预建议), (3) Generate health insights and expert summaries (生成健康洞察和专家综述), (4) Handle both interactive Q&A and structured patient data input. 触发词：心血管、心脏病、中风、风险评估、危险分层、健康评估
---

# Cardiovascular Disease Risk Assessment (Chinese Adults)

Based on the "Chinese Adult Cardiovascular Disease Primary Prevention Risk Assessment Flowchart" and relevant clinical guidelines.

## Quick Start

```bash
# Interactive assessment
scripts/risk_assessment.py --interactive

# Structured input
scripts/risk_assessment.py --input patient_data.json

# Generate full report
scripts/risk_assessment.py --full-report
```

## Four Core Functions

### 1. Health Insight (健康洞察)

Analyze patient's basic health profile:

- Demographics: age, gender, region
- Vitals: blood pressure, heart rate, BMI, waist circumference
- Lab results: lipid profile, blood glucose
- Lifestyle: smoking, alcohol, exercise, diet
- Family history: premature CVD in first-degree relatives
- Medical history: diabetes, CKD, other conditions

**Input**: Patient questionnaire or structured data
**Output**: Health profile summary with flagging of abnormal values

### 2. Risk Assessment (风险评估)

Calculate cardiovascular risk category based on Chinese guidelines.

**Risk Categories**:
- **Low Risk (低危)**: No major risk factors or <5% 10-year risk
- **Medium Risk (中危)**: 1-2 risk factors or 5%-9% 10-year risk
- **High Risk (高危)**: Diabetes + 1 risk factor, or ≥10% 10-year risk
- **Very High Risk (很高危)**: Existing CVD, or diabetes with target organ damage

**Risk Factors Considered**:
| Factor | Threshold |
|--------|-----------|
| Age | Men ≥45y, Women ≥55y |
| Hypertension | SBP≥140 or DBP≥90 or on treatment |
| Dyslipidemia | LDL-C≥4.9 or TC≥7.2 or on treatment |
| Diabetes | FPG≥7.0 or HbA1c≥6.5% or on treatment |
| Smoking | Current smoker |
| Obesity | BMI≥28 or waist≥90cm(M)/≥85cm(F) |
| Family History | Premature CVD in 1st degree relatives |

### 3. Intervention Prescription (干预处方)

Provide recommendations based on risk category.

#### Lifestyle Interventions (All Risk Levels)
- **Diet**: DASH or Mediterranean diet, sodium <5g/day
- **Exercise**: 150min/week moderate intensity
- **Weight Control**: Target BMI 18.5-23.9
- **Smoking Cessation**: Complete cessation recommended
- **Alcohol Limit**: Men <25g/day, Women <15g/day

#### Medical Interventions (by Risk Level)

| Risk Level | BP Target | LDL Target | Antiplatelet | Statin |
|------------|-----------|------------|--------------|--------|
| Low | <140/90 | <3.4 | Not recommended | Consider if LDL≥4.9 |
| Medium | <140/90 | <3.4 | Consider | Consider |
| High | <130/80 | <2.6 | Consider | Recommended |
| Very High | <130/80 | <1.8 | Recommended | High-intensity |

### 4. Expert Summary (专家综述)

Generate comprehensive clinical report including:
- Risk assessment summary with confidence level
- Priority-ranked intervention list
- Short-term and long-term goals
- Follow-up monitoring schedule
- Patient education points
- Red flags requiring immediate attention

## Input Modes

### Mode A: Interactive Q&A

When user provides partial information or asks general questions, Claude should:

1. Identify missing critical data points
2. Ask targeted questions one at a time
3. Calculate risk as information becomes available
4. Provide interim insights and final recommendations

Example:
```
User: "评估这个50岁男性的心血管风险"
Claude: "需要了解以下信息：
1. 血压是多少？
2. 是否有糖尿病？
3. 血脂检查结果？
..."
```

### Mode B: Structured Input

When user provides complete patient data (JSON, structured text), process directly:

```json
{
  "patient": {
    "age": 50,
    "gender": "male",
    "sbp": 145,
    "dbp": 92,
    "ldl_c": 3.8,
    "has_diabetes": false,
    "smoker": true,
    "bmi": 27
  }
}
```

## Reference Materials

- **Risk criteria details**: See [references/risk_criteria.md](references/risk_criteria.md)
- **Intervention guidelines**: See [references/interventions.md](references/interventions.md)
- **Risk calculation script**: See [scripts/risk_calculator.py](scripts/risk_calculator.py)

## Workflow

1. **Data Collection** - Gather patient information via chosen mode
2. **Health Insight** - Analyze and flag abnormal values
3. **Risk Assessment** - Calculate risk category using risk calculator
4. **Intervention Prescription** - Generate personalized recommendations
5. **Expert Summary** - Compile comprehensive report

## Notes

- These guidelines apply to Chinese adults aged 40-79
- For patients with existing CVD, refer to secondary prevention guidelines
- Risk assessment should be repeated annually or when major risk factors change
- Clinical judgment should always supplement algorithm-based recommendations
