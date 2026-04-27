# 医疗智能体技能系统设计方案

## 设计理念

参考 Claude Code 的技能系统，为医疗智能体设计一套声明式、可扩展的技能管理系统。

### 核心原则

1. **声明式定义** - 技能通过 YAML/JSON 配置定义，无需修改代码
2. **意图驱动** - 通过关键词和上下文自动触发匹配的技能
3. **渐进增强** - 支持基础技能 → 规则增强 → 组合技能的层级
4. **可观测性** - 完整的技能执行追踪和调试

---

## 1. 技能规格定义

### 1.1 技能元数据结构

```yaml
# skills/hypertension_assessment.yml
name: hypertension_assessment
display_name: "高血压评估"
version: "1.0.0"
category: health_assessment
layer: domain

# 触发配置
triggers:
  # 显式触发
  slash_command: "/bp-assess"

  # 隐式触发 - 意图关键词
  intent_keywords:
    - "血压"
    - "高血压"
    - "收缩压"
    - "舒张压"
    - "血压高"

  # 上下文条件
  context_conditions:
    requires_patient_data: true
    min_confidence: 0.6

# 技能配置
config:
  # 规则增强
  rule_enhancement:
    enabled: true
    categories:
      - diagnosis
      - risk_assessment
    disease_code: hypertension
    use_vital_signs: true
    use_risk_scoring: true

# 提示词模板
prompt_template: |
  你是一个高血压评估专家。

  用户输入: {{user_input}}

  {% if rule_results %}
  匹配的临床规则:
  {% for rule in rule_results %}
  - {{rule.name}} (置信度: {{rule.confidence}})
  {% endfor %}
  {% endif %}

  请基于上述信息提供专业的评估和建议。

# 参数提取配置
extraction:
  - field: systolic
    patterns:
      - "(?P<systolic>\\d+)[/\\/](?P<diastolic>\\d+)"
      - "收缩压(?P<systolic>\\d+)"
    type: integer
  - field: diastolic
    patterns:
      - "(?P<systolic>\\d+)[/\\/](?P<diastolic>\\d+)"
      - "舒张压(?P<diastolic>\\d+)"
    type: integer

# 输出格式
output:
  format: structured
  schema:
    assessment:
      type: string
    risk_level:
      type: enum
      values: [normal, elevated, high, very_high]
    recommendations:
      type: array
      items: string

# 权限和安全
security:
  requires_auth: false
  max_requests_per_minute: 10
  allowed_scopes: [patient_read, assessment_write]
```

### 1.2 技能类型分类

```yaml
# 技能层级定义
layers:
  # Layer 1: 基础工具 - 始终可用
  basic:
    - name: data_parser
      description: "解析用户输入的医疗数据"
    - name: format_helper
      description: "格式化医疗报告"

  # Layer 2: 领域技能 - 按需披露
  domain:
    - name: hypertension_assessment
      description: "高血压评估"
      trigger_keywords: ["血压", "高血压"]
    - name: diabetes_assessment
      description: "糖尿病评估"
      trigger_keywords: ["血糖", "糖尿病"]
    - name: dyslipidemia_assessment
      description: "血脂评估"
      trigger_keywords: ["血脂", "胆固醇"]

  # Layer 3: 组合技能 - 复杂任务
  composite:
    - name: comprehensive_health_checkup
      description: "综合健康体检评估"
      workflow:
        - step: collect_vital_signs
        - step: assess_four_highs
        - step: generate_report
      trigger_conditions:
        complexity_threshold: 0.8
```

---

## 2. 触发机制设计

### 2.1 触发流程图

```
用户输入: "我血压150/95，严重吗？"
    │
    ▼
┌─────────────────────────────┐
│  1. 输入预处理               │
│  - 分词                     │
│  - 实体提取                 │
│  - 上下文加载               │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  2. 显式触发检测             │
│  - 是否以 / 开头?           │
│  - 匹配 slash_command       │
└──────────┬──────────────────┘
           │ No
           ▼
┌─────────────────────────────┐
│  3. 意图识别                │
│  - 关键词匹配               │
│  - 语义相似度计算           │
│  - 上下文相关性             │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  4. 技能候选排序            │
│  - 置信度评分              │
│  - 优先级排序              │
│  - 层级过滤                │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  5. 技能选择                │
│  - 最高置信度              │
│  - 或多技能并行             │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  6. 参数提取                │
│  - 正则匹配                │
│  - NER 实体识别            │
│  - 上下文推断              │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  7. 技能执行                │
│  - 规则评估                │
│  - LLM 调用                │
│  - 响应生成                │
└─────────────────────────────┘
```

### 2.2 触发器实现

```python
# src/domain/shared/services/skill_trigger.py

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import re

class TriggerType(Enum):
    """触发类型"""
    SLASH_COMMAND = "slash_command"      # /bp-assess
    INTENT_KEYWORD = "intent_keyword"    # "血压"
    CONTEXT_PATTERN = "context_pattern"  # 上下文模式
    SEMANTIC_SIMILARITY = "semantic"     # 语义相似度

@dataclass
class TriggerMatch:
    """触发匹配结果"""
    trigger_type: TriggerType
    skill_id: str
    confidence: float
    extracted_params: Dict[str, Any]
    match_reason: str

class SkillTriggerEngine:
    """
    技能触发引擎

    负责:
    1. 解析用户输入
    2. 匹配技能触发条件
    3. 提取技能参数
    4. 返回匹配的技能列表
    """

    def __init__(self, skill_registry):
        self._skill_registry = skill_registry
        self._entity_extractor = EntityExtractor()

    async def match_skills(
        self,
        user_input: str,
        context: Dict[str, Any],
    ) -> List[TriggerMatch]:
        """
        匹配用户输入到技能

        Args:
            user_input: 用户原始输入
            context: 对话上下文

        Returns:
            按置信度排序的技能匹配列表
        """
        matches = []

        # 1. 检查显式触发 (/command)
        slash_match = self._match_slash_command(user_input)
        if slash_match:
            matches.append(slash_match)
            return matches  # 显式命令优先

        # 2. 关键词匹配
        keyword_matches = await self._match_keywords(user_input, context)
        matches.extend(keyword_matches)

        # 3. 上下文模式匹配
        context_matches = await self._match_context(user_input, context)
        matches.extend(context_matches)

        # 4. 语义相似度（可选，需要嵌入模型）
        semantic_matches = await self._match_semantic(user_input, context)
        matches.extend(semantic_matches)

        # 按置信度排序
        matches.sort(key=lambda m: m.confidence, reverse=True)

        # 过滤低置信度匹配
        min_confidence = context.get("min_confidence", 0.3)
        matches = [m for m in matches if m.confidence >= min_confidence]

        return matches

    def _match_slash_command(self, user_input: str) -> Optional[TriggerMatch]:
        """匹配斜杠命令"""
        if not user_input.startswith("/"):
            return None

        command = user_input.split()[0][1:]  # 去掉 /
        command = command.lower()

        for skill in self._skill_registry.get_all():
            slash_cmd = skill.config.get("triggers", {}).get("slash_command", "")
            if slash_cmd and slash_cmd.lstrip("/") == command:
                return TriggerMatch(
                    trigger_type=TriggerType.SLASH_COMMAND,
                    skill_id=skill.id,
                    confidence=1.0,  # 显式命令最高置信度
                    extracted_params={"command": command},
                    match_reason=f"显式命令: /{command}"
                )

        return None

    async def _match_keywords(
        self,
        user_input: str,
        context: Dict[str, Any],
    ) -> List[TriggerMatch]:
        """关键词匹配"""
        matches = []
        input_lower = user_input.lower()

        for skill in self._skill_registry.get_all():
            keywords = skill.config.get("triggers", {}).get("intent_keywords", [])

            for keyword in keywords:
                if keyword.lower() in input_lower:
                    confidence = self._calculate_keyword_confidence(
                        keyword, user_input
                    )
                    matches.append(TriggerMatch(
                        trigger_type=TriggerType.INTENT_KEYWORD,
                        skill_id=skill.id,
                        confidence=confidence,
                        extracted_params={},
                        match_reason=f"关键词匹配: '{keyword}'"
                    ))
                    break  # 每个技能只匹配一次

        return matches

    def _calculate_keyword_confidence(
        self,
        keyword: str,
        user_input: str,
    ) -> float:
        """计算关键词匹配置信度"""
        base_confidence = 0.7

        # 精确匹配加分
        if keyword.lower() == user_input.lower():
            return 1.0

        # 关键词在输入中的位置
        position = user_input.lower().find(keyword.lower())

        # 在开头 = 更高的意图
        if position == 0:
            return min(0.95, base_confidence + 0.2)

        # 在末尾 = 较高的意图
        if position == len(user_input) - len(keyword):
            return min(0.9, base_confidence + 0.15)

        # 在中间 = 基础置信度
        return base_confidence

    async def _match_context(
        self,
        user_input: str,
        context: Dict[str, Any],
    ) -> List[TriggerMatch]:
        """上下文模式匹配"""
        matches = []

        for skill in self._skill_registry.get_all():
            conditions = skill.config.get("triggers", {}).get(
                "context_conditions", {}
            )

            # 检查是否需要患者数据
            if conditions.get("requires_patient_data"):
                if context.get("patient_id"):
                    # 有患者数据，增加置信度
                    matches.append(TriggerMatch(
                        trigger_type=TriggerType.CONTEXT_PATTERN,
                        skill_id=skill.id,
                        confidence=0.5,
                        extracted_params={},
                        match_reason="上下文: 有患者数据"
                    ))

        return matches

    async def _match_semantic(
        self,
        user_input: str,
        context: Dict[str, Any],
    ) -> List[TriggerMatch]:
        """语义相似度匹配（预留接口）"""
        # TODO: 集成嵌入模型进行语义匹配
        return []
```

### 2.3 参数提取器

```python
# src/domain/shared/services/parameter_extractor.py

class ParameterExtractor:
    """
    参数提取器

    从用户输入中提取技能执行所需的参数
    """

    def __init__(self):
        self._patterns = {}

    def load_skill_patterns(self, skill):
        """加载技能的参数提取模式"""
        extraction_config = skill.config.get("extraction", [])

        for field_config in extraction_config:
            field = field_config["field"]
            patterns = field_config.get("patterns", [])
            self._patterns[field] = patterns

    def extract(
        self,
        user_input: str,
        skill,
    ) -> Dict[str, Any]:
        """
        从用户输入提取参数

        Args:
            user_input: 用户输入
            skill: 技能配置

        Returns:
            提取的参数字典
        """
        params = {}
        extraction_config = skill.config.get("extraction", [])

        for field_config in extraction_config:
            field = field_config["field"]
            patterns = field_config.get("patterns", [])
            field_type = field_config.get("type", "string")

            for pattern in patterns:
                match = re.search(pattern, user_input)
                if match:
                    value = match.groupdict().get(field)
                    if value:
                        # 类型转换
                        params[field] = self._convert_type(value, field_type)
                        break

        return params

    def _convert_type(self, value: str, target_type: str) -> Any:
        """类型转换"""
        if target_type == "integer":
            return int(value)
        elif target_type == "float":
            return float(value)
        elif target_type == "boolean":
            return value.lower() in ["true", "yes", "1"]
        else:
            return value
```

---

## 3. 技能执行引擎

### 3.1 执行流程

```python
# src/domain/shared/services/skill_executor.py

class SkillExecutionEngine:
    """
    技能执行引擎

    负责:
    1. 加载技能配置
    2. 提取执行参数
    3. 执行规则评估
    4. 调用 LLM 生成响应
    5. 返回结构化结果
    """

    def __init__(
        self,
        session: AsyncSession,
        rule_engine: RuleEngine,
        llm_client: Any,
    ):
        self._session = session
        self._rule_engine = rule_engine
        self._llm_client = llm_client
        self._parameter_extractor = ParameterExtractor()

    async def execute(
        self,
        skill_match: TriggerMatch,
        user_input: str,
        context: Dict[str, Any],
    ) -> SkillExecutionResult:
        """
        执行技能

        Args:
            skill_match: 技能匹配结果
            user_input: 用户原始输入
            context: 执行上下文

        Returns:
            技能执行结果
        """
        # 1. 加载技能配置
        skill = await self._load_skill(skill_match.skill_id)

        # 2. 提取参数
        params = self._parameter_extractor.extract(user_input, skill)
        params.update(skill_match.extracted_params)

        # 3. 检查前置条件
        if not await self._check_preconditions(skill, context):
            return SkillExecutionResult(
                success=False,
                error="前置条件不满足",
                skill_id=skill.id,
            )

        # 4. 规则评估（如果启用）
        rule_results = []
        rule_config = skill.config.get("rule_enhancement", {})

        if rule_config.get("enabled"):
            rule_context = RuleExecutionContext(
                patient_id=context.get("patient_id", "unknown"),
                input_data=params,
                consultation_id=context.get("consultation_id"),
                skill_id=skill.id,
            )
            rule_results = await self._rule_engine.evaluate_rules(
                rule_context,
                categories=rule_config.get("categories"),
                disease_code=rule_config.get("disease_code"),
            )

        # 5. 构建增强提示词
        prompt = self._build_prompt(skill, user_input, params, rule_results)

        # 6. 调用 LLM
        llm_response = await self._llm_client.generate(
            prompt=prompt,
            context={
                "skill": skill.name,
                "params": params,
                "rule_results": [r.to_dict() for r in rule_results],
            }
        )

        # 7. 解析输出
        output = self._parse_output(llm_response, skill)

        # 8. 记录执行历史
        await self._log_execution(skill, params, rule_results, output)

        return SkillExecutionResult(
            success=True,
            skill_id=skill.id,
            response=llm_response,
            structured_output=output,
            rule_results=rule_results,
            extracted_params=params,
        )

    def _build_prompt(
        self,
        skill,
        user_input: str,
        params: Dict,
        rule_results: List,
    ) -> str:
        """构建增强提示词"""
        template = skill.config.get("prompt_template", "{{user_input}}")

        # 使用 Jinja2 模板
        from jinja2 import Template

        jinja_template = Template(template)

        return jinja_template.render(
            user_input=user_input,
            params=params,
            rule_results=rule_results,
        )
```

---

## 4. 技能文件组织结构

```
medical_agent/
├── skills/                        # 技能定义目录
│   ├── basic/                     # Layer 1: 基础工具
│   │   ├── data_parser.yml
│   │   ├── format_helper.yml
│   │   └── validator.yml
│   │
│   ├── domain/                    # Layer 2: 领域技能
│   │   ├── hypertension_assessment.yml
│   │   ├── diabetes_assessment.yml
│   │   ├── dyslipidemia_assessment.yml
│   │   ├── gout_assessment.yml
│   │   └── obesity_assessment.yml
│   │
│   ├── composite/                 # Layer 3: 组合技能
│   │   ├── comprehensive_checkup.yml
│   │   ├── chronic_management.yml
│   │   └── emergency_triage.yml
│   │
│   └── skill_registry.yml         # 技能注册表
│
├── src/domain/shared/services/
│   ├── skill_trigger.py           # 触发引擎
│   ├── skill_executor.py          # 执行引擎
│   ├── skill_registry.py          # 技能注册
│   └── parameter_extractor.py     # 参数提取
│
└── src/interface/api/routes/
    └── skills_v2.py                # 新版技能 API
```

---

## 5. API 设计

### 5.1 技能触发 API

```python
@router.post("/api/v2/skills/trigger")
async def trigger_skill(
    request: SkillTriggerRequest,
) -> SkillTriggerResponse:
    """
    技能触发端点

    接收用户输入，自动匹配并执行合适的技能
    """
    engine = SkillTriggerEngine(skill_registry)

    # 匹配技能
    matches = await engine.match_skills(
        user_input=request.user_input,
        context=request.context,
    )

    if not matches:
        return SkillTriggerResponse(
            matched=False,
            message="未找到匹配的技能",
        )

    # 执行最高置信度的技能
    executor = SkillExecutionEngine(session, rule_engine, llm)
    result = await executor.execute(
        skill_match=matches[0],
        user_input=request.user_input,
        context=request.context,
    )

    return SkillTriggerResponse(
        matched=True,
        skill_id=matches[0].skill_id,
        confidence=matches[0].confidence,
        execution_result=result,
    )
```

### 5.2 技能列表 API

```python
@router.get("/api/v2/skills")
async def list_skills(
    layer: Optional[str] = None,
    category: Optional[str] = None,
    enabled_only: bool = True,
) -> List[SkillInfo]:
    """
    列出可用技能

    支持按层级、分类过滤
    """
    skills = skill_registry.get_all()

    if layer:
        skills = [s for s in skills if s.layer == layer]

    if category:
        skills = [s for s in skills if s.category == category]

    if enabled_only:
        skills = [s for s in skills if s.enabled]

    return [
        SkillInfo(
            id=s.id,
            name=s.name,
            display_name=s.display_name,
            description=s.description,
            layer=s.layer,
            category=s.category,
            triggers=s.config.get("triggers", {}),
        )
        for s in skills
    ]
```

---

## 6. 实施计划

### 阶段 1: 基础设施 (3-5天)
1. ✅ 创建技能文件结构
2. ✅ 实现 YAML 技能加载器
3. ✅ 实现技能注册表
4. ✅ 单元测试

### 阶段 2: 触发引擎 (2-3天)
1. ✅ 实现关键词匹配
2. ✅ 实现参数提取
3. ✅ 实现置信度计算
4. ✅ 集成测试

### 阶段 3: 执行引擎 (3-4天)
1. ✅ 实现技能执行流程
2. ✅ 集成规则引擎
3. ✅ 实现 Jinja2 模板渲染
4. ✅ 端到端测试

### 阶段 4: 迁移现有技能 (2-3天)
1. ✅ 将 8 个生产技能转换为 YAML
2. ✅ 测试兼容性
3. ✅ 性能优化

### 阶段 5: 前端集成 (2-3天)
1. ✅ 技能配置 UI
2. ✅ 技能测试面板
3. ✅ 执行历史查看

---

## 7. 示例：完整技能定义

```yaml
# skills/domain/hypertension_assessment.yml

name: hypertension_assessment
display_name: "高血压评估"
version: "2.0.0"
category: health_assessment
layer: domain
enabled: true
priority: 10

# 触发配置
triggers:
  slash_command: "/bp"
  intent_keywords:
    - "血压"
    - "高血压"
    - "收缩压"
    - "舒张压"
  context_conditions:
    requires_patient_data: false
    min_confidence: 0.5

# 规则增强
rule_enhancement:
  enabled: true
  categories:
    - diagnosis
    - risk_assessment
  disease_code: hypertension
  use_vital_signs: true
  use_risk_scoring: true

# 提示词模板
prompt_template: |
  # 角色
  你是一个专业的高血压评估专家，具有丰富的临床经验。

  # 任务
  根据用户提供的血压数据，进行专业评估并提供健康建议。

  # 用户输入
  {{user_input}}

  # 提取的数据
  {% if params.systolic and params.diastolic %}
  - 收缩压: {{params.systolic}} mmHg
  - 舒张压: {{params.diastolic}} mmHg
  {% endif %}
  {% if params.age %}
  - 年龄: {{params.age}} 岁
  {% endif %}

  # 临床规则评估结果
  {% if rule_results %}
  {% for rule in rule_results if rule.matched %}
  - {{rule.rule_name}} (置信度: {{rule.confidence}})
  {% endfor %}
  {% endif %}

  # 输出要求
  请提供:
  1. 血压水平诊断（正常/正常高值/高血压1级/2级/3级）
  2. 当前风险评估
  3. 具体的健康建议
  4. 是否需要就医的建议

  # 注意事项
  - 回答要专业但不失亲和力
  - 避免使用过于专业的术语
  - 重要建议要明确突出

# 参数提取
extraction:
  - field: systolic
    patterns:
      - "(?P<systolic>\\d+)[/\\/](?P<diastolic>\\d+)"
      - "收缩压\\s*[:：]?\\s*(?P<systolic>\\d+)"
    type: integer
    required: true

  - field: diastolic
    patterns:
      - "(?P<systolic>\\d+)[/\\/](?P<diastolic>\\d+)"
      - "舒张压\\s*[:：]?\\s*(?P<diastolic>\\d+)"
    type: integer
    required: true

  - field: age
    patterns:
      - "(?P<age>\\d+)\\s*岁"
      - "年龄\\s*[:：]?\\s*(?P<age>\\d+)"
    type: integer

# 输出格式
output:
  type: structured
  schema:
    diagnosis:
      type: string
      description: "血压水平诊断"
    risk_level:
      type: enum
      values: [normal, elevated, high_stage_1, high_stage_2, high_stage_3]
    recommendations:
      type: array
      items:
        type: string
    needs_medical_attention:
      type: boolean

# 权限与限流
security:
  requires_auth: false
  max_requests_per_minute: 20
  allowed_scopes:
    - patient:read
    - assessment:write

# 示例
examples:
  - input: "我血压150/95"
    expected_diagnosis: "高血压1级"
  - input: "收缩压135，舒张压85"
    expected_diagnosis: "正常高值"
```

---

## 8. 总结

本方案实现了类似 Claude Code 的技能系统，具有以下特点：

| 特性 | Claude Code 技能 | 本方案实现 |
|------|-----------------|-----------|
| 声明式定义 | ✅ | ✅ YAML 配置 |
| 斜杠命令 | ✅ | ✅ /bp, /sugar |
| 关键词触发 | ✅ | ✅ 意图匹配 |
| 参数提取 | ✅ | ✅ 正则 + NER |
| 组合技能 | ✅ | ✅ Workflow 定义 |
| 权限控制 | ✅ | ✅ Scope-based |
| 执行追踪 | ✅ | ✅ 历史记录 |
| 渐进披露 | - | ✅ Layer 设计 |

是否开始实施此方案？
