# 双后端技能执行系统 (Dual-Backend Skill Execution System)

## 概述

实现了支持两种执行后端的技能执行系统，可通过配置自由切换：

1. **Subprocess 后端** (默认) - 基于 `subprocess.run()` 的脚本执行
2. **MS-Agent 后端** - 基于 `msagent` 库的执行（LLM规划、沙箱隔离）

## 文件结构

```
src/infrastructure/agent/
├── skill_executor_base.py        # 执行器抽象基类
├── subprocess_executor.py         # Subprocess 后端实现
├── msagent_executor_impl.py       # MS-Agent 后端实现
├── skill_executor_factory.py      # 工厂模式 + 配置管理
└── ms_agent_executor.py           # 统一入口（重构）

src/config/
├── settings.py                    # 添加了执行器配置项

.env.example                       # 环境变量配置示例
test_backend_comparison.py         # 对比测试脚本
```

## 配置切换方法

### 方法1: 环境变量 (推荐)

```bash
# .env 文件
SKILL_EXECUTOR_BACKEND=subprocess  # 或 msagent, auto
SKILL_EXECUTOR_TIMEOUT=30
SKILL_EXECUTOR_USE_SANDBOX=false
```

### 方法2: 代码配置

```python
from src.infrastructure.agent.skill_executor_factory import set_executor_config

# 切换到 msagent
set_executor_config({"backend": "msagent"})

# 切换回 subprocess
set_executor_config({"backend": "subprocess"})

# 自动选择
set_executor_config({"backend": "auto"})
```

### 方法3: 动态指定

```python
from src.infrastructure.agent.ms_agent_executor import execute_skill_via_backend

# 临时指定后端
result = await execute_skill_via_backend(
    skill_name="chronic-disease-risk-assessment",
    user_input="评估我的健康风险",
    patient_context=patient_context,
    backend="msagent"  # 临时使用 msagent
)
```

## 后端对比

| 特性 | Subprocess | MS-Agent |
|------|-----------|----------|
| **实现方式** | subprocess.run() | msagent 库 |
| **进程隔离** | ✅ 每个脚本独立进程 | ⚙️ 可选沙箱隔离 |
| **LLM 规划** | ❌ 无 | ✅ 自主分析 SKILL.md |
| **性能开销** | 中等（进程启动） | 低（进程内）或 高（沙箱） |
| **依赖** | 无额外依赖 | pip install msagent |
| **稳定性** | ✅ 生产验证 | ⚙️ 实验性 |
| **调试难度** | 低 | 中等 |

## 对比测试

运行对比测试：

```bash
python test_backend_comparison.py
```

测试结果示例：

```
============================================================
双后端对比测试 (Dual-Backend Comparison Test)
============================================================

可用后端 (Available backends):
  [OK] subprocess
  [N/A] msagent

============================================================
Testing backend: SUBPROCESS
============================================================

[SUCCESS] subprocess
  执行时间: 908.51 ms
  实际后端: subprocess
  输出大小: 1677 bytes
  模块数量: 7

详细结果已保存至: backend_comparison_results.json
```

## 安装 MS-Agent (可选)

如果要使用 MS-Agent 后端：

```bash
pip install msagent
```

## API 使用

### 基础使用

```python
from src.infrastructure.agent.ms_agent_executor import execute_skill_via_msagent

result = await execute_skill_via_msagent(
    skill_name="chronic-disease-risk-assessment",
    user_input="评估我的健康风险",
    patient_context=patient_context
)

if result and result.success:
    modules = result.result_data.get("modules", {})
    # 处理结果...
```

### 查询后端状态

```python
from src.infrastructure.agent.skill_executor_factory import (
    get_active_backend,
    list_available_backends
)

# 当前激活的后端
backend = get_active_backend()  # "subprocess" 或 "msagent"

# 可用的后端
available = list_available_backends()
# {"subprocess": True, "msagent": False}
```

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    execute_skill_via_msagent()              │
│                        (统一入口)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   SkillExecutorFactory                       │
│         (根据配置创建合适的执行器实例)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│ SubprocessSkillExecutor│  │ MSAgentSkillExecutor │
├──────────────────────┤  ├──────────────────────┤
│ - parse_workflow()    │  │ - parse_workflow()    │
│ - execute_step()      │  │ - execute_step()      │
│ - execute()           │  │ - execute()           │
└──────────────────────┘  └──────────────────────┘
         │                          │
         ▼                          ▼
┌──────────────────────┐  ┌──────────────────────┐
│ subprocess.run()     │  │ msagent.ScriptExecutor│
└──────────────────────┘  └──────────────────────┘
```

## 兼容性

- ✅ 完全向后兼容现有代码
- ✅ 默认使用 subprocess 后端（稳定）
- ✅ MS-Agent 未安装时自动降级到 subprocess
- ✅ 所有现有接口保持不变
