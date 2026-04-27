# 第三方健康平台API集成指南

## 目录
1. [概述](#概述)
2. [支持的API类型](#支持的api类型)
3. [凭证配置](#凭证配置)
4. [数据映射规范](#数据映射规范)
5. [错误处理](#错误处理)

---

## 概述

本Skill支持从第三方健康平台、体检系统、医院信息系统获取健康数据，实现自动化的健康风险评估。

### 集成优势
- 自动获取数据，减少手动录入
- 数据来源可靠，提高评估准确性
- 支持批量评估，提高效率

---

## 支持的API类型

### 1. 健康管理平台API

**典型场景**：企业健康管理平台、互联网医院

**API特点**：
- RESTful接口
- OAuth2.0或API Key认证
- 返回标准化健康数据

**接入流程**：
1. 获取API文档和凭证
2. 配置凭证（见下文）
3. 调用 `scripts/api_client.py`

### 2. 体检机构API

**典型场景**：体检中心、第三方体检机构

**API特点**：
- 通常提供体检报告数据
- 数据格式可能需要映射
- 支持批量查询

### 3. 医院信息系统API

**典型场景**：医院HIS系统、电子病历系统

**API特点**：
- 通常需要医院授权
- 数据安全性要求高
- 可能涉及HL7等标准

---

## 凭证配置

### 配置方式

首次使用第三方API时，需要配置API凭证。系统提供两种配置方式：

#### 方式一：环境变量（推荐）

```bash
# 健康平台API密钥
export HEALTH_API_KEY="your-api-key-here"

# OCR服务API密钥
export OCR_API_KEY="your-ocr-api-key"
```

#### 方式二：命令行参数

```bash
python scripts/api_client.py \
  --endpoint https://health-api.example.com/v1 \
  --patient-id P123456 \
  --api-key your-api-key-here
```

### 凭证类型

根据不同API的认证方式，可能需要配置：

| 凭证类型 | 环境变量 | 说明 |
|---------|---------|------|
| API Key | HEALTH_API_KEY | 简单API密钥认证 |
| OAuth Token | HEALTH_OAUTH_TOKEN | OAuth2.0访问令牌 |
| OCR API Key | OCR_API_KEY | OCR服务API密钥 |

---

## 数据映射规范

### 标准输入格式

API返回的数据将被转换为以下标准格式：

```json
{
  "patient_info": {
    "name": "患者姓名",
    "age": 年龄,
    "gender": "性别"
  },
  "health_metrics": {
    "blood_pressure": {
      "systolic": 收缩压,
      "diastolic": 舒张压
    },
    "blood_glucose": {
      "fasting": 空腹血糖,
      "hba1c": 糖化血红蛋白
    },
    "blood_lipid": {
      "tc": 总胆固醇,
      "tg": 甘油三酯,
      "ldl_c": 低密度脂蛋白,
      "hdl_c": 高密度脂蛋白
    },
    "uric_acid": 尿酸,
    "bmi": {
      "height": 身高,
      "weight": 体重,
      "value": BMI值
    }
  }
}
```

### 常见字段映射

不同API可能使用不同的字段名称，系统会自动进行映射：

| 标准字段 | 可能的API字段名 |
|---------|---------------|
| systolic | sbp, systolic_bp, 收缩压 |
| diastolic | dbp, diastolic_bp, 舒张压 |
| fasting | fpg, fasting_glucose, 空腹血糖 |
| tc | total_cholesterol, 总胆固醇 |
| tg | triglyceride, 甘油三酯 |

### 自定义映射

如果API使用特殊的字段命名，可以在 `api_client.py` 的 `_normalize_api_data` 方法中添加映射规则。

---

## 错误处理

### 常见错误及解决方案

| 错误类型 | 错误信息 | 解决方案 |
|---------|---------|---------|
| 认证失败 | HTTP 401 | 检查API密钥是否正确 |
| 未找到患者 | HTTP 404 | 确认患者ID是否正确 |
| 网络超时 | Timeout | 检查网络连接，增加超时时间 |
| 数据格式错误 | JSON decode error | 检查API返回格式 |

### 重试机制

系统内置重试机制，对于临时性网络错误会自动重试3次。

---

## API开发指南

### 开发自定义API适配器

如果需要对接新的健康平台API，可以按照以下步骤开发适配器：

1. 在 `api_client.py` 中添加新的API类型处理方法
2. 实现数据映射逻辑
3. 处理特殊的认证方式
4. 添加错误处理

### 示例代码

```python
def _normalize_custom_api_data(self, api_data: Dict) -> Dict:
    """自定义API数据映射"""
    normalized = {
        'patient_info': {},
        'health_metrics': {}
    }
    
    # 添加映射逻辑
    # ...
    
    return normalized
```

---

## 安全注意事项

1. **凭证保护**：API密钥等敏感信息不要硬编码在代码中
2. **HTTPS加密**：确保API传输使用HTTPS协议
3. **数据脱敏**：保存数据时注意敏感信息脱敏
4. **访问控制**：限制API访问权限，避免未授权访问

---

## 常见问题

### Q: API返回的数据字段不完整怎么办？

A: 系统会自动检查必填字段，如缺失会提示用户补充。

### Q: 如何支持多个健康平台？

A: 可以为不同的平台配置不同的环境变量，或通过参数指定不同的API密钥。

### Q: API调用失败如何处理？

A: 系统会返回详细的错误信息，可根据错误类型进行相应处理。临时性错误可以重试。

---

## 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0 | 2024-01 | 初始版本 |
