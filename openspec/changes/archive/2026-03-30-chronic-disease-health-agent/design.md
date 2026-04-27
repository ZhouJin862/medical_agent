# 慢病健康管理智能体系统 - 技术设计

## Context

### 背景
当前健康档案系统缺乏智能化的健康评估和管理能力。健管师需要手工分析患者数据，效率低且易遗漏风险。随着"四高一重"慢病患者数量持续增长，亟需引入 AI 智能体实现自动化健康评估、风险预测和个性化健康方案生成。

### 现状
- 健康档案系统已有患者数据（血压、血糖、血脂等）
- 现有 Java 服务提供分诊导医、合理用药、服务推荐功能
- 无 AI 智能体能力，无健康管理方案生成

### 约束
- 需与现有 Java 服务集成
- 患者数据通过 MCP 协议从健康档案系统获取（不存储在本地）
- 需支持前后端分离架构
- 必须遵循 DDD 设计规范
- 采用 TDD 开发模式

### 利益相关者
- 健管师：使用智能体进行健康评估和方案制定
- 患者：接收个性化的健康管理建议
- 开发团队：维护和扩展智能体系统

## Goals / Non-Goals

**Goals:**
- 构建基于 DDD 的慢病管理智能体系统
- 实现聊天交互式健康评估和管理
- 支持四高一重（高血糖、高血压、高血脂、高尿酸、肥胖）专项管理
- 集成外部 Java 服务（分诊、用药、服务推荐）
- 支持模型动态切换和 Skill 动态加载
- 提供前后端完整实现

**Non-Goals:**
- 不替代医生诊断，仅提供辅助建议
- 不直接存储患者健康档案（通过 MCP 获取）
- 不实现电子病历系统（与现有系统集成）
- 不支持视频、语音等多模态交互（V1 版本）

## Decisions

### 1. 架构模式：DDD（领域驱动设计）

**决策：** 采用四层 DDD 架构（接口层、应用层、领域层、基础设施层）

**理由：**
- 清晰的职责分离，便于维护和扩展
- 领域层与基础设施层解耦，便于技术栈替换
- 符合复杂业务系统的设计最佳实践
- 便于团队协作和知识传递

**替代方案：**
- 三层架构：职责不够清晰，业务逻辑容易分散
- 六边形架构：过于复杂，学习成本高

### 2. 限界上下文划分

**决策：** 划分 3 个限界上下文 + 共享内核

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Consultation   │  │  HealthPlan     │  │ Recommendation  │
│  (咨询上下文)    │  │  (健康方案)      │  │  (推荐)         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         ┌──────────────────────────────────────┐
         │         Shared Kernel (共享内核)      │
         │  PatientData, VitalSigns, DiseaseType │
         └──────────────────────────────────────┘
```

**理由：**
- Consultation：核心对话业务，独立性强
- HealthPlan：处方生成，与咨询解耦便于复用
- Recommendation：外部推荐服务，作为值对象使用
- Shared Kernel：四高一重共用值对象，避免重复

### 3. AI 框架：LangGraph + DSPy

**决策：** 使用 LangGraph 编排工作流，DSPy 实现 Skills

**理由：**
- LangGraph：可视化工作流，状态管理清晰，支持条件分支
- DSPy：声明式定义 Skills，支持自动优化提示词，模块化可组合
- 两者互补：LangGraph 负责流程控制，DSPy 负责技能实现

**替代方案：**
- 纯 LangChain：灵活性低，提示词管理困难
- 纯 DSPy：缺乏工作流编排能力
- 自研框架：开发成本高，维护困难

### 4. Skills 管理：数据库动态加载

**决策：** Skills 配置存储在数据库，系统启动时动态加载

**理由：**
- 无需重启服务即可更新 Skills
- 支持多租户场景（不同客户不同 Skills）
- 便于 A/B 测试和灰度发布
- 支持运行时启用/禁用 Skills

**数据模型：**
```sql
skills (主表)
├── id, name, display_name, type, category, enabled
skill_prompts (提示词)
├── skill_id, prompt_type, content, version
skill_model_configs (模型配置)
├── skill_id, model_provider, model_name, temperature
skill_knowledge_mapping (知识库关联)
├── skill_id, knowledge_base_code
skill_intent_mapping (意图映射)
├── skill_id, intent_keyword
```

### 5. 模型切换：配置驱动

**决策：** 通过 YAML 配置文件控制模型选择，支持按 Skill 配置

**理由：**
- 灵活应对不同场景需求（敏感数据用司内模型）
- 支持模型降级策略（主模型失败切换备用）
- 便于成本控制（复杂任务用优质模型，简单任务用经济模型）

**配置格式：**
```yaml
model_config:
  default:
    provider: internal
    model: glm-5
    api_key: ${ANTHROPIC_API_KEY}
    base_url: https://open.bigmodel.cn/api/anthropic

  providers:
    openai:
      model: gpt-4o-mini
      api_key: ${OPENAI_API_KEY}

  skill_mapping:
    triage_guidance:
      provider: internal
    medication_check:
      provider: internal
```

### 6. 记忆系统：Mem0 长期记忆

**决策：** 使用 Mem0 存储患者上下文记忆

**理由：**
- 支持向量检索，快速找到相关记忆
- 自动总结对话，提取关键信息
- 支持多用户隔离

**记忆内容：**
- 患者基本信息
- 健康评估结果
- 重要风险因素
- 生活习惯和偏好

### 7. MCP 集成：独立进程 Servers

**决策：** 4 个 MCP Servers 作为独立进程运行

**理由：**
- 隔离性好，单个 Server 故障不影响其他
- 可独立部署和扩展
- 便于调试和监控

**Server 列表：**
| Server | 用途 | Tools |
|--------|------|-------|
| profile_server | 健康档案 | get_patient_profile, get_vital_signs, get_medical_records |
| triage_server | 分诊导医 | get_hospitals, get_departments, get_doctors |
| medication_server | 合理用药 | check_medication, recommend_drugs |
| service_server | 服务推荐 | recommend_insurance, recommend_health_services |

### 8. 前后端架构

**后端：** FastAPI + WebSocket
- RESTful API 用于 CRUD 操作
- WebSocket 用于实时聊天

**前端：** 聊天界面 + 个性化页面
- 聊天区域：自然语言交互
- 展示区域：根据智能体返回的 `structured_data` 动态渲染

### 9. 四高一重业务规则

**决策：** 在值对象中实现业务规则，确保领域逻辑纯粹

**示例：**
```python
class BloodPressure(ValueObject):
    def classify(self) -> str:
        if self.systolic < 120 and self.diastolic < 80:
            return "正常"
        elif self.systolic < 140 and self.diastolic < 90:
            return "正常高值"
        # ...
```

### 10. 测试策略：TDD

**决策：** 严格遵循红-绿-重构循环

**测试覆盖：**
- 单元测试：领域层（实体、值对象、领域服务）
- 集成测试：应用服务、仓储实现
- E2E 测试：关键业务流程

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │  Chat Interface     │  │  Personalized Display       │  │
│  │  (WebSocket)        │  │  (Dynamic Rendering)        │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Interface Layer                                         ││
│  │  Controllers → DTOs → WebSocket Handlers                ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Application Layer                                      ││
│  │  Application Services → Commands → Queries → Handlers   ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Domain Layer                                           ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ││
│  │  │Consultation  │  │HealthPlan    │  │Recommendation│  ││
│  │  │(Aggregates)  │  │(Aggregates)  │  │(Value Objects)│  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  ││
│  │  ┌──────────────────────────────────────────────────────┐││
│  │  │            Shared Kernel                             │││
│  │  │  PatientData, VitalSigns, DiseaseType, RiskLevel     │││
│  │  └──────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Infrastructure Layer                                   ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        ││
│  │  │LangGraph   │  │DSPy Skills │  │MCP Clients │        ││
│  │  │Workflow    │  │(Dynamic)   │  │            │        ││
│  │  └────────────┘  └────────────┘  └────────────┘        ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        ││
│  │  │LLM Factory │  │Memory      │  │Persistence │        ││
│  │  │            │  │(Mem0)      │  │(MySQL)     │        ││
│  │  └────────────┘  └────────────┘  └────────────┘        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                            │ MCP Protocol
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      MCP Servers (独立进程)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │profile_server│  │triage_server │  │medication_   │      │
│  │              │  │              │  │server        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐                                            │
│  │service_server│                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  External Java Services                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │健康档案系统   │  │分诊导医系统   │  │合理用药系统   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### 核心表结构

```sql
-- 咨询对话（Consultation 聚合根）
consultations
├── id (PK)
├── consultation_id (unique)
├── patient_id (患者外部ID，不存储患者详情)
├── status (enum: active, completed, archived)
├── created_at, updated_at

-- 对话消息（Message 实体）
messages
├── id (PK)
├── consultation_id (FK)
├── role (enum: user, assistant, system)
├── content (TEXT)
├── intent (意图分类)
├── structured_metadata (JSON: 存储返回的结构化数据快照)
├── created_at

-- 健康方案（HealthPlan 聚合根）
health_plans
├── id (PK)
├── plan_id (unique)
├── patient_id
├── plan_type (enum: comprehensive, disease_specific)
├── created_at, updated_at

-- 处方（Prescription 实体）
prescriptions
├── id (PK)
├── health_plan_id (FK)
├── prescription_type (enum: diet, exercise, sleep, medication, psych)
├── content (JSON: 处方详细内容)
├── created_at

-- Skills 配置
skills (主表)
├── id (PK)
├── name (unique, 如: hypertension_assessment)
├── display_name (显示名称)
├── type (enum: generic, disease_specific, prescription, mcp_tool)
├── category (分类)
├── enabled (BOOLEAN)
├── version

-- 四高一重疾病类型
disease_types
├── id (PK)
├── code (unique: HYPERTENSION, DIABETES, DYSLIPIDEMIA, GOUT, OBESITY)
├── name, name_en
├── category (enum: four_highs, obesity)
├── icd_code

-- 知识库
knowledge_bases
├── id (PK)
├── code (unique)
├── disease_code (FK → disease_types)
├── knowledge_type (enum: guideline, risk_rule, reference, drug_guide)
├── content (TEXT)
├── source (来源，如：中国高血压防治指南2023)

-- 体征指标标准
vital_signs_standards
├── id (PK)
├── indicator_code (unique: SBP, DBP, FPG, HbA1c, TC, TG, UA, BMI)
├── disease_code (关联疾病)
├── normal_min, normal_max (正常范围)
├── risk_low_min, risk_low_max (低风险范围)
├── risk_medium_min, risk_medium_max (中风险范围)
├── risk_high_min, risk_high_max (高风险范围)
```

## LangGraph Workflow Design

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentState                                │
│  • messages: List[BaseMessage]                               │
│  • patient_id: str                                           │
│  • patient_data: Dict (从 MCP 获取)                           │
│  • context: Dict (记忆、知识图谱)                             │
│  • intent: IntentType                                        │
│  • structured_output: Dict (返回给前端)                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Workflow Nodes                             │
│                                                             │
│  [load_patient] → 从 MCP 获取患者数据                         │
│       ↓                                                      │
│  [retrieve_memory] → 从 Mem0 检索相关记忆                     │
│       ↓                                                      │
│  [classify_intent] → 意图识别 (支持 @skill_name)             │
│       ↓                                                      │
│  [route_skill] ──┬──► health_assessment                      │
│                  ├──► risk_prediction                        │
│                  ├──► health_promotion                       │
│                  ├──► triage_guidance (MCP)                  │
│                  ├──► medication_check (MCP)                │
│                  └──► service_recommend (MCP)                 │
│                  │                                             │
│                  ├─ 并行执行多个 Skills                        │
│                  │                                             │
│                  ▼                                             │
│  [aggregate_results] → 聚合所有 Skill 结果                     │
│       ↓                                                      │
│  [save_memory] → 保存到 Mem0                                  │
│       ↓                                                      │
│  (END) → 返回响应                                            │
└─────────────────────────────────────────────────────────────┘
```

## DSPy Skills Architecture

```
DSPy Skills 层次结构
├── generic/ (通用 Skills)
│   ├── HealthAssessmentSkill
│   ├── RiskPredictionSkill
│   └── HealthProfileSkill
│
├── disease/ (病种 Skills - 四高一重)
│   ├── HypertensionSkill
│   ├── DiabetesSkill
│   ├── DyslipidemiaSkill
│   ├── GoutSkill
│   ├── ObesitySkill
│   └── MetabolicSyndromeSkill (组合)
│
├── prescription/ (处方 Skills)
│   ├── DietPrescriptionSkill
│   ├── ExercisePrescriptionSkill
│   └── SleepPrescriptionSkill
│
└── mcp_tools/ (MCP Tool Skills)
    ├── TriageGuidanceSkill
    ├── MedicationCheckSkill
    └── ServiceRecommendSkill
```

### DSPy Signature 示例

```python
class HypertensionAssessmentSignature(dspy.Signature):
    """高血压评估签名"""
    # 输入
    patient_data = dspy.InputField(desc="患者数据")
    blood_pressure = dspy.InputField(desc="血压：收缩压/舒张压")
    medical_history = dspy.InputField(desc="既往病史")
    knowledge = dspy.InputField(desc="高血压防治指南")

    # 输出
    bp_level = dspy.OutputField(desc="血压级别")
    cv_risk = dspy.OutputField(desc="心血管风险")
    target_bp = dspy.OutputField(desc="血压控制目标")
    recommendations = dspy.OutputField(desc="管理建议")
```

## Risks / Trade-offs

### Risk 1: LLM 输出不稳定
**描述：** LLM 输出可能不稳定，结构化数据解析失败

**缓解措施：**
- 使用 DSPy 优化提示词，提高输出稳定性
- 定义严格的 Pydantic 模型约束输出格式
- 实现重试机制和降级策略

### Risk 2: MCP 服务依赖
**描述：** 外部 MCP 服务不可用时功能降级

**缓解措施：**
- 实现 MCP 服务的健康检查和熔断机制
- 关键功能提供降级方案（如规则引擎）
- 记录详细的错误日志便于排查

### Risk 3: 模型成本
**描述：** 大量调用 LLM 可能导致成本高昂

**缓解措施：**
- 实现智能缓存（相同查询使用缓存结果）
- 简单查询使用规则引擎，复杂查询使用 LLM
- 按业务优先级分配模型资源

### Risk 4: 数据隐私
**描述：** 患者健康数据可能涉及隐私

**缓解措施：**
- 敏感数据优先使用司内模型
- 不在本地存储患者健康档案
- 实现 data-at-rest 和 data-in-transit 加密

### Trade-off 1: 开发速度 vs 灵活性
**描述：** DDD + DSPy 架构增加了初期开发成本

**权衡：**
- 牺牲短期开发速度
- 获得长期可维护性和扩展性

### Trade-off 2: 性能 vs 准确性
**描述：** 调用多个 Skills 可能增加响应时间

**权衡：**
- 通过并行执行优化性能
- 对于紧急场景提供快速通道

## Migration Plan

### 阶段 1：基础设施搭建 (Week 1-2)
- [ ] 项目结构初始化（DDD 四层）
- [ ] 数据库设计和迁移脚本
- [ ] MCP Servers 基础框架
- [ ] 配置管理系统

### 阶段 2：核心功能实现 (Week 3-5)
- [ ] 领域层：实体、值对象、聚合根
- [ ] LangGraph 工作流框架
- [ ] DSPy Skills 基础实现
- [ ] 记忆系统集成

### 阶段 3：四高一重 Skills (Week 6-8)
- [ ] 高血压评估 Skill
- [ ] 糖尿病评估 Skill
- [ ] 血脂评估 Skill
- [ ] 痛风评估 Skill
- [ ] 肥胖评估 Skill
- [ ] 代谢综合征 Skill

### 阶段 4：处方和推荐 (Week 9-10)
- [ ] 饮食/运动/睡眠处方 Skills
- [ ] MCP 集成（分诊、用药、服务推荐）
- [ ] 推荐结果聚合

### 阶段 5：前端开发 (Week 11-13)
- [ ] 聊天界面（WebSocket）
- [ ] 个性化页面渲染
- [ ] 状态管理

### 阶段 6：测试和优化 (Week 14-15)
- [ ] 单元测试
- [ ] 集成测试
- [ ] E2E 测试
- [ ] 性能优化
- [ ] DSPy 提示词优化

### 阶段 7：部署和上线 (Week 16)
- [ ] 生产环境配置
- [ ] 数据迁移
- [ ] 灰度发布
- [ ] 监控告警配置

### Rollback 策略
- 保留旧系统并行运行
- 新系统出现严重问题时快速切换回旧系统
- 数据库迁移采用双写策略，确保数据安全

## Open Questions

1. **健康档案系统接口规范**
   - 问题：外部 Java 服务的具体接口文档尚未确认
   - 影响：MCP Server 实现依赖接口规范
   - 解决方案：需与相关团队确认接口文档

2. **DSPy 优化数据来源**
   - 问题：提示词优化需要多少训练数据
   - 影响：Skills 优化效果依赖数据质量
   - 解决方案：先使用规则库作为 baseline，逐步收集优化数据

3. **模型配额管理**
   - 问题：各模型的调用配额如何管理
   - 影响：可能影响服务可用性
   - 解决方案：实现配额监控和自动降级机制

4. **前端技术栈选择**
   - 问题：前端框架（React/Vue）尚未确定
   - 影响：前端开发计划
   - 解决方案：需与前端团队协商确定
