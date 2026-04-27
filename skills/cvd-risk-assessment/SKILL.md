---
name: cvd-risk-assessment
description: 心血管病风险评估、心血管风险评估、CVD风险、心血管病一级预防、心脏病风险评估、中风风险评估。适用于中国成人心血管病一级预防风险评估 - 评估心血管风险等级，识别危险因素。触发词：心血管、心脏病、中风、风险评估、危险分层、健康评估
tags: [心血管, 心脏病, 中风, 风险评估, 危险分层, CVD, cardiovascular, heart disease, stroke]
---

# 中国成人心血管病风险评估

基于《中国成人心血管病一级预防风险评估流程图》及相关临床指南。

## 三层评估流程

### 第一步：心血管病风险判定（初始高危人群）

符合以下任一条件即判定为高危/很高危：
- **年龄≥40岁的糖尿病患者**
- **LDL-C ≥4.9 mmol/L** 或 **TC ≥7.2 mmol/L**
- **CKD 3/4期**（eGFR <60 mL/min/1.73m²）
- **严重高血压**（SBP ≥180 mmHg 或 DBP ≥110 mmHg）

当有≥3个上述危险因素或包含严重高血压时，判定为**很高危**。

### 第二步：10年风险并行评估

如果第一步未判定为高危，则**并行执行**以下两种10年风险评估：

#### 评估A：10年ASCVD风险评估（查表法）

**查表因素**：
1. **血清胆固醇水平分层**（优先使用LDL-C，其次TC）
   - 1级：LDL-C 1.8-2.6 或 TC 3.1-4.1 mmol/L
   - 2级：LDL-C 2.6-3.4 或 TC 4.1-5.2 mmol/L
   - 3级：LDL-C 3.4-4.9 或 TC 5.2-7.2 mmol/L

2. **危险因素数量**（不包括高血压）
   - 吸烟
   - 低HDL-C（<1.0 mmol/L）
   - 年龄（男≥45岁，女≥55岁）

3. **血压状态**
   - 无高血压（SBP<140 且 DBP<90）
   - 有高血压（SBP≥140 或 DBP≥90）

**查表规则**：

| 危险因素数 | 1级 (TC 3.1-4.1 或 LDL-C 1.8-2.6) | 2级 (TC 4.1-5.2 或 LDL-C 2.6-3.4) | 3级 (TC 5.2-7.2 或 LDL-C 3.4-4.9) |
|:----------:|:-----------------------------------:|:-----------------------------------:|:-----------------------------------:|
| 0个 | 低危 (<5%) | 低危 (<5%) | 低危 (<5%) |
| 1个 | 低危 (<5%) | 低危 (<5%) | 中危 (5%-9%) |
| 2个 | 中危 (5%-9%) | 中危 (5%-9%) | 中危 (5%-9%) |
| 3个 | 中危 (5%-9%) | 中危 (5%-9%) | 高危 (≥10%) |

#### 表2：有高血压人群

| 危险因素数 | 1级 (TC 3.1-4.1 或 LDL-C 1.8-2.6) | 2级 (TC 4.1-5.2 或 LDL-C 2.6-3.4) | 3级 (TC 5.2-7.2 或 LDL-C 3.4-4.9) |
|:----------:|:-----------------------------------:|:-----------------------------------:|:-----------------------------------:|
| 0个 | 低危 (<5%) | 中危 (5%-9%) | 中危 (5%-9%) |
| 1个 | 中危 (5%-9%) | 中危 (5%-9%) | 中危 (5%-9%) |
| 2个 | 中危 (5%-9%) | 中危 (5%-9%) | 高危 (≥10%) |
| 3个 | 高危 (≥10%) | 高危 (≥10%) | 高危 (≥10%) |

**风险分层**：
- **低危**：10年风险 <5%
- **中危**：10年风险 5%-9%
- **高危**：10年风险 ≥10%

#### 评估B：10年心血管病发病风险评估（基于血压分级）

**血压分级标准**：
| 分级 | 收缩压 (SBP) | 舒张压 (DBP) |
|:----:|:-------------:|:-------------:|
| 正常高值 | 130-139 mmHg | 85-89 mmHg |
| 高血压1级 | 140-159 mmHg | 90-99 mmHg |
| 高血压2级及以上 | ≥160 mmHg | ≥100 mmHg |

**高危判定标准**（满足以下任一条件即为高危）：
1. **正常高值血压** + **3个危险因素**（包括高血压、吸烟、低HDL-C、年龄≥45/55岁等）
2. **高血压1级** + **2个危险因素**
3. **高血压2级及以上** + **1个危险因素**

**非高危情况**：参考评估A的10年ASCVD查表结果（低危/中危/高危）

### 第三步：余生风险高危判定

**触发条件**：10年风险为中危 **且** 年龄<55岁

**余生高危判定标准**（需具备以下**任意2项及以上**）：
- **收缩压 ≥160 mmHg** 或 **舒张压 ≥100 mmHg**
- **非HDL-C ≥5.2 mmol/L**
- **HDL-C <1.0 mmol/L**
- **BMI ≥28 kg/m²**
- **吸烟**

## 风险等级分类

| 等级 | 定义 | 随访间隔 |
|------|------|----------|
| 低危 | 无主要危险因素或10年风险<5% | 每年 |
| 中危 | 1-2个危险因素或10年风险5%-9% | 每6个月 |
| 高危 | 3个危险因素或10年风险≥10% | 每3-6个月 |
| 很高危 | 多个严重危险因素或余生风险高危 | 每1-3个月 |

## 快速开始

```bash
# 交互式评估
scripts/risk_assessment.py --interactive

# 结构化输入
scripts/risk_assessment.py --input patient_data.json
```

## 输入模式

### 模式A：交互式问答

当用户提供部分信息时：
1. 识别缺失的关键数据点
2. 询问必需信息（年龄、性别）
3. 信息可用时计算风险等级

### 模式B：结构化输入

```json
{
  "age": 50,
  "gender": "male",
  "sbp": 145,
  "dbp": 92,
  "ldl_c": 3.8,
  "has_diabetes": false,
  "smoker": true,
  "bmi": 27,
  "hdl_c": 0.9
}
```

## 操作步骤

### 步骤1：心血管风险评估

```bash
python scripts/risk_assessment.py --input <健康数据文件> --mode skill
```

**输入数据要求**：
- **必需**：年龄（age）、性别（gender）
- **可选**：血压（sbp/dbp）、血脂（ldl_c, tc, hdl_c, tg）、糖尿病状态（has_diabetes）、吸烟状态（smoker）、BMI、CKD分期等

**输入格式示例**：

```json
{
  "age": 50,
  "gender": "male",
  "sbp": 145,
  "dbp": 92,
  "ldl_c": 3.8,
  "has_diabetes": false,
  "smoker": true,
  "bmi": 27,
  "hdl_c": 0.9
}
```

**输出格式**：

```json
{
  "success": true,
  "status": "completed",
  "skill_name": "cvd-risk-assessment",
  "final_output": {
    "modules": {
      "risk_assessment": {
        "risk_level": "high",
        "risk_level_zh": "高危",
        "risk_factors_count": 3,
        "key_factors": ["高血压", "年龄≥45岁", "吸烟"],
        "follow_up": "3-6个月",
        "ten_year_risk_range": "≥10%",
        "ten_year_cvd_risk_zh": "高危"
      }
    }
  },
  "risk_assessment": {
    "risk_category": "high",
    "risk_category_zh": "高危",
    "risk_factors_count": 3,
    "key_factors": ["高血压", "年龄≥45岁", "吸烟"],
    "follow_up_interval": "3-6个月",
    "assessment_path": "ten_year_risk",
    "ten_year_risk": "high",
    "ten_year_risk_range": "≥10%",
    "ten_year_cvd_risk": "high",
    "ten_year_cvd_risk_zh": "高危",
    "lifetime_risk": null
  }
}
```

**输出字段说明**：
- `risk_level_zh`: 心血管病发病风险（当前综合风险等级）
- `ten_year_risk_range`: 10年ASCVD风险评估范围（<5%/5%-9%/≥10%）
- `ten_year_cvd_risk_zh`: 10年心血管病发病风险等级（基于血压分级+危险因素）
- `lifetime_risk`: 余生风险（如有）

**评估路径说明**：
- `initial_high`: 初始高危人群判定
- `ten_year_risk`: 10年ASCVD风险评估
- `lifetime_high`: 余生风险高危判定

**数据不完整处理**：
当必需数据（年龄、性别）缺失时，脚本返回 `incomplete` 状态：

```json
{
  "success": false,
  "status": "incomplete",
  "message": "Missing required patient data",
  "required_fields": ["age", "gender"],
  "provided_data": {...}
}
```

## 参考资料链接

- **风险判定标准详解**：[references/risk_criteria.md](references/risk_criteria.md)
- **风险计算脚本**：[scripts/risk_calculator.py](scripts/risk_calculator.py)

## 使用说明

- 本指南适用于40-79岁中国成人
- 风险评估应每年重复一次，或当主要危险因素变化时重新评估
- 临床判断应始终补充基于算法的建议
