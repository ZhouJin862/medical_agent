# SKILL.md 统一格式规范

本文档定义了医疗Agent系统中所有Claude Skills的SKILL.md文件统一格式规范。

## 概述

统一的SKILL.md格式确保：
- 所有skill使用一致的元数据结构
- 支持渐进式加载 (progressive disclosure)
- 支持多skill编排和组合执行
- 向后兼容旧格式
- 易于验证和维护

## 文件结构

```
skills/<domain>/<skill-name>/
├── SKILL.md                 # 主文件 (YAML frontmatter + markdown)
├── references/              # 参考材料目录
│   ├── *.md                # 参考文档
│   └── ...
├── scripts/                 # 辅助脚本目录
│   ├── *.py                # Python脚本
│   └── ...
├── examples/                # 可选示例目录
│   ├── *.md
│   └── *.json
└── assets/                  # 可选资源目录
    └── *.md                # 模板文件
```

## Frontmatter 格式

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | Skill唯一标识，kebab-case格式 |
| `description` | string | Skill描述，包含触发词说明 |

### 可选字段

#### 基础元数据

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `display_name` | string | name的值 | 显示名称 |
| `version` | string | "1.0.0" | 版本号 (semver) |
| `author` | string | - | 作者 |
| `license` | string | "MIT" | 许可证 |
| `enabled` | boolean | true | 是否启用 |

#### 执行配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `execution_type` | string | "prompt" | 执行类型: workflow/prompt/composite |
| `layer` | string | "domain" | 披露层次: basic/domain/composite |
| `priority` | integer | 10 | 优先级 (0-100, 越高越优先) |

#### 触发配置 (triggers)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keywords` | array | [] | 触发关键词列表 |
| `intent_patterns` | array | [] | 意图匹配正则表达式列表 |
| `confidence_threshold` | float | 0.7 | 匹配置信度阈值 (0-1) |

#### 依赖配置 (requires)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `python` | string | - | Python版本要求 |
| `packages` | array | [] | Python包依赖 |
| `mcp_servers` | array | [] | MCP服务器依赖 |
| `skills` | array | [] | 其他skill依赖 |

#### 输出配置 (output)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `format` | string | "structured" | 输出格式: structured/text/mixed |
| `schema` | object | null | JSON Schema (structured格式) |
| `template` | string | null | 输出模板 (text格式) |

#### Skill关系

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `complementary_skills` | array | [] | 互补skill列表 |
| `alternative_skills` | array | [] | 替代skill列表 |
| `required_skills` | array | [] | 前置skill列表 |
| `can_combine_with` | array | [] | 可合并执行的skill列表 |

## 完整示例

### Workflow类型Skill

```yaml
---
name: cvd-risk-assessment
display_name: 心血管病风险评估
description: |
  评估中国成年人心血管疾病风险，提供干预建议。

  触发词：心血管、心脏病、中风、风险评估、危险分层、健康评估

version: "1.0.0"
author: medical-agent-team
license: MIT
enabled: true

# 执行配置
execution_type: workflow
layer: domain
priority: 10

# 触发配置
triggers:
  keywords:
    - 心血管
    - 心脏病
    - 中风
    - 风险评估
    - 危险分层
    - 健康评估
  intent_patterns:
    - "评估.*风险"
    - ".*危险分层"
  confidence_threshold: 0.7

# 依赖配置
requires:
  python: ">=3.10"
  packages:
    - pyyaml==6.0.1
    - requests==2.31.0
  mcp_servers: []
  skills: []

# 输出配置
output:
  format: structured
  schema:
    type: object
    properties:
      risk_level:
        type: string
        enum: [low, medium, high, very_high]
      risk_factors:
        type: array
        items:
          type: string
      recommendations:
        type: array
        items:
          type: string

# Skill关系
complementary_skills:
  - skill: exercise-prescription
    relationship_type: complementary
    trigger_condition: "用户询问运动建议"
    context_transfer:
      - risk_level
      - recommended_activities

  - skill: diet-prescription
    relationship_type: complementary
    trigger_condition: "用户询问饮食建议"
    context_transfer:
      - risk_level
      - dietary_restrictions

alternative_skills:
  - skill: general-health-assessment
    relationship_type: alternative

can_combine_with:
  - diabetes-assessment
  - dyslipidemia-assessment
  - hypertension-assessment
---
```

### Prompt类型Skill

```yaml
---
name: health-education
display_name: 健康教育
description: |
  提供健康知识科普和健康教育内容。

  触发词：健康知识、科普、健康教育、什么是

version: "1.0.0"
author: medical-agent-team
license: MIT
enabled: true

# 执行配置
execution_type: prompt
layer: basic
priority: 5

# 触发配置
triggers:
  keywords:
    - 健康知识
    - 科普
    - 健康教育
    - 什么是
  confidence_threshold: 0.6

# 依赖配置
requires:
  python: ">=3.10"
  packages: []
  mcp_servers: []
  skills: []

# 输出配置
output:
  format: text
---
```

### Composite类型Skill

```yaml
---
name: comprehensive-health-check
display_name: 综合健康检查
description: |
  提供全面的健康评估，包含多项风险评估。

  触发词：全面检查、综合评估、体检分析、全身检查

version: "1.0.0"
author: medical-agent-team
license: MIT
enabled: true

# 执行配置
execution_type: composite
layer: composite
priority: 15

# 触发配置
triggers:
  keywords:
    - 全面检查
    - 综合评估
    - 体检分析
    - 全身检查
  confidence_threshold: 0.7

# 依赖配置 - 包含的base skills
requires:
  python: ">=3.10"
  packages: []
  mcp_servers: []
  skills:
    - cvd-risk-assessment
    - diabetes-risk-assessment
    - hypertension-risk-assessment

# 输出配置
output:
  format: structured
---
```

## 执行类型说明

### workflow (工作流类型)

适用于需要执行特定步骤的技能：

- 必须有 `scripts/` 目录
- SKILL.md中需要定义 "## 操作步骤" 或 "## 工作流" 章节
- 步骤格式：`### 步骤N：标题` 后跟代码块
- 示例：风险评估、计算类任务

### prompt (提示词类型)

适用于LLM直接生成响应的技能：

- 不需要scripts目录
- SKILL.md body内容作为LLM的指导prompt
- 适用于：问答、教育、解释类任务

### composite (组合类型)

适用于组合多个base skills的技能：

- 通过 `requires.skills` 定义包含的skills
- 定义组合逻辑和结果聚合方式
- 适用于：综合评估、多领域分析

## 命名规范

### Skill名称 (name)

- 格式：kebab-case (全小写，单词用连字符分隔)
- 示例：`cvd-risk-assessment`, `health-education`
- 禁止：中文、空格、驼峰命名

### 显示名称 (display_name)

- 可使用中文
- 简洁明了
- 示例：`心血管病风险评估`, `健康教育`

## 验证

使用提供的验证工具检查SKILL.md格式：

```python
from src.domain.shared.services.skill_frontmatter_parser import validate_skill_frontmatter
from pathlib import Path

is_valid, errors = validate_skill_frontmatter(Path("skills/cvd-risk-assessment/SKILL.md"))
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

## 迁移指南

### 从旧格式迁移

旧格式：
```yaml
---
name: cvd-risk-assessment
description: 心血管风险评估...触发词：心血管、心脏病
dependency:
  python:
    - pyyaml==6.0.1
---
```

新格式：
```yaml
---
name: cvd-risk-assessment
display_name: 心血管病风险评估
description: |
  心血管风险评估...

  触发词：心血管、心脏病

version: "1.0.0"
execution_type: workflow
layer: domain
priority: 10

triggers:
  keywords:
    - 心血管
    - 心脏病
  confidence_threshold: 0.7

requires:
  python: ">=3.10"
  packages:
    - pyyaml==6.0.1
---
```

### 自动迁移

使用迁移工具：
```python
from src.domain.shared.services.skill_frontmatter_parser import migrate_legacy_frontmatter

# 读取旧frontmatter
old_data = yaml.safe_load(old_frontmatter_str)

# 迁移到新格式
new_frontmatter = migrate_legacy_frontmatter(old_data, skill_name)

# 输出新frontmatter
import yaml
new_yaml = yaml.dump(new_frontmatter.to_dict(), allow_unicode=True)
```

## 最佳实践

1. **描述要详细**：description应包含skill的功能、适用场景、触发词
2. **触发词要精准**：使用用户可能输入的自然语言关键词
3. **优先级要合理**：重要且常用的skill设置更高优先级
4. **关系要明确**：明确定义与其他skill的关系，支持组合执行
5. **版本要管理**：重要变更时更新版本号
6. **保持向后兼容**：新格式应支持旧格式的平滑迁移
