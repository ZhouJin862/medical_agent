# 输入数据与模板格式规范

## 目录
1. [数据采集标准](#数据采集标准)
2. [健康数据输入格式](#健康数据输入格式)
3. [报告模板格式规范](#报告模板格式规范)
4. [数据验证规则](#数据验证规则)
5. [示例与模板](#示例与模板)

---

## 数据采集标准

**重要提示**：健康数据采集必须严格遵循 [data_collection_checklist.md](data_collection_checklist.md) 中定义的指标清单。

### 最小评估数据集（必采指标）

进行基本健康风险评估的最低要求：

| 分类 | 指标 | 字段名 | 数量 |
|------|------|--------|------|
| 基础体格 | 身高、体重、腰围、收缩压、舒张压 | height, weight, waist_circumference, systolic, diastolic | 5项 |
| 糖代谢 | 空腹血糖、糖化血红蛋白 | fasting_glucose, hba1c | 2项 |
| 脂代谢 | TC、TG、LDL-C、HDL-C | tc, tg, ldl_c, hdl_c | 4项 |
| 尿酸 | 血尿酸 | uric_acid | 1项 |
| **合计** | | | **12项** |

### 标准评估数据集

在最小评估数据集基础上，增加：

| 分类 | 指标 | 字段名 | 说明 |
|------|------|--------|------|
| 肾功能 | eGFR、UACR | egfr, uacr | 预警早期肾脏微血管损伤 |
| 生活方式 | 吸烟史 | smoking | China-PAR模型核心因子 |

---

## 健康数据输入格式

### JSON数据结构

健康数据应以JSON格式提供，严格按照以下结构：

```json
{
  "patient_info": {
    "name": "患者姓名",
    "age": 年龄,
    "gender": "性别(male/female)"
  },
  "health_metrics": {
    // 1. 基础体格指标
    "basic": {
      "height": 身高,
      "weight": 体重,
      "waist_circumference": 腰围,
      "body_fat_rate": 体脂率,
      "visceral_fat_level": 内脏脂肪等级
    },
    // 2. 血压
    "blood_pressure": {
      "systolic": 收缩压,
      "diastolic": 舒张压,
      "heart_rate": 心率
    },
    // 3. 糖代谢
    "blood_glucose": {
      "fasting_glucose": 空腹血糖,
      "hba1c": 糖化血红蛋白,
      "ogtt_2h": OGTT 2小时血糖
    },
    // 4. 脂代谢
    "blood_lipid": {
      "tc": 总胆固醇,
      "tg": 甘油三酯,
      "ldl_c": 低密度脂蛋白,
      "hdl_c": 高密度脂蛋白,
      "non_hdl_c": 非高密度脂蛋白,
      "lp_a": 脂蛋白a
    },
    // 5. 尿酸与肾功能
    "kidney": {
      "uric_acid": 尿酸,
      "serum_creatinine": 血清肌酐,
      "bun": 尿素氮,
      "egfr": 肾小球滤过率,
      "uacr": 尿微量白蛋白肌酐比值
    },
    // 6. 其他代谢指标
    "other_metabolism": {
      "homocysteine": 同型半胱氨酸,
      "alt": 谷丙转氨酶,
      "ast": 谷草转氨酶
    }
  },
  "clinical_examination": {
    // 临床影像与专科检查
    "carotid_ultrasound": {
      "imt": 颈动脉内中膜厚度,
      "plaque": "斑块描述"
    },
    "abdominal_ultrasound": {
      "fatty_liver": "脂肪肝程度(轻/中/重)"
    },
    "ecg": "心电图描述",
    "echocardiography": "超声心动图描述",
    "fundus_photography": "眼底检查描述"
  },
  "lifestyle": {
    // 生活方式与依从性
    "smoking": {
      "history": 是否吸烟,
      "amount": 每日吸烟量,
      "quit_years": 戒烟时长
    },
    "alcohol": {
      "history": 是否饮酒,
      "frequency": 饮酒频率
    },
    "exercise": {
      "weekly_minutes": 每周运动时长,
      "frequency": 运动频率,
      "type": "运动类型"
    },
    "diet": {
      "salt_intake": "盐摄入水平(高/中/低)",
      "sugary_drink_frequency": 含糖饮料频率,
      "dietary_fiber": "膳食纤维摄入评价"
    },
    "sleep": {
      "duration": 睡眠时长,
      "snoring": 是否打鼾,
      "quality": "睡眠质量"
    },
    "medication": {
      "antihypertensive": ["降压药物列表"],
      "lipid_lowering": ["降脂药物列表"],
      "glucose_lowering": ["降糖药物列表"],
      "mpr": 服药覆盖率
    }
  },
  "template": "模板名称(可选)"
}
```

### 字段详细说明

#### patient_info（患者基本信息）

| 字段 | 类型 | 必填 | 单位 | 说明 | 示例 |
|------|------|------|------|------|------|
| name | string | 是 | - | 患者姓名 | "张三" |
| age | number | 是 | 岁 | 年龄 | 45 |
| gender | string | 是 | - | 性别（male/female/男/女） | "male" |

#### health_metrics.basic（基础体格）

| 字段 | 类型 | 必填 | 单位 | 正常范围 | 说明 |
|------|------|------|------|---------|------|
| height | number | 是 | cm | 100-250 | 身高 |
| weight | number | 是 | kg | 20-300 | 体重 |
| waist_circumference | number | 是 | cm | 50-200 | 腰围（评估中心型肥胖） |
| body_fat_rate | number | 否 | % | 10-40 | 体脂率 |
| visceral_fat_level | number | 否 | 等级 | 1-30 | 内脏脂肪等级 |

#### health_metrics.blood_pressure（血压）

| 字段 | 类型 | 必填 | 单位 | 正常范围 | 说明 |
|------|------|------|------|---------|------|
| systolic | number | 是 | mmHg | 60-250 | 收缩压 |
| diastolic | number | 是 | mmHg | 40-150 | 舒张压 |
| heart_rate | number | 否 | bpm | 40-180 | 心率 |

#### health_metrics.blood_glucose（糖代谢）

| 字段 | 类型 | 必填 | 单位 | 正常范围 | 说明 |
|------|------|------|------|---------|------|
| fasting_glucose | number | 是 | mmol/L | 2.0-30.0 | 空腹血糖（必采） |
| hba1c | number | 是 | % | 4.0-15.0 | 糖化血红蛋白（必采，反映近3个月血糖） |
| ogtt_2h | number | 否 | mmol/L | 2.0-30.0 | OGTT 2小时血糖 |

#### health_metrics.blood_lipid（脂代谢）

| 字段 | 类型 | 必填 | 单位 | 正常范围 | 说明 |
|------|------|------|------|---------|------|
| tc | number | 是 | mmol/L | 1.0-15.0 | 总胆固醇 |
| tg | number | 是 | mmol/L | 0.1-10.0 | 甘油三酯 |
| ldl_c | number | 是 | mmol/L | 0.5-10.0 | 低密度脂蛋白胆固醇（最关键指标） |
| hdl_c | number | 是 | mmol/L | 0.3-5.0 | 高密度脂蛋白胆固醇 |
| non_hdl_c | number | 否 | mmol/L | 1.0-12.0 | 非高密度脂蛋白（残余风险评估） |
| lp_a | number | 否 | mg/L | 0-300 | 脂蛋白a（残余风险评估） |

#### health_metrics.kidney（尿酸与肾功能）

| 字段 | 类型 | 必填 | 单位 | 正常范围 | 说明 |
|------|------|------|------|---------|------|
| uric_acid | number | 是 | μmol/L | 100-1000 | 血尿酸（必采） |
| serum_creatinine | number | 否 | μmol/L | 20-2000 | 血清肌酐 |
| bun | number | 否 | mmol/L | 1.0-50.0 | 尿素氮 |
| egfr | number | 否 | mL/(min·1.73m²) | 10-200 | 估算肾小球滤过率 |
| uacr | number | 否 | mg/g | 0-1000 | 尿微量白蛋白/肌酐比值（必采项，预警肾脏微血管损伤） |

#### health_metrics.other_metabolism（其他代谢指标）

| 字段 | 类型 | 必填 | 单位 | 正常范围 | 说明 |
|------|------|------|------|---------|------|
| homocysteine | number | 否 | μmol/L | 0-100 | 同型半胱氨酸（H型高血压评估） |
| alt | number | 否 | U/L | 0-500 | 谷丙转氨酶（脂肪肝评估） |
| ast | number | 否 | U/L | 0-500 | 谷草转氨酶（脂肪肝评估） |

#### clinical_examination（临床影像与专科检查）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| carotid_ultrasound.imt | number | 否 | 颈动脉内中膜厚度(mm) |
| carotid_ultrasound.plaque | string | 否 | 斑块描述 |
| abdominal_ultrasound.fatty_liver | string | 否 | 脂肪肝程度（轻/中/重） |
| ecg | string | 否 | 心电图描述 |
| echocardiography | string | 否 | 超声心动图描述 |
| fundus_photography | string | 否 | 眼底检查描述 |

#### lifestyle（生活方式与依从性）

| 字段路径 | 类型 | 必填 | 说明 |
|---------|------|------|------|
| smoking.history | boolean | 否 | 是否吸烟（China-PAR模型核心因子） |
| smoking.amount | number | 否 | 每日吸烟量（支） |
| smoking.quit_years | number | 否 | 戒烟时长（年） |
| alcohol.history | boolean | 否 | 是否饮酒 |
| alcohol.frequency | number | 否 | 饮酒频率（次/周） |
| exercise.weekly_minutes | number | 否 | 每周运动时长（分钟） |
| exercise.frequency | number | 否 | 运动频率（次/周） |
| exercise.type | string | 否 | 运动类型 |
| diet.salt_intake | string | 否 | 盐摄入水平（高/中/低） |
| diet.sugary_drink_frequency | number | 否 | 含糖饮料频率（次/周） |
| diet.dietary_fiber | string | 否 | 膳食纤维摄入评价 |
| sleep.duration | number | 否 | 睡眠时长（小时） |
| sleep.snoring | boolean | 否 | 是否打鼾（OSAHS风险） |
| sleep.quality | string | 否 | 睡眠质量 |
| medication.antihypertensive | array | 否 | 降压药物列表 |
| medication.lipid_lowering | array | 否 | 降脂药物列表 |
| medication.glucose_lowering | array | 否 | 降糖药物列表 |
| medication.mpr | number | 否 | 服药覆盖率（%） |

---

## 报告模板格式规范

### 模板文件结构

报告模板使用Markdown格式，支持YAML Front Matter定义元数据：

```markdown
---
template_name: 模板名称
template_version: 版本号
sections:
  - 章节1
  - 章节2
variables:
  - 变量1
  - 变量2
---

# 报告标题

## 章节1
内容...

## 章节2
内容...
```

### HE-Report模板专用变量

#### 健康综合画像部分

| 变量名 | 类型 | 来源 | 说明 |
|--------|------|------|------|
| report_number | string | 系统生成 | 报告编号 |
| assessment_date | string | 系统生成 | 评估日期 |
| core_logic | string | 智能体生成 | 核心评估逻辑说明 |
| health_score | string | 智能体生成 | 综合健康评分 |
| risk_level | string | 智能体生成 | 风险预警级别 |
| metabolic_label | string | 智能体生成 | 临床代谢标签 |
| medical_comment | string | 智能体生成 | 严肃医疗简评 |

#### 形态与代谢基础部分

| 变量名 | 类型 | 来源 | 说明 |
|--------|------|------|------|
| bmi_value | number | 计算得出 | BMI值 |
| waist_circumference | number | 用户输入 | 腰围（cm） |
| ultrasound_evidence | string | 智能体生成 | 超声检查证据 |
| obesity_assessment | string | 智能体生成 | 肥胖评估结论 |

#### 三高关键指标部分

| 变量名 | 类型 | 来源 | 说明 |
|--------|------|------|------|
| bp_value | string | health_metrics.blood_pressure | 血压测量值 |
| bp_interpretation | string | 智能体生成 | 血压循证医学解读 |
| bp_target | string | 智能体生成 | 血压控制靶标 |
| glucose_value | string | health_metrics.blood_glucose | 血糖测量值（含HbA1c） |
| glucose_interpretation | string | 智能体生成 | 血糖循证医学解读 |
| glucose_target | string | 智能体生成 | 血糖控制靶标 |
| lipid_value | string | health_metrics.blood_lipid | 血脂测量值（LDL-C） |
| lipid_interpretation | string | 智能体生成 | 血脂循证医学解读 |
| lipid_target | string | 智能体生成 | 血脂控制靶标 |
| uric_acid_value | number | health_metrics.kidney.uric_acid | 尿酸测量值 |
| uric_acid_interpretation | string | 智能体生成 | 尿酸循证医学解读 |
| uric_acid_target | string | 智能体生成 | 尿酸控制靶标 |

---

## 数据验证规则

### 必填字段验证

系统将自动验证以下必填字段：

**最小评估数据集（12项）**：
1. patient_info.name
2. patient_info.age
3. patient_info.gender
4. health_metrics.basic.height
5. health_metrics.basic.weight
6. health_metrics.basic.waist_circumference
7. health_metrics.blood_pressure.systolic
8. health_metrics.blood_pressure.diastolic
9. health_metrics.blood_glucose.fasting_glucose
10. health_metrics.blood_glucose.hba1c
11. health_metrics.blood_lipid.tc
12. health_metrics.blood_lipid.tg
13. health_metrics.blood_lipid.ldl_c
14. health_metrics.blood_lipid.hdl_c
15. health_metrics.kidney.uric_acid

### 数据完整性校验

- **最小数据集校验**：必须满足12项必采指标，否则无法进行评估
- **标准数据集提示**：缺少推荐采集指标时给出提示
- **完整数据集评估**：建议采集完整数据集以获得更准确的评估

---

## 示例与模板

### 完整输入数据示例

```json
{
  "patient_info": {
    "name": "张三",
    "age": 45,
    "gender": "male"
  },
  "health_metrics": {
    "basic": {
      "height": 170,
      "weight": 82.3,
      "waist_circumference": 98,
      "body_fat_rate": 28.5
    },
    "blood_pressure": {
      "systolic": 148,
      "diastolic": 96,
      "heart_rate": 78
    },
    "blood_glucose": {
      "fasting_glucose": 6.9,
      "hba1c": 6.3,
      "ogtt_2h": null
    },
    "blood_lipid": {
      "tc": 5.8,
      "tg": 2.1,
      "ldl_c": 4.1,
      "hdl_c": 1.0,
      "non_hdl_c": 4.8,
      "lp_a": 35
    },
    "kidney": {
      "uric_acid": 495,
      "serum_creatinine": 95,
      "bun": 6.5,
      "egfr": 88,
      "uacr": 45
    },
    "other_metabolism": {
      "homocysteine": 18,
      "alt": 45,
      "ast": 38
    }
  },
  "clinical_examination": {
    "carotid_ultrasound": {
      "imt": 1.2,
      "plaque": "右侧分叉处见1.8mm混合回声斑块"
    },
    "abdominal_ultrasound": {
      "fatty_liver": "中度"
    },
    "ecg": "窦性心律，左室高电压",
    "fundus_photography": "视网膜动脉轻度硬化"
  },
  "lifestyle": {
    "smoking": {
      "history": true,
      "amount": 20,
      "quit_years": null
    },
    "alcohol": {
      "history": true,
      "frequency": 3
    },
    "exercise": {
      "weekly_minutes": 60,
      "frequency": 2,
      "type": "快走"
    },
    "diet": {
      "salt_intake": "高",
      "sugary_drink_frequency": 5,
      "dietary_fiber": "不足"
    },
    "sleep": {
      "duration": 6,
      "snoring": true,
      "quality": "一般"
    },
    "medication": {
      "antihypertensive": [],
      "lipid_lowering": [],
      "glucose_lowering": [],
      "mpr": 0
    }
  },
  "template": "default"
}
```

---

## 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0 | 2024-01 | 初始版本 |
| 2.0 | 2024-01 | 基于"四高一重"数据采集清单更新，增加完整指标定义 |
