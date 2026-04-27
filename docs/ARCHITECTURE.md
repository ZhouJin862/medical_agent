# 医疗智能体项目整体架构

## 项目概览

```
medical_agent/
├── src/
│   ├── application/          # 应用层 - 命令处理、服务编排
│   ├── domain/               # 领域层 - 业务逻辑、实体、规则
│   ├── infrastructure/        # 基础设施层 - 外部服务集成
│   └── interface/            # 接口层 - API、WebSocket、DTO
├── skills/                   # Claude Skills (文件系统技能)
├── frontend/                # React + TypeScript 前端
└── docs/                    # 文档
```

---

## 四层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer (接口层)                    │
│  FastAPI Routes + WebSocket + DTOs                         │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer (应用层)                    │
│  Commands + Queries + Handlers + Services                   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer (领域层)                       │
│  Entities + Value Objects + Rules + Repositories            │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Infrastructure Layer (基础设施层)                │
│  Agent + LLM + Database + MCP + Memory + Skills            │
└─────────────────────────────────────────────────────────────┘
```

---

## 详细架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              用户                                           │
│                      Web Browser / Mobile App                          │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │ HTTP/WebSocket
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           Interface Layer                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐        │
│  │   FastAPI Routes  │  │   WebSocket      │  │   DTOs/Models    │        │
│  │                   │  │   Handlers       │  │                   │        │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘        │
│                                                                              │
│  Key Files:                                                                   │
│  - src/interface/api/main.py              # FastAPI 应用入口            │
│  - src/interface/api/routes/             # API 路由定义                │
│  - src/interface/websocket/              # WebSocket 处理器            │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         Application Layer                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Command Handlers                              │   │
│  │  - consultation_command_handlers.py                               │   │
│  │  - skill_command_handlers.py                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Query Handlers                                 │   │
│  │  - consultation_query_handlers.py                                 │   │
│  │  - skill_query_handlers.py                                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Application Services                            │   │
│  │  - chat_service.py                   # 聊天服务                      │   │
│  │  - consultation_service.py           # 咨询服务                    │   │
│  │  - skill_management_service.py       # 技能管理服务                │   │
│  │  - health_assessment_service.py       # 健康评估服务                │   │
│  │  - health_plan_service.py            # 健康计划服务                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          Domain Layer                                  │
│                                                                              │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  │
│  │   Consultation      │  │    Health Plan     │  │   Recommendation   │  │
│  │   Domain           │  │    Domain          │  │   Domain           │  │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Shared Domain                                │   │
│  │  - services/                                                       │   │
│  │    - rule_engine.py                # 规则引擎 (阈⚊值、范围、评分)   │   │
│  │    - rule_enhanced_skill.py       # 技能+规则集成                │   │
│  │    - llm_skill_selector.py         # LLM技能选择器              │   │
│  │    - skills_registry.py            # Claude Skills 注册表        │   │
│  │    - unified_skills_repository.py  # 统一技能仓库               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Domain Models (Entities, Value Objects, Events):                         │
│  - Consultation, Message, ConsultationStatus                              │
│  - HealthPlan, Prescription (Diet, Exercise, Medication...)             │
│  - Recommendation, ServiceProduct                                     │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       Agent System                               │   │
│  │  - agent/                                                         │   │
│  │    - graph.py                     # LangGraph 工作流图           │   │
│  │    - state.py                    # Agent 状态定义               │   │
│  │    - nodes.py                    # 工作流节点                 │   │
│  │    - skills_integration.py        # Skills 集成                │   │
│  │                                                                   │   │
│  │  Workflow:                                                          │   │
│  │    load_patient → retrieve_memory → classify_intent              │   │
│  │    → execute_skill → aggregate → save_memory                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       LLM Integration                             │   │
│  │  - llm/                                                          │   │
│  │    - claude_client.py              # Claude API 客户端          │   │
│  │    - prompt_builder.py             # 提示词构建器              │   │
│  │                                                                   │   │
│  │  Model: Claude Sonnet 4 / Haiku (可配置)                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       Database                                    │   │
│  │  - persistence/                                                  │   │
│  │    - models/                      # SQLAlchemy ORM 模型        │   │
│  │      - skill_models.py             # 技能模型                    │   │
│  │      - rule_models.py              # 规则模型                    │   │
│  │      - consultation_models.py      # 咨询模型                  │   │
│  │    - session/                     # 数据库会话管理              │   │
│  │                                                                   │   │
│  │  Database: MySQL (aiomysql)                                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       MCP (Model Context Protocol)                  │   │
│  │  - mcp/                                                          │   │
│  │    - client_factory.py             # MCP 客户端工厂             │   │
│  │    - profile_server.py              # 用户资料 MCP 服务        │   │
│  │    - knowledge_server.py            # 知识库 MCP 服务           │   │
│  │                                                                   │   │
│  │  Used for: Patient profile retrieval, Knowledge base access              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       Memory                                       │   │
│  │  - memory/                                                       │   │
│  │    - memory_store.py              # Mem0 记忆存储               │   │
│  │                                                                   │   │
│  │  Used for: Conversation history, user profile extraction                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       Knowledge Base                                │   │
│  │  - knowledge/                                                    │   │
│  │    - retrieval.py                 # 知识检索                  │   │
│  │                                                                   │   │
│  │  Used for: Medical guidelines, drug information, reference data           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        Claude Skills (File System)                       │
│                                                                              │
│  skills/                                                                     │
│  ├── hypertension-assessment/SKILL.md    # 高血压评估技能                  │
│  ├── diabetes-assessment/SKILL.md       # 糖尿病评估技能                  │
│  ├── dyslipidemia-assessment/SKILL.md   # 血脂异常评估技能                │
│  ├── gout_assessment/SKILL.md           # 痛风评估技能                    │
│  └── ...                                                                │
│                                                                              │
│  Progressive Disclosure:                                                  │
│  - Startup:   Only name + description                                 │
│  - Trigger:   Load SKILL.md                                            │
│  - On-demand: Load reference/*.md                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 核心组件说明

### 1. Agent 工作流 (LangGraph)

```
用户输入 "我血压150/95，严重吗？"
    │
    ▼
load_patient (加载患者数据)
    │  → MCP Profile Server → 获取患者基本信息、生命体征
    ▼
retrieve_memory (检索对话历史)
    │  → Mem0 Memory Store → 获取对话上下文
    ▼
classify_intent (意图分类)
    │  → LLMSkillSelector → LLM分析并选择合适的技能
    │  → 结果: hypertension-assessment (confidence: 1.0)
    ▼
execute_skill (执行技能)
    │  → ClaudeSkillsExecutor → 加载技能内容
    │  → 规则引擎评估 (可选)
    │  → LLM 生成响应
    ▼
aggregate_results (聚合结果)
    │  → 整合技能输出、结构化数据
    ▼
save_memory (保存记忆)
    │  → Mem0 Memory Store → 保存对话历史
    ▼
返回响应给用户
```

### 2. 技能系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Skills 系统架构                              │
└─────────────────────────────────────────────────────────────┘

                      ┌─────────────────┐
                      │  用户输入         │
                      │  "血压150/95"     │
                      └────────┬────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
         │ Claude Skills│ │ Database    │ │ LLM Selection│
         │ (File System)│ │ Skills      │ │             │
         └─────────────┘ └─────────────┘ └─────────────┘
                │              │              │
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ UnifiedSkillsRepository│
                    │  - 统一技能访问       │
                    │  - 渐进式披露支持     │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Skill Execution     │
                    │  - 规则引擎评估       │
                    │  - LLM 增强生成       │
                    │  - 模板渲染输出       │
                    └─────────────────────┘
```

#### 2.1 技能模板系统

每个单病种风险评估技能都包含模板管理器：

```
skills/[skill-name]/
├── SKILL.md                    # 技能元数据
├── scripts/
│   ├── main.py                 # 技能入口
│   └── template_manager.py     # 模板管理器
└── assets/
    └── report_template.md      # 报告模板
```

**模板渲染流程：**
```
1. 加载模板 (template_manager.load_template)
2. 准备变量 (template_vars)
3. 按章节渲染 (render_template_by_section)
4. 返回模块化输出 (modules)
```

**输出格式：**
```json
{
  "success": true,
  "skill_name": "hypertension-risk-assessment",
  "data": {
    "modules": {
      "报告信息": "报告编号、日期等",
      "一、血压水平评估": "## 一、血压水平评估\n\n...",
      "二、心血管风险分层": "## 二、心血管风险分层\n\n...",
      ...
    },
    "total_modules": 6,
    "risk_level": "high",
    "risk_grade": "2级"
  }
}
```

### 3. 规则引擎

```
规则引擎 (RuleEngine)
    │
    ├── 阈值规则 (THRESHOLD)
    │   └── 示例: systolic >= 140 OR diastolic >= 90
    │
    ├── 范围规则 (RANGE)
    │   ├── 单字段: BMI 18.5-24.9
    │   └── 双字段: BP (systolic: 140-159, diastolic: 90-99)
    │
    ├── 评分规则 (SCORE)
    │   └── 多因素加权评分
    │
    └── 条件规则 (CONDITION)
        └── 复杂逻辑组合

规则评估结果:
    - 匹配的规则列表
    - 置信度分数
    - 结构化输出
```

### 4. 数据流

```
用户请求
    │
    ▼
┌─────────────────┐
│  FastAPI Route   │ → /api/chat/send
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ChatService    │ → 创建命令、调用处理器
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Command Handler │ → 处理业务逻辑
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MedicalAgent   │ → LangGraph 工作流
└────────┬────────┘
         │
    ├──▼──┬───┬───┬───┬───┐
    │    │   │   │   │
    ▼    ▼   ▼   ▼   ▼
  患者  记忆 意图 技能 聚合
  数据  上下文 分类 执行 结果
    │    │   │   │   │
    └────┴───┴───┴───┘
         │
         ▼
    ┌────────────┐
    │  LLM + 规则  │
    │  生成响应   │
    └────────────┘
```

---

## 技术栈

### 后端
- **框架**: FastAPI + Python 3.13
- **工作流**: LangGraph
- **数据库**: MySQL + aiomysql + SQLAlchemy
- **LLM**: Claude (Sonnet 4 / Haiku)
- **记忆**: Mem0
- **知识库**: 向量检索

### 前端
- **框架**: React + TypeScript
- **UI**: Material-UI (MUI)
- **状态管理**: React Context + Hooks
- **路由**: React Router

### 集成
- **MCP**: Model Context Protocol (外部服务集成)
- **WebSocket**: 实时通信
- **REST API**: 标准 HTTP 接口

---

## 当前已实现功能

### ✅ 核心功能
- [x] LangGraph 工作流引擎
- [x] Claude Skills (文件系统技能)
- [x] 数据库技能管理
- [x] 规则引擎 (阈值、范围、评分)
- [x] LLM 技能选择器
- [x] 渐进式披露机制
- [x] MCP 集成 (用户资料、知识库)
- [x] Mem0 记忆存储
- [x] WebSocket 实时通信

### ✅ 技能 (6个)

#### 单病种风险评估技能 (5个)
- [x] **高血压风险评估** (hypertension-risk-assessment)
  - 基于血压值评估高血压风险分级
  - 使用模板生成结构化报告
  - 包含心血管风险分层、干预建议等

- [x] **高血糖风险评估** (hyperglycemia-risk-assessment)
  - 基于空腹血糖/糖化血红蛋白评估糖尿病风险
  - 使用模板生成结构化报告
  - 包含糖尿病前期评估、并发症筛查等

- [x] **高血脂风险评估** (hyperlipidemia-risk-assessment)
  - 基于血脂四项评估心血管风险
  - 使用模板生成结构化报告
  - 包含LDL-C危险分层、残余风险评估等

- [x] **高尿酸风险评估** (hyperuricemia-risk-assessment)
  - 基于血尿酸值评估痛风风险
  - 使用模板生成结构化报告
  - 包含肾功能评估、代谢综合征评估等

- [x] **肥胖风险评估** (obesity-risk-assessment)
  - 基于BMI和腰围评估肥胖风险
  - 使用模板生成结构化报告
  - 包含中心型肥胖评估、代谢综合征诊断等

#### 综合评估技能 (1个)
- [x] **慢性病综合风险评估** (chronic-disease-risk-assessment)
  - "四高一重"综合评估（高血压、高血糖、高血脂、高尿酸、肥胖）
  - 基于循证医学证据的多维度健康画像
  - 量化预测疾病爆发概率

### ✅ API 端点
- `/api/chat/send` - 发送消息
- `/api/skills/*` - 技能管理 (v1)
- `/api/v2/skills/*` - Claude Skills (v2)
- `/api/agent/process` - Skills-Integrated Agent
- `/api/rules/*` - 规则管理
- `/ws/chat` - WebSocket 聊天

---

## 设计模式

### 1. DDD (领域驱动设计)
- **Domain Layer**: 纯业务逻辑，无外部依赖
- **Application Layer**: 编排用例和事务
- **Infrastructure Layer**: 技术实现细节

### 2. CQRS (命令查询分离)
- **Commands**: 写操作 (创建、更新、删除)
- **Queries**: 读操作 (查询、列表)

### 3. Repository Pattern
- 抽象数据访问
- 支持不同存储实现

### 4. Strategy Pattern
- 可插拔的技能执行策略
- 规则引擎可独立替换

### 5. Progressive Disclosure
- 分层加载技能内容
- 优化 Token 使用

---

## 扩展性

### 添加新技能

**方式 1: Claude Skills (文件系统)**
```bash
mkdir -p skills/new-skill/reference
vim skills/new-skill/SKILL.md
```

**方式 2: 数据库技能**
```python
await skill_service.create_skill(
    name="new_skill",
    display_name="新技能",
    description="技能描述",
    intent_keywords=["关键词"],
)
```

### 添加新规则
```python
rule = {
    "name": "new_rule",
    "type": "threshold",
    "config": {"field": "value", "operator": ">=", "threshold": 100},
}
```

### 添加新 MCP 服务
```python
# 创建新的 MCP 客户端
class NewMCPClient(BaseMCPClient):
    server_name = "new_server"
    ...
```

---

## 总结

这是一个 **现代化的医疗智能体系统**，采用：

1. **领域驱动设计** - 清晰的领域边界
2. **LangGraph 工作流** - 可控的 Agent 流程
3. **Claude Skills** - 标准化的技能管理
4. **规则引擎** - 临床决策支持
5. **渐进式披露** - 高效的内容加载
6. **MCP 集成** - 灵活的外部服务接入

整体架构清晰、可扩展，适合持续迭代和功能增强。
