# Composite Skills Guide

## Overview

**Composite Skills** allow you to combine multiple base skills (from file system or database) with custom business rules and configuration. This enables:

- **Personalized workflows** - Combine standard assessments with organization-specific logic
- **Multi-domain assessments** - Run several related assessments in one request
- **Custom response formats** - Tailor the output style for different user segments
- **Business rule integration** - Apply organization-specific decision logic

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Composite Skill Request                     │
│                  "VIP用户做综合健康评估"                          │
└────────────────────────────────────┬────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              1. Check if Composite Skill                        │
│              - Lookup in database by skill name                 │
│              - Check for base_skills configuration              │
└────────────────────────────────────┬────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
        ┌───────────────────────┐     ┌──────────────────────────┐
        │   Composite Skill     │     │   Standard Skill          │
        │   (Database)          │     │   (File or Database)      │
        └───────────┬───────────┘     └───────────┬──────────────┘
                    │                             │
                    ▼                             ▼
        ┌───────────────────────┐     ┌──────────────────────────┐
        │ Composite Executor    │     │ Claude Skills Executor    │
        │                       │     │                           │
        │ 1. Load Base Skills   │     │ 1. Load SKILL.md          │
        │ 2. Apply Overrides    │     │ 2. Build Prompt           │
        │ 3. Execute (Seq/Par)  │     │ 3. Generate Response      │
        │ 4. Aggregate Results  │     │                           │
        └───────────┬───────────┘     └───────────┬──────────────┘
                    │                             │
                    └────────────────┬────────────┘
                                     ▼
                        ┌───────────────────────┐
                        │    Return Response     │
                        └───────────────────────┘
```

## Database Schema

Composite skills are stored in the `skills` table with a special `config` structure:

```sql
CREATE TABLE skills (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    type ENUM('generic', 'disease_specific', 'prescription', 'mcp_tool'),
    enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) DEFAULT '1.0.0',

    -- Composite skill configuration
    config JSON,

    INDEX idx_skill_name (name),
    INDEX idx_skill_enabled (enabled)
);
```

### Composite Skill Config Structure

```json
{
  "base_skills": [
    "hypertension-assessment",
    "diabetes_assessment",
    "obesity_assessment"
  ],
  "override_settings": {
    "response_style": "vip_detailed",
    "include_recommendations": true,
    "add_personal_notes": true
  },
  "business_rules": {
    "priority_queue": true,
    "dedicated_specialist": true,
    "follow_up_reminder": true
  },
  "workflow_config": {
    "execution_mode": "sequential",
    "timeout_seconds": 60
  },
  "display_name": "VIP综合健康评估",
  "response_style": "vip_detailed",
  "execution_mode": "sequential"
}
```

## Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `base_skills` | `string[]` | List of skill names to combine (required) |
| `override_settings` | `object` | Custom settings to apply to all skills |
| `business_rules` | `object` | Organization-specific business rules |
| `workflow_config` | `object` | Workflow execution configuration |
| `display_name` | `string` | Human-readable name for the composite skill |
| `response_style` | `string` | Style: `standard` or `vip_detailed` |
| `execution_mode` | `string` | Mode: `sequential` or `parallel` |

## Execution Modes

### Sequential Mode (default)

Skills execute one after another, with each skill receiving the output of previous skills as context.

```json
{
  "execution_mode": "sequential"
}
```

**Use case**: When later skills need to build on earlier skill outputs.

**Example**:
1. First skill: General health assessment
2. Second skill: Risk prediction (uses assessment results)
3. Third skill: Recommendations (uses risk level)

### Parallel Mode

All skills execute simultaneously, then results are aggregated.

```json
{
  "execution_mode": "parallel"
}
```

**Use case**: When skills are independent and can run concurrently.

**Example**:
1. Blood pressure assessment
2. Diabetes assessment
3. Lipid assessment

All run in parallel, then results are combined.

## Creating Composite Skills

### Method 1: Direct Database Insert

```sql
INSERT INTO skills (
    id, name, display_name, description, type, enabled, config
) VALUES (
    UUID(),
    'vip_health_plan',
    'VIP综合健康评估',
    '为VIP用户提供综合健康评估服务，包括高血压、糖尿病、血脂等多项评估',
    'generic',
    TRUE,
    JSON_SET(
        JSON_OBJECT(),
        '$.base_skills',
        JSON_ARRAY('hypertension-assessment', 'diabetes_assessment', 'obesity_assessment'),
        '$.override_settings',
        JSON_OBJECT('response_style', 'vip_detailed'),
        '$.execution_mode',
        'sequential'
    )
);
```

### Method 2: API Endpoint

```bash
curl -X POST "http://localhost:8006/api/v2/skills/composite" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "vip_health_plan",
    "display_name": "VIP综合健康评估",
    "description": "为VIP用户提供综合健康评估",
    "base_skills": [
      "hypertension-assessment",
      "diabetes_assessment",
      "obesity_assessment"
    ],
    "override_settings": {
      "response_style": "vip_detailed"
    },
    "execution_mode": "sequential"
  }'
```

### Method 3: Python API

```python
from src.infrastructure.database import get_db_session
from src.infrastructure.persistence.models.skill_models import SkillModel
import json

async def create_composite_skill():
    async for session in get_db_session():
        skill = SkillModel(
            name="vip_health_plan",
            display_name="VIP综合健康评估",
            description="为VIP用户提供综合健康评估",
            type=SkillType.GENERIC,
            enabled=True,
            config={
                "base_skills": [
                    "hypertension-assessment",
                    "diabetes_assessment",
                    "obesity_assessment"
                ],
                "override_settings": {
                    "response_style": "vip_detailed"
                },
                "execution_mode": "sequential"
            }
        )
        session.add(skill)
        await session.commit()
        break
```

## Using Composite Skills

### Via Agent API

```bash
curl -X POST "http://localhost:8006/api/agent/process" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient_001",
    "message": "帮我做VIP综合健康评估，我血压150/95，血糖7.5"
  }'
```

The agent will:
1. Classify intent → Select `vip_health_plan` skill
2. Detect it's a composite skill
3. Load base skills: hypertension, diabetes, obesity
4. Execute sequentially with VIP styling
5. Return aggregated response

### Via Direct Skill Invocation

```bash
curl -X POST "http://localhost:8006/api/agent/process" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient_001",
    "message": "@vip_health_plan 帮我评估一下"
  }'
```

Using `@skill_name` directly invokes the skill.

## Response Styles

### Standard Style

```
Based on my analysis:

**Hypertension Assessment:**
Your blood pressure of 150/95 mmHg indicates...

**Diabetes Assessment:**
Your fasting glucose of 7.5 mmol/L indicates...
```

### VIP Detailed Style

```
## Personalized Health Assessment

### Executive Summary
I've conducted a comprehensive assessment across multiple health domains...

### Detailed Findings

#### Hypertension Assessment
[Detailed analysis...]

#### Diabetes Assessment
[Detailed analysis...]

### Personalized Recommendations
Based on the above assessment, I recommend:
- [Specific recommendations...]
```

## Best Practices

### 1. Skill Selection

- **Combine related skills** - Skills that assess related conditions
- **Avoid redundancy** - Don't combine skills with significant overlap
- **Consider execution time** - Parallel mode for independent skills

### 2. Configuration

- **Use clear naming** - `vip_health_plan`, `comprehensive_checkup`
- **Document purpose** - Clear description of when to use
- **Set appropriate mode** - Sequential if dependencies exist

### 3. Response Styling

- **Match user segment** - VIP style for premium users
- **Keep aggregated output readable** - Don't overwhelm with too much detail
- **Include clear sections** - Summary, findings, recommendations

## Examples

### Example 1: Chronic Disease Management

```json
{
  "name": "chronic_disease_management",
  "display_name": "慢病综合管理",
  "description": "高血压、糖尿病、血脂综合管理",
  "base_skills": [
    "hypertension-assessment",
    "diabetes_assessment",
    "dyslipidemia-assessment"
  ],
  "override_settings": {
    "include_treatment_plan": true,
    "include_lifestyle_advice": true
  },
  "execution_mode": "parallel"
}
```

### Example 2: Health Checkup Plus

```json
{
  "name": "health_checkup_plus",
  "display_name": "健康体检+",
  "description": "全面健康评估，包含四高和肥胖",
  "base_skills": [
    "hypertension-assessment",
    "diabetes_assessment",
    "dyslipidemia-assessment",
    "gout_assessment",
    "obesity_assessment"
  ],
  "override_settings": {
    "response_style": "detailed"
  },
  "execution_mode": "parallel"
}
```

### Example 3: Hospital Triage Workflow

```json
{
  "name": "hospital_triage",
  "display_name": "医院分诊流程",
  "description": "医院内部分诊和初步评估流程",
  "base_skills": [
    "health_consultation",
    "health_checkup_assessment"
  ],
  "business_rules": {
    "department_routing": true,
    "urgency_classification": true,
    "resource_check": true
  },
  "workflow_config": {
    "assign_department": true,
    "notify_specialist": "high_risk"
  },
  "execution_mode": "sequential"
}
```

## Troubleshooting

### Issue: Base skills not found

**Cause**: One or more base skills don't exist or are disabled.

**Solution**:
1. Check if base skills exist: `GET /api/v2/skills`
2. Verify base skills are enabled
3. Check skill name spelling (case-sensitive)

### Issue: Execution timeout

**Cause**: Too many skills in parallel or slow skill execution.

**Solution**:
1. Reduce number of base skills
2. Switch to sequential mode
3. Increase timeout in workflow_config

### Issue: Poor response aggregation

**Cause**: Skills have conflicting or overlapping outputs.

**Solution**:
1. Review base skill compatibility
2. Adjust override_settings
3. Create custom aggregation logic

## Migration from Single Skills

To migrate existing database skills to composite skills:

1. **Identify related skills** - Skills often used together
2. **Create composite config** - Define base_skills array
3. **Test execution** - Verify aggregation works
4. **Update references** - Point users to composite skill
5. **Deprecate individual** - Mark old skills if needed

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/skills/composite` | POST | Create composite skill |
| `/api/v2/skills/composite/{name}` | GET | Get composite skill config |
| `/api/v2/skills/composite/{name}` | PUT | Update composite skill |
| `/api/v2/skills/composite/{name}` | DELETE | Delete composite skill |
| `/api/agent/process` | POST | Execute via agent |
