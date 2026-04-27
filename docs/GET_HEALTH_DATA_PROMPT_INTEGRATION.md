# get_health_data Tool Integration with Agent Prompts

## Overview

The `get_health_data` tool from the Ping An health archive API has been integrated into the medical agent's prompts and workflow. This allows the agent to automatically retrieve comprehensive patient health data using a customer ID (客户号/partyId).

## What Was Changed

### 1. Agent Node Updates (`src/infrastructure/agent/nodes.py`)

#### `load_patient_node` Function
- Now attempts to use `get_health_data` when a `party_id` is available
- Falls back to individual tool calls (`get_patient_profile`, `get_vital_signs`, `get_medical_records`) if no `party_id` is provided
- Extracts `party_id` from:
  - User input dictionary
  - Conversation memory context
  - Extracted user profile

#### `_extract_user_profile` Function
- Added pattern matching for `party_id` (客户号) extraction from conversations
- Recognizes patterns like:
  - `客户号：12345678`
  - `partyId: ABC123`
  - `客户编号：xxx`
  - `编号：12345678`

### 2. Skill Signature Updates (`src/infrastructure/dspy/signatures/four_highs.py`)

#### `HealthAssessmentSignature`
- Added `party_id` as an optional input field
- Updated system prompt to mention `get_health_data` tool
- Updated prompt template to indicate when Ping An data was used

#### `RiskPredictionSignature`
- Added `party_id` as an optional input field
- Updated system prompt to mention `get_health_data` tool for complete historical data
- Updated prompt template to indicate when Ping An data was used

## How It Works

### Flow Diagram

```
User Input (with party_id)
       |
       v
[extract_user_profile] --> Extract party_id from conversation
       |
       v
[load_patient_node] --> Check if party_id available
       |
       +-- Yes --> Use get_health_data(party_id)
       |             Returns comprehensive data from Ping An API
       |
       +-- No --> Use individual tools (get_patient_profile, etc.)
       |
       v
[Patient Context Created] --> Contains all patient data
       |
       v
[Skill Execution] --> health_assessment, risk_prediction, etc.
       |
       v
[Response Generated]
```

### Data Flow with party_id

When a user provides a `party_id` (客户号):

1. **Extraction**: The agent extracts the party_id from user input or conversation history
2. **API Call**: `get_health_data(party_id="12345678")` is called
3. **Data Retrieved**:
   ```json
   {
     "data": {
       "basic_info": { "name": "...", "gender": "...", "age": 30 },
       "health_indicators": { "blood_pressure": "...", "blood_glucose": "..." },
       "diagnoses": [...],
       "medications": [...],
       "allergies": [...],
       "chronic_diseases": [...]
     },
     "_metadata": {
       "party_id": "12345678",
       "request_id": "...",
       "iesp_api_code": "queryHealthData"
     }
   }
   ```
4. **Context Creation**: Patient context is populated with all retrieved data
5. **Skill Execution**: Skills use the comprehensive data for assessment

## Usage Examples

### Example 1: Direct party_id in User Input

```
User: "我的客户号是12345678，请帮我做健康评估"

Agent Response:
- Extracts party_id: "12345678"
- Calls get_health_data(party_id="12345678")
- Generates health assessment using retrieved data
```

### Example 2: party_id in Conversation History

```
Conversation:
User: "你好"
Agent: "您好，请问有什么可以帮您？"
User: "我的客户号是12345678"
Agent: "好的，已记录您的客户号"
User: "请帮我做健康评估"

Agent Response:
- Retrieves party_id: "12345678" from conversation memory
- Calls get_health_data(party_id="12345678")
- Generates health assessment
```

### Example 3: No party_id Provided

```
User: "请帮我做健康评估"

Agent Response:
- No party_id available
- Uses individual tools: get_patient_profile, get_vital_signs, get_medical_records
- Generates assessment with available data
```

## Prompt Updates

### Health Assessment System Prompt

```
你是一位专业的健康管理师，负责评估用户的整体健康状况。

请根据提供的用户体征数据和健康信息，进行全面、客观的健康评估。
评估结果应包含：
1. 整体健康状况评级
2. 各项指标的分析
3. 异常指标说明
4. 健康建议

可用工具：
- get_health_data: 使用party_id（客户号）从平安健康档案系统获取患者健康数据

注意：如果用户提供了客户号(partyId/客户号)，应该优先使用get_health_data工具获取完整的健康档案数据。
```

### Risk Prediction System Prompt

```
你是一位专业的风险评估专家，负责预测用户的健康风险。

基于用户当前的体征数据和病史，预测：
1. 患病风险率（各种疾病的发生概率）
2. 疾病恶化风险率
3. 并发症风险
4. 失能风险
5. 预期医疗成本

预测应基于医学指南和循证医学证据。

可用工具：
- get_health_data: 使用party_id（客户号）从平安健康档案系统获取患者完整健康数据，用于更准确的风险预测

注意：如果用户提供了客户号(partyId/客户号)，应该优先使用get_health_data工具获取完整的历史数据。
```

## party_id Pattern Matching

The agent recognizes these patterns for party_id extraction:

| Pattern | Example | Extracted Value |
|---------|---------|-----------------|
| 客户号： | 客户号：12345678 | 12345678 |
| 客户号 | 客户号 12345678 | 12345678 |
| partyId: | partyId: ABC123 | ABC123 |
| party_id: | party_id: ABC123 | ABC123 |
| 客户编号： | 客户编号：12345678 | 12345678 |
| 编号： | 编号：12345678 | 12345678 |

## MCP Tool Definition

The `get_health_data` tool is registered in the profile MCP server:

```python
{
    "name": "get_health_data",
    "description": "Get comprehensive patient health data from Ping An health archive system using OAuth2 authentication. Queries basic info, vital signs, medical records, and lab results by customer ID (partyId/客户号)",
    "inputSchema": {
        "type": "object",
        "properties": {
            "party_id": {
                "type": "string",
                "description": "Customer/Patient identifier from Ping An system (客户号/partyId)"
            }
        },
        "required": ["party_id"]
    }
}
```

## Testing

### Manual Testing

```bash
# Test the pingan client
python tests/integration/mcp/test_pingan_client.py

# Test agent with party_id
curl -X POST http://localhost:8003/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "test_001",
    "message_content": "我的客户号是12345678，请帮我做健康评估",
    "consultation_id": null
  }'
```

### Expected Behavior

1. **With valid party_id**: Complete health data retrieved from Ping An API
2. **With invalid party_id**: Error response from API, fallback to individual tools
3. **Without party_id**: Individual tools called directly

## Configuration

### Environment Variables

No additional environment variables are required. The Ping An API credentials are configured in:
- `mcp_servers/profile_server/pingan_client.py`

### API Endpoints

- **Token URL**: `https://test-api.pingan.com.cn:20443/oauth/oauth2/access_token`
- **Data URL**: `https://test-api.pingan.com.cn:20443/open/appsvr/health/ehis/iesp/purveyor/postWithJson.do`

## Future Enhancements

1. **Caching**: Cache retrieved health data to reduce API calls
2. **Batch Operations**: Support multiple party_ids in a single request
3. **Real-time Updates**: Implement webhook for data updates
4. **Error Handling**: Enhanced error messages for common failures
5. **Audit Logging**: Log all party_id access for compliance

## Related Documentation

- [Ping An Health Archive API](./PINGAN_HEALTH_ARCHIVE_API.md)
- [MCP Tools Documentation](../mcp_servers/README.md)
- [Agent Architecture](./ARCHITECTURE.md)
