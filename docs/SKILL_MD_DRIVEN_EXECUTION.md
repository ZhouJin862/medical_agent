# SKILL.md 驱动执行架构

## 概述

采用 **SKILL.md 驱动**的技能执行架构，将 SKILL.md 作为工作流定义的单一配置源，通过通用执行器解析并执行其中定义的步骤。

---

## 架构对比

### 传统方式：main.py 驱动

```
┌─────────────────────────────────────────────┐
│              skills/hypertension/            │
├─────────────────────────────────────────────┤
│  SKILL.md (文档)                             │
│  - 描述技能功能                              │
│  - 定义工作流步骤                           │
├─────────────────────────────────────────────┤
│  scripts/main.py (执行入口)                  │
│  - 硬编码执行逻辑                            │
│  - 重复定义工作流                            │
│  - 与 SKILL.md 不同步                         │
├─────────────────────────────────────────────┤
│  scripts/health_data_validator.py            │
│  scripts/risk_calculator.py                  │
│  scripts/template_manager.py                 │
└─────────────────────────────────────────────┘

问题：
- SKILL.md 和 main.py 内容重复
- 修改工作流需要改两个文件
- main.py 变成维护瓶颈
```

### 新方式：SKILL.md 驱动

```
┌─────────────────────────────────────────────┐
│              skills/hypertension/            │
├─────────────────────────────────────────────┤
│  SKILL.md (单一配置源)                       │
│  - 描述技能功能                              │
│  - 定义工作流步骤 ✓                         │
│  - 指定脚本和参数                            │
├─────────────────────────────────────────────┤
│  SkillWorkflowExecutor (通用执行器)           │
│  - 解析 SKILL.md 工作流                        │
│  - 依次执行定义的脚本                         │
│  - 传递数据并收集结果                         │
├─────────────────────────────────────────────┤
│  scripts/health_data_validator.py            │
│  scripts/risk_calculator.py                  │
│  scripts/template_manager.py                 │
└─────────────────────────────────────────────┘

优势：
- SKILL.md 是唯一的配置源
- 执行器完全通用
- 脚本松耦合，可复用
- 易于维护和扩展
```

---

## SKILL.md 工作流定义格式

```markdown
## 操作步骤

### 步骤1：数据验证
```bash
python scripts/health_data_validator.py --input <健康数据文件>
```

### 步骤2：血压风险评估
```bash
python scripts/risk_calculator.py --input validated_data.json --focus hypertension
```

### 步骤3：报告生成
```bash
python scripts/template_manager.py --template report --input risk_assessment_data.json
```
```

**格式说明**：
- 每个步骤以 `### 步骤N：标题` 开始
- 包含一个 bash 代码块，指定要执行的 Python 脚本
- 参数使用占位符（如 `<健康数据文件>`），执行时自动替换

---

## 执行器实现

### SkillWorkflowParser

**职责**：解析 SKILL.md

```python
class SkillWorkflowParser:
    def parse_frontmatter(self) -> Dict[str, Any]:
        """解析 YAML frontmatter（技能元数据）"""

    def parse_execution_steps(self) -> List[ExecutionStep]:
        """解析操作步骤"""
        # 提取 "## 操作步骤" 到 "## 资源索引" 之间的内容
        # 匹配 "### 步骤N：标题" 后的 bash 代码块
        # 返回 ExecutionStep 对象列表
```

### SkillWorkflowExecutor

**职责**：执行工作流

```python
class SkillWorkflowExecutor:
    def parse_workflow(self) -> List[ExecutionStep]:
        """解析工作流步骤"""

    def execute_step(self, step: ExecutionStep, input_data, env):
        """执行单个步骤"""
        # 创建临时输入文件
        # 构建：python script.py --input temp.json [其他参数]
        # subprocess.run() 执行
        # 返回步骤结果

    def execute(self, input_data, env):
        """执行完整工作流"""
        # 1. 解析工作流步骤
        # 2. 依次执行每个步骤
        # 3. 将上一步的输出作为下一步的输入
        # 4. 返回最终结果
```

---

## 数据流转

```
输入数据 (input_data)
    │
    ├────────────────────────────────────────┐
    │                                        │
    ▼                                        │
┌────────────────────────────────────────┐ │
│  步骤1: 数据验证                         │ │
│  Input: input_data                      │ │
│  Output: validated_data                 │ │
└────────────────────────────────────────┘ │
    │                                        │
    ▼                                        ▼
┌────────────────────────────────────────┐ │
│  步骤2: 风险评估                         │ │
│  Input: validated_data                  │ │
│  Output: risk_assessment_data          │ │
└────────────────────────────────────────┘ │
    │                                        │
    ▼                                        ▼
┌────────────────────────────────────────┐ │
│  步骤3: 报告生成                         │ │
│  Input: risk_assessment_data            │ │
│  Output: report_modules                 │ │
└────────────────────────────────────────┘ │
    │                                        │
    ▼                                        ▼
最终结果 (report_modules)
```

---

## 使用示例

### 1. 命令行调用

```bash
python src/infrastructure/agent/skill_md_executor.py hypertension-risk-assessment \
    --input test_data.json
```

### 2. Python 代码调用

```python
from src.infrastructure.agent.skill_md_executor import execute_skill_via_skill_md

result = execute_skill_via_skill_md(
    skill_name="hypertension-risk-assessment",
    input_data={
        "user_input": "评估血压风险",
        "patient_data": {"age": 45, "gender": "male"},
        "vital_signs": {"systolic_bp": 150, "diastolic_bp": 95}
    }
)

print(result)
# {
#     "success": True,
#     "skill": "hypertension-risk-assessment",
#     "steps_executed": 3,
#     "step_results": [...],
#     "final_output": {...}
# }
```

---

## 脚本要求

每个脚本需要支持 `--input` 参数：

```python
# scripts/health_data_validator.py
import argparse
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        data = json.load(f)

    # 处理数据
    result = validate(data)

    # 输出 JSON 结果
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
```

---

## 扩展到其他技能

### 1. 创建技能目录结构

```bash
mkdir -p skills/new-assessment/{assets,scripts,references}
touch skills/new-assessment/SKILL.md
```

### 2. 在 SKILL.md 中定义工作流

```markdown
---
name: new-assessment
description: 新的健康评估技能
---

## 操作步骤

### 步骤1：数据收集
```bash
python scripts/collector.py --input <数据文件>
```

### 步骤2：分析计算
```bash
python scripts/analyzer.py --input collected_data.json
```

### 步骤3：结果输出
```bash
python scripts/output.py --input analysis_result.json
```
```

### 3. 实现脚本

每个脚本支持 `--input` 参数，接收和输出 JSON 数据。

### 4. 无需修改执行器

通用执行器会自动：
- 解析 SKILL.md
- 按顺序执行脚本
- 传递数据
- 收集结果

---

## 与现有系统集成

### 集成到 ms_agent_executor.py

```python
async def execute_skill_via_skill_md(
    skill_name: str,
    user_input: str,
    patient_context: Optional[PatientContext] = None,
    timeout: int = 30
) -> Optional[SkillExecutionResult]:
    """使用 SKILL.md 驱动方式执行技能"""
    from src.infrastructure.agent.skill_md_executor import SkillWorkflowExecutor

    skill_dir = Path("skills") / skill_name
    executor = SkillWorkflowExecutor(skill_dir)

    # 准备输入数据
    input_data = {
        "user_input": user_input,
        "patient_data": patient_context.basic_info if patient_context else {},
        "vital_signs": patient_context.vital_signs if patient_context else {},
        "medical_history": patient_context.medical_history if patient_context else {},
    }

    # 执行工作流
    result = await asyncio.to_thread(
        executor.execute,
        input_data=input_data,
        env=None
    )

    return SkillExecutionResult(
        skill_name=skill_name,
        success=result.get("success", False),
        result_data=result.get("final_output", result),
        execution_time=result.get("execution_time", 0)
    )
```

---

## 优势总结

| 优势 | 说明 |
|------|------|
| **单一配置源** | SKILL.md 是唯一的配置文件，修改工作流只需改 SKILL.md |
| **可视化工作流** | Markdown 格式，工作流步骤清晰可见 |
| **松耦合脚本** | 脚本独立，可在多个技能中复用 |
| **通用执行器** | 执行器完全通用，无需为每个技能写 main.py |
| **易于维护** | 新增技能只需写 SKILL.md 和实现脚本 |
| **易于扩展** | 添加新步骤只需在 SKILL.md 中增加一行 |

---

## 结论

采用 **SKILL.md 驱动**的架构是更好的选择：

1. **符合 DRY 原则** - 消除 SKILL.md 和 main.py 的重复
2. **职责清晰** - SKILL.md 定义"做什么"，脚本定义"怎么做"
3. **维护性强** - 修改工作流不需要改动代码
4. **扩展性好** - 新增技能或步骤非常简单

建议逐步迁移现有技能到这种架构，最终废弃 main.py 方式。
