---
name: chronic-disease-risk-assessment
description: 为健康险企业提供四高一重（高血压、高血糖、高血脂、高尿酸、超重）全病程健康风险评估服务；当用户需要进行慢病风险评估、体检报告分析、心血管风险预测、糖尿病风险预测或健康管理建议时使用；严格遵循循证医学原则，基于国标/行标/临床最佳实践标准进行评估
dependency:
  python:
    - pyyaml==6.0.1
    - requests==2.31.0
---

# 慢性疾病预防风险评估

## 任务目标
- 本 Skill 用于：为健康险企业提供全病程健康风险评估服务
- 核心能力：
  - 胰岛素抵抗与内皮损伤双路径评估
  - China-PAR 心血管风险预测（10年ASCVD）
  - 糖尿病转化风险预测（3年）
  - 靶器官损害循证评估
  - 阶梯式干预处方生成
- 触发条件：用户需要评估慢病风险、分析体检报告、制定健康管理计划或进行健康风险筛查

## 核心原则

### 数据采集原则

**必须严格遵守以下原则**：

1. **真实性原则**：所有健康指标数据必须基于用户输入或API获取的真实数据值
2. **完整性原则**：数据为空值时，引导用户补充，绝不允许主观臆断或虚构数据
3. **可追溯原则**：所有数据来源必须可追溯（用户输入/API来源/文件上传）
4. **规范性原则**：数据采集严格遵循 [数据采集清单](references/data_collection_checklist.md)

**禁止行为**：
- ❌ 禁止主观臆断或推测健康指标数值
- ❌ 禁止使用默认值填充缺失的必采指标
- ❌ 禁止在无数据依据的情况下进行评估

### 健康评估原则

**必须严格遵循循证医学**：

1. **证据导向**：所有评估结论必须基于医学证据，引用国标/行标/临床医学最佳实践标准
2. **标准遵循**：评估标准遵循：
   - 国家标准：如《中国高血压防治指南》
   - 行业标准：如《中国成人血脂异常防治指南》
   - 临床最佳实践：如China-PAR模型、HOMA-IR指数等
3. **客观严谨**：评估结论基于客观数据和循证医学证据，不带主观判断
4. **溯源明确**：所有医学结论需注明参考标准和证据来源

**评估输出要求**：
- ✅ 健康指征：基于实际检测数据
- ✅ 医学证据：引用权威医学标准
- ✅ 评估结论：循证医学推导
- ✅ 参考标准：明确标注国标/行标/临床指南

---

## 前置准备

### 依赖说明
Scripts脚本所需的依赖包及版本：
```
pyyaml==6.0.1
requests==2.31.0
```

### ⚠️ 数据采集规范

**重要**：健康数据采集必须严格遵循 [数据采集清单](references/data_collection_checklist.md) 中定义的指标规范。

#### 最小评估数据集（必采指标）

进行健康风险评估的最低要求为 **12项必采指标**：

| 分类 | 必采指标 |
|------|---------|
| 基础体格（5项） | 身高、体重、腰围、收缩压、舒张压 |
| 糖代谢（2项） | 空腹血糖、糖化血红蛋白（HbA1c） |
| 脂代谢（4项） | TC、TG、LDL-C、HDL-C |
| 尿酸（1项） | 血尿酸 |

**提示**：
- 缺少必采指标将无法进行评估
- 建议采集标准数据集（含eGFR、UACR、吸烟史）以获得更准确的评估
- 详细指标清单请参考 [data_collection_checklist.md](references/data_collection_checklist.md)

### 输入方式

#### 方式一：第三方API输入（推荐）
健康档案数据中台API自动获取数据

**执行方式**：
```bash
python /workspace/projects/chronic-disease-risk-assessment/scripts/api_client.py --endpoint <API地址> --patient-id <患者ID>
```

**支持的API类型**：
- 健康管理平台API
- 体检机构API
- 医院信息系统API

**API集成指南**：参考 [references/api_integration_guide.md](references/api_integration_guide.md)

**凭证配置**：首次使用第三方API时，系统会引导配置API凭证

#### 方式二：手动录入
用户直接告知各项健康指标，智能体协助整理为标准格式

**表单格式**：参考 [references/template_format_spec.md](references/template_format_spec.md)

#### 方式二：图片识别（智能体执行）
上传体检报告图片，智能体使用图像识别能力直接读取并提取健康数据

**执行方式**：
- 用户上传体检报告图片
- 智能体识别图片内容，提取健康指标
- 智能体整理为标准格式数据

**注意**：智能体本身具备图像识别能力，可直接读取图片内容

#### 方式三：JSON文件输入
创建健康数据文件（如 `health_data.json`），格式参考 [references/template_format_spec.md](references/template_format_spec.md)

### 数据完整度校验
系统自动验证必填字段：
- 必填：血压、空腹血糖、血脂（TC/TG/LDL-C/HDL-C）、尿酸、BMI
- 可选：HbA1c、腰围、超声检查、颈动脉彩超、UACR、eGFR等

### 报告模板选择

系统支持4种报告模板：

| 模板名称 | 适用场景 | 特点 |
|---------|---------|------|
| default（标准版） | 综合评估 | 完整循证医学评估，靶器官损害评估，风险预测 |
| insurance（保险版） | 健康险企业 | 风险分级突出，医疗支出风险预测，干预窗口期分析 |
| clinical（临床版） | 医生临床决策 | 专业术语，详细数据，循证医学证据 |
| personal（个人版） | 普通用户 | 通俗语言，图表化呈现，可操作性建议 |

**使用方式**：
```bash
python /workspace/projects/chronic-disease-risk-assessment/scripts/template_manager.py --template insurance
```

## 操作步骤

### 标准流程

### 步骤1：数据获取与验证
```bash
python scripts/health_data_validator.py --input <健康数据文件> --mode skill
```

**其他输入方式**：
- **API模式**：`python scripts/api_client.py --endpoint <API地址> --patient-id <患者ID>`
- **图片识别模式**：用户上传体检报告图片，智能体识别并整理数据

**输出**：验证通过的标准化数据，保存为 `validated_data.json`

### 步骤2：风险评估计算

```bash
python scripts/risk_calculator.py --input validated_data.json --json-output
```

**计算内容**：
- 四高一重风险分层（血压、血糖、血脂、尿酸、BMI）
- China-PAR 10年ASCVD风险预测
- 3年糖尿病转化风险预测
- 胰岛素抵抗评估（HOMA-IR）
- 靶器官损害评估
- 综合风险评分

**输出**：风险评估结果，保存为 `risk_assessment.json`

**China-PAR模型说明**：参考 [references/china_par_model.md](references/china_par_model.md)

### 步骤3：报告生成
```bash
python scripts/template_manager.py --template default --render --format modules
```

**报告内容**：
- 读取 `risk_assessment.json` 中的风险评估结果
- 生成报告编号（格式：EBM-YYYY-MMDD-XXX）
- 基于所选模板结构填充内容：
  - 健康综合画像：计算综合健康评分、风险预警级别、临床代谢标签
  - 四高一重循证证据链：形态与代谢基础评估、三高关键指标对照表
  - 靶器官损害评估：血管内皮与斑块评估、微血管与肾功能评估（如有数据）
  - 疾病爆发概率预测：10年ASCVD风险、3年糖尿病转化风险
  - 阶梯式干预处方：临床治疗建议、治疗性生活方式改变
  - 专家综述：综合评估总结与风险提示
- 自动附加免责声明

### 可选分支

**分支A：数据不完整**
- 系统自动识别缺失字段
- 智能体询问用户补充相应指标
- 支持部分评估：用户可选择仅评估已有指标

**分支B：批量评估**
- 支持批量导入患者数据
- 循环执行评估流程
- 生成批量评估汇总报告

**分支C：自定义模板**
- 用户提供自定义模板路径
- 智能体根据模板变量调整报告内容结构

## 资源索引

### 必要脚本
- [scripts/health_data_validator.py](scripts/health_data_validator.py)：健康数据验证与标准化
- [scripts/risk_calculator.py](scripts/risk_calculator.py)：风险评估计算引擎（含China-PAR模型）
- [scripts/template_manager.py](scripts/template_manager.py)：报告模板管理器
- [scripts/api_client.py](scripts/api_client.py)：第三方健康平台API客户端
- [scripts/china_par_calculator.py](scripts/china_par_calculator.py)：China-PAR风险预测计算

### 领域参考
- [references/data_collection_checklist.md](references/data_collection_checklist.md)：**数据采集清单**（必读，严格遵循指标规范）
- [references/assessment_standards.md](references/assessment_standards.md)：四高一重评估标准
- [references/template_format_spec.md](references/template_format_spec.md)：输入数据与模板格式规范
- [references/risk_factors_guide.md](references/risk_factors_guide.md)：风险因素与干预指南
- [references/api_integration_guide.md](references/api_integration_guide.md)：API集成指南
- [references/china_par_model.md](references/china_par_model.md)：China-PAR模型说明

### 输出资产
- [assets/default_template.md](assets/default_template.md)：标准版报告模板（HE-Report格式）
- [assets/insurance_template.md](assets/insurance_template.md)：保险版报告模板
- [assets/clinical_template.md](assets/clinical_template.md)：临床版报告模板
- [assets/personal_template.md](assets/personal_template.md)：个人版报告模板

## 注意事项

### 数据准确性
- 确保健康指标数据来源可靠（体检报告、医疗记录等）
- 注意单位统一（血压mmHg、血糖mmol/L、尿酸μmol/L等）
- 如有异常值，脚本会标记提醒，请核实后重新评估

### 评估局限性
- 本评估基于通用医学标准，仅供参考
- 不能替代专业医生的诊断和建议
- 特殊人群（孕妇、老年人、慢性病患者）需结合临床实际

### API凭证配置
- 第三方健康平台API需配置相应的API Key
- 首次使用时，系统会引导完成凭证配置

### 隐私保护
- 评估报告包含个人健康信息，注意保密
- 建议定期清理临时文件（validated_data.json、risk_assessment.json）
- API传输需确保HTTPS加密

## 使用示例

### 示例1：API输入模式
```bash
# 从健康平台API获取数据并评估
python /workspace/projects/chronic-disease-risk-assessment/scripts/api_client.py --endpoint https://health-api.example.com/v1 --patient-id P123456

# 计算风险
python /workspace/projects/chronic-disease-risk-assessment/scripts/risk_calculator.py --input validated_data.json

# 加载保险版模板
python /workspace/projects/chronic-disease-risk-assessment/scripts/template_manager.py --template insurance

# 智能体生成报告
```

### 示例2：图片识别模式
用户上传体检报告图片，智能体识别并提取健康数据，自动整理为标准格式后执行评估流程。

### 示例3：手动录入
用户直接告知健康指标：
- "我45岁，男性，血压148/96mmHg，空腹血糖6.9mmol/L..."

智能体自动整理数据并执行评估流程。

### 示例4：指定模板
```bash
# 使用临床版模板
python /workspace/projects/chronic-disease-risk-assessment/scripts/template_manager.py --template clinical

# 使用个人版模板
python /workspace/projects/chronic-disease-risk-assessment/scripts/template_manager.py --template personal
```
