# Medical Agent API 文档

慢病健康管理智能体系统 RESTful API 完整参考文档。

## 目录

- [概述](#概述)
- [认证](#认证)
- [通用规范](#通用规范)
- [核心端点](#核心端点)
- [数据模型](#数据模型)
- [错误代码](#错误代码)
- [速率限制](#速率限制)

## 概述

Medical Agent API 提供慢病健康管理的智能对话服务，支持健康评估、风险预测、个性化处方等功能。

**Base URL:**
- 开发环境: `http://localhost:8000`
- 生产环境: `https://api.medical-agent.com`

**API 版本:** `v1`

## 认证

### API Key 认证

```http
GET /api/v1/chat/sessions
Authorization: Bearer YOUR_API_KEY
```

### 获取 API Key

1. 登录管理控制台
2. 进入 API 密钥管理
3. 创建新密钥
4. 复制密钥（仅显示一次）

### 密钥权限

| 权限 | 描述 |
|------|------|
| `chat:read` | 读取对话历史 |
| `chat:write` | 发送消息 |
| `health:read` | 读取健康数据 |
| `plan:read` | 读取健康计划 |
| `admin` | 管理员权限 |

## 通用规范

### 请求格式

**Content-Type:** `application/json`

**示例请求:**

```http
POST /api/chat/send HTTP/1.1
Host: api.medical-agent.com
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "message": "我的血压是135/88，正常吗？",
  "patient_id": "patient-001",
  "context": {
    "age": 45,
    "gender": "male"
  }
}
```

### 响应格式

所有响应遵循以下结构：

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req-abc123"
}
```

### 分页

列表端点支持分页：

```http
GET /api/chat/consultations?page=1&page_size=20
```

**响应:**

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

## 核心端点

### 1. 聊天对话

#### 1.1 发送消息

发送用户消息并获取 AI 响应。

```http
POST /api/chat/send HTTP/1.1
```

**请求参数:**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| message | string | 是 | 用户消息内容 |
| patient_id | string | 是 | 患者ID |
| consultation_id | string | 否 | 对话ID（继续对话） |
| context | object | 否 | 额外上下文信息 |
| vital_signs | object | 否 | 体征数据 |
| request_type | string | 否 | 请求类型 |

**请求示例:**

```json
{
  "message": "我的血压是135/88，这正常吗？需要担心吗？",
  "patient_id": "patient-001",
  "vital_signs": {
    "blood_pressure": {
      "systolic": 135,
      "diastolic": 88
    }
  }
}
```

**响应示例:**

```json
{
  "consultation_id": "consult-20240115-001",
  "message_id": "msg-001",
  "response": "您的血压135/88 mmHg处于正常高值范围。收缩压（高压）略高于正常值上限（<130 mmHg），舒张压在正常范围内。建议您：1）定期监测血压变化；2）注意低盐饮食；3）保持适量运动；4）管理压力。如果血压持续升高，请咨询医生。",
  "intent": "health_assessment",
  "confidence": 0.95,
  "skills_used": ["hypertension_assessment"],
  "related_info": {
    "blood_pressure_status": "normal_high",
    "risk_category": "low"
  },
  "follow_up_suggestions": [
    "建议在安静环境下休息5分钟后再次测量",
    "记录连续一周的血压数据"
  ]
}
```

#### 1.2 获取对话历史

获取对话的消息历史。

```http
GET /api/chat/consultations/{consultation_id}/messages HTTP/1.1
```

**路径参数:**

| 参数 | 描述 |
|------|------|
| consultation_id | 对话ID |

**查询参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| page | int | 页码（默认1） |
| page_size | int | 每页数量（默认50） |

**响应示例:**

```json
{
  "consultation_id": "consult-20240115-001",
  "patient_id": "patient-001",
  "messages": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "我的血压是135/88",
      "timestamp": "2024-01-15T10:00:00Z"
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "您的血压处于正常高值...",
      "intent": "health_assessment",
      "timestamp": "2024-01-15T10:00:01Z"
    }
  ],
  "total": 2
}
```

#### 1.3 关闭对话

关闭一个对话会话。

```http
POST /api/chat/consultations/{consultation_id}/close HTTP/1.1
```

**响应示例:**

```json
{
  "success": true,
  "closed_at": "2024-01-15T10:30:00Z"
}
```

### 2. 健康评估

#### 2.1 获取健康数据

获取患者的健康评估数据。

```http
GET /api/health/{patient_id} HTTP/1.1
```

**路径参数:**

| 参数 | 描述 |
|------|------|
| patient_id | 患者ID |

**响应示例:**

```json
{
  "patient_id": "patient-001",
  "last_assessment": "2024-01-15T10:00:00Z",
  "vital_signs": {
    "blood_pressure": {
      "systolic": 135,
      "diastolic": 88,
      "status": "normal_high",
      "last_measured": "2024-01-15T09:00:00Z"
    },
    "blood_glucose": {
      "fasting": 6.2,
      "hba1c": 6.0,
      "status": "normal",
      "last_measured": "2024-01-14T08:00:00Z"
    }
  },
  "risk_assessment": {
    "overall_risk": "low",
    "risk_factors": [
      {
        "type": "blood_pressure",
        "level": "elevated",
        "confidence": 0.85
      }
    ]
  }
}
```

#### 2.2 创建健康评估

创建新的健康评估记录。

```http
POST /api/health/assessments HTTP/1.1
```

**请求参数:**

```json
{
  "patient_id": "patient-001",
  "assessment_type": "comprehensive",
  "vital_signs": {
    "blood_pressure": {"systolic": 135, "diastolic": 88},
    "blood_glucose": {"fasting": 6.2, "hba1c": 6.0},
    "lipid": {
      "total_cholesterol": 5.2,
      "ldl_c": 3.0,
      "hdl_c": 1.2,
      "triglycerides": 1.8
    }
  }
}
```

**响应示例:**

```json
{
  "assessment_id": "assessment-001",
  "created_at": "2024-01-15T11:00:00Z",
  "results": {
    "conditions": [
      {
        "name": "prehypertension",
        "status": "normal_high",
        "confidence": 0.9
      }
    ],
    "recommendations": [
      "定期监测血压",
      "低盐饮食"
    ]
  }
}
```

### 3. 健康计划

#### 3.1 获取健康计划

获取患者的个性化健康计划。

```http
GET /api/plan/{patient_id} HTTP/1.1
```

**响应示例:**

```json
{
  "plan_id": "plan-001",
  "patient_id": "patient-001",
  "created_at": "2024-01-15T00:00:00Z",
  "valid_until": "2024-04-15T00:00:00Z",
  "prescriptions": {
    "diet": {
      "type": "diet_prescription",
      "title": "DASH饮食方案",
      "description": "采用DASH（Dietary Approaches to Stop Hypertension）饮食模式",
      "recommendations": [
        "每日蔬菜摄入量: 500-600克",
        "水果每日: 200-300克",
        "低脂乳制品: 每日2-3份"
      ],
      "restrictions": [
        "钠盐每日<5克",
        "红肉每周<3份"
      ]
    },
    "exercise": {
      "type": "exercise_prescription",
      "title": "有氧运动处方",
      "frequency": "每周5次",
      "duration_per_session": "30-45分钟",
      "intensity": "中等强度",
      "activities": [
        "快走",
        "游泳",
        "骑自行车"
      ]
    },
    "medication": {
      "type": "medication_prescription",
      "medications": [
        {
          "name": "降压药（如需要）",
          "dosage": "遵医嘱",
          "frequency": "每日1次",
          "notes": "请在医生指导下使用"
        }
      ]
    }
  }
}
```

### 4. Skill 管理

#### 4.1 列出可用 Skills

```http
GET /api/v3/skills HTTP/1.1
```

**响应示例:**

```json
{
  "skills": [
    {
      "id": "hypertension_assessment",
      "name": "高血压评估",
      "category": "four_highs",
      "description": "评估血压水平和高血压风险",
      "enabled": true,
      "version": "1.0.0",
      "endpoints": [
        "血压评估",
        "心血管风险预测"
      ],
      "input_schema": {
        "blood_pressure": {
          "systolic": "number",
          "diastolic": "number"
        }
      }
    }
  ]
}
```

#### 4.2 获取 Skill 详情

```http
GET /api/v3/skills/{skill_name} HTTP/1.1
```

**响应示例:**

```json
{
  "id": "hypertension_assessment",
  "name": "高血压评估",
  "description": "根据血压值评估高血压等级和风险",
  "category": "four_highs",
  "enabled": true,
  "prompt_template": "请根据以下血压数据进行评估...",
  "model_config": {
    "model": "glm-5",
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "systolic": {"type": "number"},
      "diastolic": {"type": "number"}
    },
    "required": ["systolic", "diastolic"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "level": {"type": "string"},
      "risk_category": {"type": "string"}
    }
  }
}
```

### 5. 流式聊天

#### 5.1 SSE 流式响应

```http
POST /api/chat/stream HTTP/1.1
```

**请求格式:** 与 `/api/chat/send` 相同

**响应格式:** Server-Sent Events (SSE)

```
data: {"type": "start", "request_id": "req-001"}

data: {"type": "token", "content": "您的"}

data: {"type": "token", "content": "血压"}

data: {"type": "end", "full_response": "您的血压..."}
```

**客户端示例:**

```javascript
const eventSource = new EventSource('/api/chat/stream?' + new URLSearchParams({
  message: "我的血压是135/88",
  patient_id: "patient-001"
}));

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'token') {
    // 显示 token
    appendToChat(data.content);
  } else if (data.type === 'end') {
    eventSource.close();
    showFullResponse(data.full_response);
  }
};
```

### 6. WebSocket 连接

#### 6.1 建立 WebSocket 连接

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/patient-001');

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleIncomingMessage(message);
};

// 发送消息
ws.send(JSON.stringify({
  type: 'message',
  content: '我的血压是135/88'
}));
```

## 数据模型

### Consultation（对话）

```typescript
interface Consultation {
  consultation_id: string;
  patient_id: string;
  status: 'active' | 'closed' | 'archived';
  created_at: string;
  updated_at: string;
  messages: Message[];
}
```

### Message（消息）

```typescript
interface Message {
  id: string;
  consultation_id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  confidence?: number;
  timestamp: string;
  metadata?: Record<string, any>;
}
```

### VitalSigns（体征）

```typescript
interface VitalSigns {
  blood_pressure?: {
    systolic: number;
    diastolic: number;
  };
  blood_glucose?: {
    fasting?: number;
    postprandial?: number;
    hba1c?: number;
  };
  lipid?: {
    total_cholesterol?: number;
    ldl_c?: number;
    hdl_c?: number;
    triglycerides?: number;
  };
  uric_acid?: number;
  bmi?: number;
}
```

## 错误代码

### HTTP 状态码

| 代码 | 描述 |
|------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 数据验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

### 错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "message": ["不能为空", "格式不正确"]
    },
    "request_id": "req-abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 常见错误代码

| 代码 | 描述 | 解决方案 |
|------|------|----------|
| `INVALID_API_KEY` | API 密钥无效 | 检查密钥是否正确 |
| `RATE_LIMIT_EXCEEDED` | 超出速率限制 | 降低请求频率 |
| `PATIENT_NOT_FOUND` | 患者不存在 | 检查 patient_id |
| `CONSULTATION_CLOSED` | 对话已关闭 | 创建新对话 |
| `SKILL_NOT_ENABLED` | Skill 未启用 | 启用对应 Skill |
| `LLM_TIMEOUT` | LLM API 超时 | 稍后重试 |

## 速率限制

### 默认限制

| 层级 | 限制 | 适用场景 |
|------|------|----------|
| 免费版 | 100 请求/小时 | 个人用户 |
| 基础版 | 1000 请求/小时 | 小型诊所 |
| 专业版 | 10000 请求/小时 | 中型机构 |
| 企业版 | 无限制 | 大型机构 |

### 速率限制头

响应中包含以下头：

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642234567
```

### 重试策略

遇到 429 错误时，使用指数退避：

```python
import time
import requests

def send_with_retry(url, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json=data)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
            time.sleep(retry_after)
        else:
            return response

    raise Exception("Max retries exceeded")
```

## SDK 和示例

### Python SDK

```python
from medical_agent import MedicalAgentClient

client = MedicalAgentClient(api_key="your-api-key")

# 发送消息
response = client.chat.send(
    message="我的血压是135/88",
    patient_id="patient-001"
)

print(response.response)
```

### JavaScript SDK

```javascript
import { MedicalAgent } from '@medical-agent/sdk';

const client = new MedicalAgent('your-api-key');

const response = await client.chat.send({
  message: '我的血压是135/88',
  patientId: 'patient-001'
});

console.log(response.response);
```

### cURL 示例

```bash
curl -X POST https://api.medical-agent.com/api/chat/send \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的血压是135/88",
    "patient_id": "patient-001"
  }'
```

## 更新日志

### v1.2.0 (2024-01-15)
- 新增流式聊天 API
- 新增 WebSocket 支持
- 优化 Skill 查询性能

### v1.1.0 (2024-01-01)
- 新增健康计划 API
- 支持批量体征数据提交
- 优化错误响应格式

### v1.0.0 (2023-12-15)
- 初始版本发布
- 基础聊天对话功能
- 健康评估功能
