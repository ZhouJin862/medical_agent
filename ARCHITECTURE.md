# 智能体架构文档

## 系统概述

慢病健康管理智能体系统是一个基于 **DDD (领域驱动设计)** 的分层架构应用，集成了 **LangGraph** 工作流引擎和 **Claude Skills** 技能系统，提供智能化的健康评估、风险预测和健康管理计划生成服务。

---

## 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                      表现层 (Presentation)                  │
├─────────────────────────────────────────────────────────────┤
│  • FastAPI Routes (API 接口)                                │
│  • DTOs (请求/响应模型)                                       │
│  • Middleware (日志、错误处理、CORS)                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      应用层 (Application)                     │
├─────────────────────────────────────────────────────────────┤
│  • Application Services (应用服务)                           │
│    - ChatApplicationService                                  │
│    - SkillManagementApplicationService                       │
│    - ConsultationApplicationService                          │
│    - HealthAssessmentApplicationService                       │
│    - HealthPlanApplicationService                            │
│  • Commands (命令)                                           │
│  • Queries (查询)                                             │
│  • Handlers (处理器)                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      领域层 (Domain)                          │
├─────────────────────────────────────────────────────────────┤
│  • 实体 (Entities)                                           │
│    - Patient, Consultation, HealthPlan, Message             │
│  • 值对象 (Value Objects)                                    │
│    - BloodPressure, BMI, LipidProfile, etc.                  │
│  • 聚合 (Aggregates)                                         │
│  • 领域服务 (Domain Services)                                 │
│    - SkillsRegistry (技能注册表)                             │
│    - UnifiedSkillsRepository (统一技能仓库)                   │
│    - LLMSkillSelector (LLM 技能选择器)                        │
│    - ClaudeSkillsExecutor (Claude 技能执行器)                 │
│    - CompositeSkillExecutor (组合技能执行器)                 │
│    - SkillPackageManager (技能包管理器)                       │
│  • 仓储接口 (Repository Interfaces)                           │
│  • 领域事件 (Domain Events)                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   基础设施层 (Infrastructure)                │
├─────────────────────────────────────────────────────────────┤
│  • Agent (智能体)                                             │
│    - AgentState (智能体状态)                                  │
│    - LangGraph 工作流                                         │
│    - 节点 (Nodes):                                            │
│      - load_patient, retrieve_memory, classify_intent        │
│      - route_skill, execute_skill, aggregate_results         │
│    - SkillsIntegrationAgent (技能集成智能体)                 │
│  • 持久化 (Persistence)                                       │
│    - Database (MySQL + SQLAlchemy)                           │
│    - Repositories Impl (仓储实现)                             │
│  • 会话管理 (Session)                                         │
│    - SessionManager                                           │
│  • 内存存储 (Memory)                                          │
│    - MemoryStore (Mem0/File-based)                           │
│  • 外部服务集成                                               │
│    - Anthropic API                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心组件详解

### 1. 智能体引擎 (Agent Engine)

#### 1.1 LangGraph 工作流

```
┌─────────────────────────────────────────────────────────────┐
│                      MedicalAgent Graph                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐    ┌───────────┐    ┌────────────┐         │
│  │load_patient│───→│retrieve   │───→│classify     │         │
│  │           │    │_memory    │    │_intent     │         │
│  └──────────┘    └───────────┘    └────────────┘         │
│                                              ↓               │
│                                    ┌──────────────┐       │
│                                    │route_skill   │       │
│                                    └──────────────┘       │
│                                    ↓ (if skill)            │
│                      ┌─────────────┐    ┌──────────────┐      │
│                      │skip_skill   │←──→│execute_skill │      │
│                      └─────────────┘    └──────────────┘      │
│                               ↓                              │
│                      ┌───────────────┐                       │
│                      │aggregate      │───→ END              │
│                      │_results       │                       │
│                      └───────────────┘                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 智能体状态 (AgentState)

```python
class AgentState:
    # 输入
    user_input: str                    # 用户输入
    patient_id: str                    # 患者 ID

    # 处理状态
    status: AgentStatus                # 当前状态
    current_step: str                   # 当前步骤

    # 意图分类
    intent: IntentType                 # 意图类型
    confidence: float                  # 置信度
    suggested_skill: str                # 建议技能

    # 上下文
    patient_context: PatientContext   # 患者上下文
    conversation_memory: ConversationMemory  # 对话记忆

    # 结果
    skill_result: SkillExecutionResult  # 技能执行结果
    aggregated_response: str           # 聚合响应
    error_message: str                  # 错误消息
```

#### 1.3 意图类型 (IntentType)

```python
HEALTH_ASSESSMENT    # 健康评估
RISK_PREDICTION      # 风险预测
HEALTH_PLAN          # 健康计划
TRIAGE               # 分诊
MEDICATION_CHECK     # 用药检查
SERVICE_RECOMMENDATION # 服务推荐
GENERAL_CHAT         # 普通聊天
```

---

### 2. 技能系统 (Skills System)

#### 2.1 技能架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Skills System                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SkillsRegistry (技能注册表)                   │   │
│  │  • 扫描 skills/ 目录                                    │   │
│  │  • 读取 SKILL.md 元数据                                 │   │
│  │  • 三层渐进式披露:                                     │   │
│  │    1. 元数据层 (name, description, version)          │   │
│  │    2. 技能内容层 (SKILL.md 正文)                       │   │
│  │    3. 参考文件层 (引用的额外文档)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    UnifiedSkillsRepository (统一技能仓库)              │   │
│  │    • 整合文件技能 + 数据库技能                          │   │
│  │    • 提供统一的技能查询接口                            │   │
│  │    • 按层级分类 (basic/domain/composite)               │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │       SkillMatcher (LLM 技能匹配器)                   │   │
│  │    • 自动发现可用技能                                  │   │
│  │    • LLM 智能匹配 (Claude API)                         │   │
│  │    • 返回 skill_name, confidence, reasoning           │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     ClaudeSkillsExecutor (文件技能执行器)             │   │
│  │    • 加载 SKILL.md 内容                                │   │
│  │    • 构建增强提示词                                     │   │
│  │    • 调用 LLM 生成响应                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   FileSkillExecutor (脚本执行器)                      │   │
│  │    • 检测 skills/*/scripts/main.py                    │   │
│  │    • 子进程执行 Python 脚本                            │   │
│  │    • 传递 JSON 输入，解析输出                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   CompositeSkillExecutor (组合技能执行器)              │   │
│  │    • 执行数据库组合技能                                 │   │
│  │    • 按配置调用多个基础技能                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    SkillPackageManager (技能包管理器)                  │   │
│  │    • 导入 ZIP 技能包                                    │   │
│  │    • 导出技能包                                        │   │
│  │    • manifest.json 可选                                  │   │
│  │    • 支持 projects/ 和 skills/ 目录结构                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 技能脚本执行

技能可以包含可执行的 Python 脚本，用于结构化数据处理：

```
skills/
└── hypertension-risk-assessment/
    ├── SKILL.md
    └── scripts/
        └── main.py          # 脚本入口点
```

**脚本执行规范**：

1. **命令行参数**: `python main.py --input <input.json>`
2. **输入格式**: JSON 文件，包含 `vital_signs`, `patient_data` 等
3. **输出格式**: JSON，包含 `success`, `skill_name`, `data`
4. **执行方式**: 通过 `subprocess` 模块在隔离环境中运行
5. **超时控制**: 30 秒超时保护

**示例脚本输出**：
```json
{
  "success": true,
  "skill_name": "hypertension-risk-assessment",
  "data": {
    "risk_level": "high",
    "risk_category": "2",
    "systolic_bp": 160,
    "diastolic_bp": 95
  }
}
```

#### 2.2 技能类型

```
文件技能 (File Skills)          数据库技能 (Database Skills)
├── skills/                      ├── Database
│   ├── basic-assessment/        │   ├── hypertension-assessment
│   ├── hypertension-assessment/ │   ├── diabetes-management-plan
│   ├── hyperglycemia-risk-...    │   └── custom_composite_skill
│   └── SKILL.md                 │
```

#### 2.3 技能选择流程

```
用户输入 "血压150需要担心吗"
         ↓
MedicalAgent.process()
         ↓
┌────────────────────────────────┐
│  LangGraph 工作流节点:           │
│  1. load_patient               │
│  2. retrieve_memory            │
│  3. classify_intent            │
└────────────────────────────────┘
         ↓
┌────────────────────────────────┐
│  SkillMatcher (LLM 智能匹配)    │
│  • 自动发现所有可用技能          │
│  • 构建技能描述                  │
│  • Claude API 匹配              │
└────────────────────────────────┘
         ↓
AgentState 更新
├─ intent: "health_assessment"
├─ suggested_skill: "hypertension-risk-assessment"
├─ confidence: 0.95
└─ reasoning: "..."
         ↓
route_skill → execute_skill
         ↓
┌────────────────────────────────┐
│  检测 scripts/main.py           │
│  ├─ 存在 → 执行脚本              │
│  └─ 不存在 → ClaudeSkillsExecutor │
└────────────────────────────────┘
         ↓
aggregate_results
         ↓
响应内容 (流式返回 + 技能元数据)
```

**技能元数据追踪**：
- `intent`: 意图类型 (health_assessment, risk_prediction, chat 等)
- `suggested_skill`: 匹配的技能名称
- `confidence`: 匹配置信度 (0-1)
- `executed_skills`: 实际执行的技能列表

---

### 3. 会话管理 (Session Management)

```
┌─────────────────────────────────────────────────────────────┐
│                    Session Manager                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  SessionManager (单例模式)                                  │
│    ├── _sessions: Dict[session_id, Session]                 │
│    ├── get_or_create_session(session_id, patient_id)        │
│    ├── add_user_message(session_id, content)                │
│    ├── add_assistant_message(session_id, content)           │
│    └── get_conversation_history(session_id, limit)          │
│                                                               │
│  Session                                                       │
│    ├── session_id: str                                       │
│    ├── patient_id: str                                        │
│    ├── messages: List[SessionMessage]                       │
│    ├── created_at / updated_at                               │
│    └── metadata: Dict                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**双内存系统**：

1. **SessionManager** (会话级内存):
   - 保存用户和助手消息
   - 用于流式响应时的实时会话
   - 元数据标记: `{"saved_by": "session_manager"}`

2. **MedicalAgent.save_memory_node** (智能体内存):
   - 在 LangGraph 工作流中保存
   - 包含完整技能元数据 (intent, suggested_skill, confidence)
   - 元数据标记: `{"saved_by": "medical_agent_save_memory_node"}`

---

### 4. API 路由结构

```
/api/v1/
├── /health                          # 健康检查
├── /chat/stream                    # 流式聊天 (MedicalAgent 集成)
│   ├── POST (发送消息，接收 SSE 流)
│   │   • 请求: {message, patient_id, session_id}
│   │   • 响应: SSE 流 (start → token → end)
│   │   • end 块包含: intent, confidence, suggested_skill
│   └── 处理流程:
│       1. MedicalAgent.process()
│       2. LangGraph 工作流执行
│       3. 技能匹配 (SkillMatcher)
│       4. 脚本或 LLM 执行
│       5. 结果聚合返回
├── /chat/sessions/{patient_id}      # 获取患者会话列表
│   └── GET
├── /chat/sessions/{session_id}/messages  # 获取会话消息
│   └── GET
└── /chat/sessions/{session_id}      # 删除会话
    └── DELETE

/api/v2/
├── /skills                          # 技能列表 (文件+数据库)
│   └── GET
├── /skills/{skill_id}               # 获取技能详情
│   └── GET
├── /skills                          # 创建技能
│   └── POST
├── /skills/{skill_id}               # 更新技能
│   └── PUT
├── /skills/{skill_id}/enable        # 启用技能
│   └── POST
├── /skills/{skill_id}/disable       # 禁用技能
│   └── POST
├── /skills/{skill_id}/reload        # 重新加载技能
│   └── POST
└── /skills/{skill_id}               # 删除技能
    └── DELETE

/api/v2/
├── /skill-packages/import            # 导入技能包
│   └── POST
├── /skill-packages/export            # 导出技能包
│   └── POST
├── /skill-packages/validate          # 验证技能包
│   └── POST
└── /skill-packages/{id}              # 获取技能包
    └── GET
```

---

## 数据流

### 技能触发数据流

```
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────┐
│  前端   │    │  FastAPI  │    │   Streaming  │    │  MedicalAgent │
│  React  │───→│   API    │───→│    Chat      │───→│   .process()  │
└──────────┘    └──────────┘    └──────────────┘    └──────────────┘
                                                   ↓
                                          ┌──────────────┐
                                          │LangGraph WF  │
                                          │  (节点流程)   │
                                          └──────────────┘
                                                   ↓
                                          ┌──────────────┐
                                          │SkillMatcher  │
                                          │ (LLM智能匹配) │
                                          └──────────────┘
                                                   ↓
                                          ┌──────────────┐
                                          │  脚本/LLM    │
                                          │  执行引擎     │
                                          └──────────────┘
                                                   ↓ (流式)
┌──────────┐    ┌──────────┐    ┌──────────────┐    │   LLM      │
│  前端   │←───│  FastAPI  │←───│   Streaming  │←───│  Response  │
│  React  │    │   API    │    │    Chat      │    │  Provider  │
└──────────┘    └──────────┘    └──────────────┘    └──────────────┘
```

**Streaming Chat Endpoint (`/api/v1/chat/stream`)**：
- 使用 `MedicalAgent.process()` 进行处理
- 返回 SSE (Server-Sent Events) 流式响应
- 每个响应块包含：type, token, intent, confidence, suggested_skill
- 最终块 (end) 包含完整的技能元数据

### 会话持久化数据流

```
┌──────────┐    ┌──────────┐    ┌──────────────┐
│  前端   │───→│  FastAPI  │───→│   Session    │
│  React  │    │   API    │    │   Manager    │
│         │    │         │    │  (单例模式)   │
│  sessionId│    │         │    │              │
└──────────┘    └──────────┘    └──────────────┘
                                            ↓
                                    ┌──────────────┐
                                    │   Memory     │
                                    │   Store      │
                                    │  (持久化)     │
                                    └──────────────┘
```

---

## 关键设计模式

### 1. 仓储模式 (Repository Pattern)

```python
# 领域层 - 仓储接口
class IConsultationRepository(ABC):
    @abstractmethod
    async def save(self, consultation: Consultation) -> None:
        pass

# 基础设施层 - 仓储实现
class ConsultationRepositoryImpl(IConsultationRepository):
    async def save(self, consultation: Consultation) -> None:
        # Database implementation
        pass
```

### 2. 单例模式 (Singleton Pattern)

```python
# 全局单例
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
```

### 3. 策略模式 (Strategy Pattern)

```python
# 技能执行策略
class SkillExecutor(ABC):
    @abstractmethod
    async def execute(self, skill_name: str, input: str) -> dict:
        pass

# 文件技能执行器
class ClaudeSkillsExecutor(SkillExecutor):
    async def execute(self, skill_name: str, input: str) -> dict:
        # File-based skill execution
        pass

# 组合技能执行器
class CompositeSkillExecutor(SkillExecutor):
    async def execute(self, skill_name: str, input: str) -> dict:
        # Composite skill execution
        pass
```

### 4. 依赖注入 (Dependency Injection)

```python
# FastAPI 依赖注入
@app.get("/api/v2/skills")
async def list_skills(
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
):
    return await skill_service.list_skills()
```

---

## 技术栈

### 后端
- **框架**: FastAPI 0.110+
- **ORM**: SQLAlchemy (async)
- **数据库**: MySQL 8.0+
- **LLM**: Anthropic Claude (Sonnet 4/Haiku)
- **工作流**: LangGraph
- **异步**: asyncio, aiohttp

### 前端
- **框架**: React 18 + TypeScript
- **构建**: Vite 5
- **UI**: Material-UI (MUI)
- **图表**: ECharts, Recharts
- **状态管理**: React Hooks
- **主要组件**:
  - `ChatContainer`: 聊天界面容器
  - `MessageList`: 消息列表展示
  - `ChatInput`: 用户输入框
  - `useStreamingChat`: 流式聊天 Hook (支持 SSE)
- **消息类型扩展**:
  - `intent`: 意图类型
  - `confidence`: 置信度
  - `suggested_skill`: 匹配的技能
  - `structured_data`: 结构化输出数据

---

## 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (Port 3000)                     │
│                    React + Vite Dev Server                 │
└─────────────────────────────────────────────────────────────┘
                               │
                               ↓ Vite Proxy
┌─────────────────────────────────────────────────────────────┐
│                       后端 (Port 8001)                       │
│                    FastAPI + Uvicorn                     │
├─────────────────────────────────────────────────────────────┤
│  • API Routes                                                 │
│  • Skill Selection & Execution                              │
│  • Session Management                                        │
│  • Stream Response (SSE)                                     │
└─────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
┌──────────────┐    ┌─────────────┐     ┌──────────────┐
│   MySQL       │    │    Memory   │     │  Anthropic   │
│   Database    │    │   Store     │     │     API       │
│   (Port 3306) │    │  (Mem0/File) │     │              │
└──────────────┘    └─────────────┘     └──────────────┘
```

---

## 扩展性

### 添加新的文件技能

1. 在 `skills/` 目录创建技能文件夹
2. 创建 `SKILL.md` 文件，包含元数据和内容
3. (可选) 创建 `scripts/main.py` 用于脚本执行
4. 技能自动被 `SkillsRegistry` 发现并加载
5. LLM 自动学习技能描述并用于选择

**技能脚本示例结构**：
```
skills/my-new-skill/
├── SKILL.md           # 技能元数据和内容
└── scripts/
    └── main.py        # 脚本入口点
        # 解析 --input 参数
        # 处理输入数据
        # 返回 JSON 结果
```

### 添加新的组合技能

1. 通过 API 创建数据库技能
2. 配置要包含的基础技能列表
3. 设置执行顺序和参数传递
4. 技能自动集成到工作流

### 自定义智能体节点

1. 在 `nodes.py` 中定义新节点函数
2. 在 `graph.py` 中添加到工作流
3. 实现条件路由逻辑
4. 支持状态传递和错误处理

---

## 安全与监控

### 安全
- JWT 认证 (预留)
- CORS 配置
- SQL 注入防护 (ORM)
- XSS 防护

### 监控
- 结构化日志
- 请求/响应日志中间件
- 错误追踪
- 性能指标

### 数据持久化
- MySQL: 业务数据、技能配置
- Mem0/File: 长期记忆存储
- 内存: 会话状态、缓存

---

## 总结

该智能体系统具有以下特点：

1. **分层架构**: 清晰的 DDD 分层，易于维护和扩展
2. **技能驱动**: 通过技能系统实现功能解耦和可组合性
3. **LLM 增强**: 智能技能选择和上下文理解
4. **流式响应**: 实时返回生成结果
5. **会话管理**: 保持对话上下文和历史
6. **可扩展**: 支持文件技能、数据库技能、组合技能

通过这种架构，系统可以灵活地添加新的健康评估技能，而不需要修改核心代码，符合开闭原则（OCP）。
