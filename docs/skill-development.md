# Skill 开发指南

本文档介绍如何使用 DSPy 框架开发和部署自定义 Skills。

## 目录

- [Skill 架构概述](#skill-架构概述)
- [开发环境设置](#开发环境设置)
- [创建第一个 Skill](#创建第一个-skill)
- [Skill 配置](#skill-配置)
- [高级特性](#高级特性)
- [测试和调试](#测试和调试)
- [部署流程](#部署流程)
- [最佳实践](#最佳实践)

## Skill 架构概述

### 什么是 Skill？

Skill 是 Medical Agent 系统的基本功能单元，封装了特定的健康评估或处理能力。每个 Skill：

- 使用 DSPy Signature 定义输入输出
- 通过 LLM 执行复杂推理
- 可动态配置和热重载
- 支持版本管理和回滚

### Skill 类型

| 类型 | 描述 | 示例 |
|------|------|------|
| 评估类 | 评估健康指标 | HypertensionAssessment |
| 预测类 | 预测疾病风险 | DiabetesRiskPrediction |
| 处方类 | 生成健康处方 | DietPrescription |
| 工具类 | 调用外部服务 | TriageGuidanceSkill |

### 架构组件

```
┌─────────────────────────────────────────┐
│           Skill Registry                │
│  - 动态加载 Skill                       │
│  - Skill 实例管理                       │
│  - 版本控制                             │
└─────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────┐
│           Base Skill                    │
│  - DSPy Signature                       │
│  - LLM 集成                             │
│  - 执行引擎                             │
└─────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────┐
│         具体实现 (Skills)                │
│  - HypertensionSkill                    │
│  - DiabetesSkill                        │
│  - DietPrescriptionSkill                │
└─────────────────────────────────────────┘
```

## 开发环境设置

### 1. 安装依赖

```bash
# 安装 DSPy
pip install dspy-ai

# 安装 DSPy 扩展
pip install dpy-async

# 安装开发工具
pip install pytest pytest-asyncio pytest-cov
```

### 2. 项目结构

```
src/infrastructure/dspy/skills/
├── __init__.py
├── base_skill.py          # Base Skill 类
├── skill_registry.py       # Skill 注册表
├── skill_factory.py        # Skill 工厂
└── implementations/
    ├── __init__.py
    ├── four_highs.py       # 四高一重 Skills
    ├── prescription.py      # 处方 Skills
    └── tools.py            # 工具 Skills
```

### 3. 环境变量

```bash
# .env
LLM_MODEL=glm-5
LLM_API_KEY=your_api_key
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Skill 配置
SKILL_PATH=src/infrastructure/dspy/skills
SKILL_CACHE_ENABLED=true
SKILL_HOT_RELOAD=true
```

## 创建第一个 Skill

### 基础模板

```python
"""
我的第一个 Skill 实现
"""
import dspy
from src.infrastructure.dspy.base_skill import BaseSkill, SkillConfig
from src.infrastructure.llm import LLMFactory


class MySkillSignature(dspy.Signature):
    """定义 Skill 的输入输出"""
    def __init__(self):
        self.input = dspy.InputField(desc="用户问题")
        self.output = dspy.OutputField(desc="AI 回答")


class MySkill(BaseSkill):
    """自定义 Skill 实现"""

    def __init__(self, config: SkillConfig = None):
        super().__init__(
            name="my_skill",
            description="我的第一个 Skill",
            version="1.0.0",
            config=config or SkillConfig()
        )

        # 设置签名类
        self.signature_class = MySkillSignature

        # 创建 LLM
        self.llm = LLMFactory.create_llm()

        # 初始化 DSPy 模块
        self.module = dspy.Predict(MySkillSignature)
        self.module.llm = self.llm

    async def execute(self, **kwargs) -> SkillResult:
        """执行 Skill"""
        # 验证输入
        validated_input = self.validate_input(kwargs)

        # 执行推理
        result = await self._run_inference(validated_input)

        # 后处理
        processed_result = self.post_process(result)

        return SkillResult(
            success=True,
            data=processed_result,
            execution_time=self.get_execution_time()
        )
```

### 完整示例：胆固醇评估 Skill

```python
"""
胆固醇评估 Skill
"""
import dspy
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.infrastructure.dspy.base_skill import (
    BaseSkill,
    SkillConfig,
    SkillResult,
)
from src.infrastructure.dspy.signatures.four_highs import (
    LipidProfileAssessmentSignature,
)


class CholesterolLevel(Enum):
    """胆固醇水平"""
    NORMAL = "normal"
    BORDERLINE_HIGH = "borderline_high"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class CholesterolAssessment:
    """胆固醇评估结果"""
    total_cholesterol_level: CholesterolLevel
    ldl_level: CholesterolLevel
    hdl_level: CholesterolLevel
    triglycerides_level: CholesterolLevel
    overall_risk: str
    recommendations: list[str]


class CholesterolSkill(BaseSkill):
    """胆固醇评估 Skill"""

    # Skill 元数据
    name = "cholesterol_assessment"
    description = "根据血脂指标评估胆固醇水平和心血管风险"
    category = "four_highs"
    version = "1.0.0"
    keywords = ["胆固醇", "血脂", "TC", "LDL-C", "HDL-C", "甘油三酯"]

    def __init__(self, config: SkillConfig = None):
        super().__init__(
            name=self.name,
            description=self.description,
            category=self.category,
            version=self.version,
            keywords=self.keywords,
            config=config,
        )
        self.signature_class = LipidProfileAssessmentSignature

    async def execute(
        self,
        lipid_profile: Dict[str, float],
        patient_data: Optional[Dict[str, Any]] = None,
    ) -> SkillResult:
        """
        执行胆固醇评估

        Args:
            lipid_profile: 血脂指标
                - total_cholesterol: 总胆固醇
                - ldl_c: 低密度脂蛋白胆固醇
                - hdl_c: 高密度脂蛋白胆固醇
                - triglycerides: 甘油三酯
            patient_data: 患者信息（可选）

        Returns:
            SkillResult: 评估结果
        """
        # 验证输入
        validated = self._validate_input(lipid_profile)

        if not validated["valid"]:
            return SkillResult(
                success=False,
                error=f"输入验证失败: {validated['errors']}"
            )

        # 执行评估
        assessment = await self._assess(validated["data"])

        # 生成建议
        recommendations = self._generate_recommendations(assessment)

        return SkillResult(
            success=True,
            data={
                "assessment": assessment,
                "recommendations": recommendations,
            },
            metadata={
                "patient_age": patient_data.get("age") if patient_data else None,
                "patient_gender": patient_data.get("gender") if patient_data else None,
            }
        )

    def _validate_input(self, lipid_profile: Dict[str, float]) -> Dict:
        """验证输入数据"""
        errors = []

        # 检查必需字段
        required_fields = ["total_cholesterol", "ldl_c", "hdl_c", "triglycerides"]
        for field in required_fields:
            if field not in lipid_profile:
                errors.append(f"缺少必需字段: {field}")
            elif not isinstance(lipid_profile[field], (int, float)):
                errors.append(f"{field} 必须是数字")

        # 检查数值范围
        if "total_cholesterol" in lipid_profile:
            tc = lipid_profile["total_cholesterol"]
            if tc < 2 or tc > 20:
                errors.append("总胆固醇应在 2-20 mmol/L 之间")

        if errors:
            return {"valid": False, "errors": errors}

        return {"valid": True, "data": lipid_profile}

    async def _assess(self, lipid_profile: Dict[str, float]) -> CholesterolAssessment:
        """执行评估逻辑"""
        # 使用 DSPy 进行智能评估
        prompt = self._build_assessment_prompt(lipid_profile)

        # 调用 LLM
        result = await self._llm.apredict(
            prompt=prompt,
            temperature=0.3,  # 降低温度以获得更一致的结果
        )

        # 解析结果
        return self._parse_assessment_result(result, lipid_profile)

    def _build_assessment_prompt(self, lipid_profile: Dict[str, float]) -> str:
        """构建评估提示词"""
        return f"""请根据以下血脂指标进行评估：

总胆固醇: {lipid_profile['total_cholesterol']} mmol/L
低密度脂蛋白胆固醇 (LDL-C): {lipid_profile['ldl_c']} mmol/L
高密度脂蛋白胆固醇 (HDL-C): {lipid_profile['hdl_c']} mmol/L
甘油三酯: {lipid_profile['triglycerides']} mmol/L

请提供：
1. 总胆固醇水平评估
2. LDL-C 水平评估
3. HDL-C 水平评估
4. 甘油三酯水平评估
5. 整体心血管风险评估
6. 具体建议

以 JSON 格式返回结果。"""

    def _parse_assessment_result(
        self,
        llm_result: str,
        lipid_profile: Dict[str, float]
    ) -> CholesterolAssessment:
        """解析 LLM 评估结果"""
        # 这里简化处理，实际应该解析 JSON
        return CholesterolAssessment(
            total_cholesterol_level=self._classify_total_cholesterol(
                lipid_profile["total_cholesterol"]
            ),
            ldl_level=self._classify_ldl(lipid_profile["ldl_c"]),
            hdl_level=self._classify_hdl(lipid_profile["hdl_c"]),
            triglycerides_level=self._classify_triglycerides(
                lipid_profile["triglycerides"]
            ),
            overall_risk="medium",  # 实际应从 LLM 结果解析
            recommendations=[
                "建议低脂饮食",
                "增加有氧运动",
            ],
        )

    def _classify_total_cholesterol(self, value: float) -> CholesterolLevel:
        """分类总胆固醇水平"""
        if value < 5.2:
            return CholesterolLevel.NORMAL
        elif value < 6.2:
            return CholesterolLevel.BORDERLINE_HIGH
        else:
            return CholesterolLevel.HIGH

    def _classify_ldl(self, value: float) -> CholesterolLevel:
        """分类 LDL-C 水平"""
        if value < 3.4:
            return CholesterolLevel.NORMAL
        elif value < 4.1:
            return CholesterolLevel.BORDERLINE_HIGH
        elif value < 4.9:
            return CholesterolLevel.HIGH
        else:
            return CholesterolLevel.VERY_HIGH

    def _classify_hdl(self, value: float) -> CholesterolLevel:
        """分类 HDL-C 水平（注意：HDL 越高越好）"""
        if value >= 1.0:
            return CholesterolLevel.NORMAL
        else:
            return CholesterolLevel.HIGH  # HDL 低也是风险

    def _classify_triglycerides(self, value: float) -> CholesterolLevel:
        """分类甘油三酯水平"""
        if value < 1.7:
            return CholesterolLevel.NORMAL
        elif value < 2.3:
            return CholesterolLevel.BORDERLINE_HIGH
        else:
            return CholesterolLevel.HIGH

    def _generate_recommendations(
        self,
        assessment: CholesterolAssessment
    ) -> list[str]:
        """生成健康建议"""
        recommendations = []

        if assessment.ldl_level != CholesterolLevel.NORMAL:
            recommendations.append("减少饱和脂肪酸摄入")
            recommendations.append("增加可溶性纤维摄入")

        if assessment.hdl_level != CholesterolLevel.NORMAL:
            recommendations.append("增加有氧运动")
            recommendations.append("戒烟限酒")

        if assessment.triglycerides_level != CholesterolLevel.NORMAL:
            recommendations.append("控制精制碳水化合物")
            recommendations.append("限制酒精摄入")

        if not recommendations:
            recommendations.append("继续保持健康生活方式")

        return recommendations
```

### 注册 Skill

```python
# src/infrastructure/dspy/skills/implementations/four_highs.py

from src.infrastructure.dspy.skill_registry import SkillRegistry

# 自动注册
SkillRegistry.register(CholesterolSkill)
```

## Skill 配置

### 提示词模板

每个 Skill 可以配置自定义提示词：

```python
class MySkillSignature(dspy.Signature):
    def __init__(self):
        self.input = dspy.InputField(desc="输入")
        self.output = dspy.OutputField(desc="输出")

    # 设置提示词模板
    @staticmethod
    def get_prompt_template():
        return """请根据以下输入内容进行分析：

{input}

要求：
1. 分析准确
2. 结果清晰
3. 提供建议

输出为 JSON 格式。"""
```

### 动态提示词

从数据库加载提示词：

```python
from src.application.services.skill_prompt_template_service import (
    SkillPromptTemplateService,
)

async def load_prompt(self, skill_id: str):
    templates = await SkillPromptTemplateService.load_prompt_templates(skill_id)
    if "user" in templates:
        self.signature_class.prompt_template = templates["user"].content
```

### 模型配置

```python
from src.infrastructure.llm import ModelProvider

config = SkillConfig(
    model=ModelProvider.ANTHROPIC,
    model_name="glm-5",
    temperature=0.7,
    max_tokens=2000,
    timeout=30,
    max_retries=3,
)
```

## 高级特性

### 1. 多步骤推理

```python
import dspy

class MultiStepSignature(dspy.Signature):
    """多步骤签名"""

    # 步骤 1: 分析
    analyze = dspy.InputField(desc="待分析内容")
    analysis = dspy.OutputField(desc="分析结果")

    # 步骤 2: 评估
    assess = dspy.InputField(desc="待评估内容")
    assessment = dspy.OutputField(desc="评估结果")

    # 步骤 3: 建议
    recommend = dspy.InputField(desc="待建议内容")
    recommendation = dspy.OutputField(desc="建议结果")


class MultiStepSkill(BaseSkill):
    """多步骤 Skill"""

    async def execute(self, input_data: str) -> SkillResult:
        # 步骤 1: 分析
        analyze_result = await self._run_analyze(input_data)

        # 步骤 2: 评估
        assess_result = await self._run_assess(analyze_result)

        # 步骤 3: 建议
        recommend_result = await self._run_recommend(assess_result)

        return SkillResult(
            success=True,
            data={
                "analysis": analyze_result,
                "assessment": assess_result,
                "recommendation": recommend_result,
            }
        )
```

### 2. 工具调用 (Tool Use)

```python
class ToolSkill(BaseSkill):
    """使用外部工具的 Skill"""

    async def execute(self, query: str) -> SkillResult:
        # 准备工具定义
        tools = [
            {
                "name": "database_search",
                "description": "搜索数据库中的患者记录",
                "parameters": {
                    "patient_id": "string",
                    "date_range": "object",
                },
            },
            {
                "name": "knowledge_search",
                "description": "搜索知识库中的医疗指南",
                "parameters": {
                    "query": "string",
                    "category": "string",
                },
            },
        ]

        # 使用 Function Calling
        result = await self._llm.bind_tools(tools).call(
            prompt=query,
            tools=tools,
        )

        # 执行工具调用
        tool_results = await self._execute_tool_calls(result.tool_calls)

        # 生成最终响应
        final_response = await self._generate_response(query, tool_results)

        return SkillResult(success=True, data=final_response)
```

### 3. 流式输出

```python
class StreamingSkill(BaseSkill):
    """支持流式输出的 Skill"""

    async def execute_stream(self, input_data: str):
        """流式执行 Skill"""
        async for token in self._llm.astream(prompt=input_data):
            yield {
                "type": "token",
                "content": token,
            }

        yield {
            "type": "done",
            "full_response": self.get_full_response(),
        }
```

## 测试和调试

### 单元测试

```python
import pytest
from src.infrastructure.dspy.skills.implementations.four_highs import CholesterolSkill

@pytest.mark.asyncio
async def test_cholesterol_skill_normal():
    """测试正常胆固醇评估"""
    skill = CholesterolSkill()

    result = await skill.execute(
        lipid_profile={
            "total_cholesterol": 4.8,
            "ldl_c": 2.8,
            "hdl_c": 1.4,
            "triglycerides": 1.2,
        }
    )

    assert result.success
    assert result.data["assessment"].total_cholesterol_level == "normal"
    assert len(result.data["recommendations"]) > 0

@pytest.mark.asyncio
async def test_cholesterol_skill_invalid_input():
    """测试无效输入"""
    skill = CholesterolSkill()

    result = await skill.execute(
        lipid_profile={
            "total_cholesterol": "invalid",  # 错误类型
        }
    )

    assert not result.success
    assert "输入验证失败" in result.error
```

### 集成测试

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_cholesterol_skill_integration():
    """集成测试"""
    from src.infrastructure.dspy.skill_registry import SkillRegistry

    # 加载 Skill
    skill_info = SkillRegistry.get_skill_info("cholesterol_assessment")
    skill = skill_info.skill_class()

    # 执行
    result = await skill.execute(
        lipid_profile={
            "total_cholesterol": 6.5,
            "ldl_c": 4.2,
            "hdl_c": 1.0,
            "triglycerides": 2.5,
        },
        patient_data={"age": 50, "gender": "male"}
    )

    assert result.success
```

### 调试工具

```python
# 启用调试日志
import logging

logging.basicConfig(level=logging.DEBUG)

# Skill 调试
from src.infrastructure.dspy.base_skill import BaseSkill

class DebugSkill(BaseSkill):
    """带调试输出的 Skill"""

    async def execute(self, **kwargs):
        # 打印输入
        self.logger.debug(f"输入参数: {kwargs}")

        # 执行
        result = await super().execute(**kwargs)

        # 打印输出
        self.logger.debug(f"执行结果: {result}")

        return result
```

## 部署流程

### 1. 开发阶段

```bash
# 创建 Skill
# 编写代码
# 单元测试
pytest tests/unit/skills/test_my_skill.py
```

### 2. 测试阶段

```python
# 集成测试
pytest tests/integration/skills/test_my_skill.py

# E2E 测试
pytest tests/e2e/test_skill_routing.py
```

### 3. 注册 Skill

```sql
-- 插入 Skill 记录
INSERT INTO skills (
    id,
    name,
    category,
    description,
    version,
    enabled
) VALUES (
    'my_skill',
    'My Skill',
    'custom',
    '自定义 Skill 描述',
    '1.0.0',
    true
);

-- 插入提示词模板
INSERT INTO skill_prompts (
    skill_id,
    prompt_type,
    content,
    version
) VALUES (
    'my_skill',
    'user',
    '请根据以下输入...',
    '1.0.0'
);
```

### 4. 热重载

```python
# Skill Registry 会自动检测新版本
from src.infrastructure.dspy.skill_registry import SkillRegistry

# 刷新注册表
SkillRegistry.reload()

# 获取 Skill
skill = SkillRegistry.get_skill("my_skill")
```

## 最佳实践

### 1. 输入验证

```python
def validate_input(self, data: Dict) -> Dict:
    """严格验证输入"""
    # 1. 检查必需字段
    # 2. 验证数据类型
    # 3. 验证数值范围
    # 4. 检查业务规则
    pass
```

### 2. 错误处理

```python
async def execute(self, **kwargs) -> SkillResult:
    try:
        # 执行逻辑
        result = await self._run(**kwargs)
        return SkillResult(success=True, data=result)

    except ValueError as e:
        return SkillResult(
            success=False,
            error=f"输入错误: {str(e)}"
        )

    except Exception as e:
        self.logger.error(f"执行失败: {e}")
        return SkillResult(
            success=False,
            error="内部错误"
        )
```

### 3. 性能优化

```python
# 缓存 LLM 结果
from functools import lru_cache

class CachedSkill(BaseSkill):
    @lru_cache(maxsize=100)
    async def _cached_llm_call(self, prompt_hash: str):
        return await self._llm.apredict(prompt=prompt)
```

### 4. 提示词优化

使用 DSPy Teleprompter 优化提示词：

```python
from src.application.services.skill_optimizer_service import (
    SkillOptimizer,
    OptimizationConfig,
)

optimizer = SkillOptimizer("my_skill")

config = OptimizationConfig(
    max_iterations=5,
    target_score=0.85,
    examples=training_examples,
)

result = await optimizer.optimize(config)
```

### 5. 文档化

```python
class MySkill(BaseSkill):
    """
    我的 Skill 描述

    功能：
    - 功能 1
    - 功能 2

    输入：
    - input1: 描述
    - input2: 描述

    输出：
    - output1: 描述

    示例：
        >>> skill = MySkill()
        >>> result = await skill.execute(input1="test")
    """
    pass
```

## 附录

### A. Skill 模板

```python
"""
Skill 模板
"""
import dspy
from src.infrastructure.dspy.base_skill import BaseSkill, SkillConfig, SkillResult
from typing import Dict, Any, Optional


class TemplateSkillSignature(dspy.Signature):
    """Skill 签名定义"""
    def __init__(self):
        self.input = dspy.InputField(desc="输入描述")
        self.output = dspy.OutputField(desc="输出描述")


class TemplateSkill(BaseSkill):
    """Skill 实现"""

    # 元数据
    name = "template_skill"
    description = "Skill 描述"
    category = "custom"
    version = "1.0.0"
    keywords = ["关键词1", "关键词2"]

    def __init__(self, config: SkillConfig = None):
        super().__init__(
            name=self.name,
            description=self.description,
            category=self.category,
            version=self.version,
            keywords=self.keywords,
            config=config,
        )
        self.signature_class = TemplateSkillSignature

    async def execute(self, **kwargs) -> SkillResult:
        """执行 Skill"""
        # 1. 验证输入
        validated = self.validate_input(kwargs)

        # 2. 执行推理
        result = await self._run_inference(validated)

        # 3. 后处理
        processed = self.post_process(result)

        return SkillResult(
            success=True,
            data=processed,
        )

    def validate_input(self, data: Dict) -> Dict:
        """验证输入"""
        # 实现验证逻辑
        return {"valid": True, "data": data}

    async def _run_inference(self, data: Dict) -> Any:
        """执行推理"""
        # 实现推理逻辑
        pass

    def post_process(self, result: Any) -> Any:
        """后处理结果"""
        # 实现后处理逻辑
        return result
```

### B. 相关资源

- [DSPy 文档](https://dspy-docs.vercel.app/)
- [LLM 提供商文档](https://docs.anthropic.com/)
- [Skill 架构](../src/infrastructure/dspy/)
- [测试示例](../../tests/unit/skills/)
