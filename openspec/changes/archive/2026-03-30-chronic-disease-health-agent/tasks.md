# 慢病健康管理智能体系统 - 实现任务

## 1. 项目基础设施搭建

- [x] 1.1 创建 DDD 四层项目目录结构（interface/application/domain/infrastructure）
- [x] 1.2 配置 Pydantic Settings 和环境变量管理
- [x] 1.3 配置日志系统和中间件
- [x] 1.4 初始化 Alembic 数据库迁移
- [x] 1.5 编写 Docker Compose 配置（MySQL + Redis + 应用）

## 2. 数据库设计与实现

- [x] 2.1 创建 SQLAlchemy 基础模型（Base、公共字段）
- [x] 2.2 实现 consultations 表和 ORM 模型
- [x] 2.3 实现 messages 表和 ORM 模型
- [x] 2.4 实现 health_plans 表和 ORM 模型
- [x] 2.5 实现 prescriptions 表和 ORM 模型
- [x] 2.6 实现 disease_types 表并插入四高一重数据
- [x] 2.7 实现 skills 相关表（skills, skill_prompts, skill_model_configs）
- [x] 2.8 实现 knowledge_bases 表
- [x] 2.9 实现 vital_signs_standards 表并插入四高一重标准数据
- [x] 2.10 编写数据库迁移脚本
- [x] 2.11 编写 Repository 接口和实现（Consultation, HealthPlan）

## 3. 领域层实现 - 共享内核

- [x] 3.1 实现 PatientData 值对象
- [x] 3.2 实现 VitalSigns 值对象及其子类（BloodPressure, BloodGlucose, LipidProfile, UricAcid, BMI）
- [x] 3.3 实现 DiseaseType 枚举和值对象
- [x] 3.4 实现 RiskLevel 枚举和值对象
- [x] 3.5 实现 ContextSnapshot 值对象
- [x] 3.6 编写共享内核的单元测试

## 4. 领域层实现 - Consultation 上下文

- [x] 4.1 实现 Consultation 聚合根
- [x] 4.2 实现 Message 实体
- [x] 4.3 实现 ConsultationStatus 和 IntentType 值对象
- [x] 4.4 实现 MessageContent 值对象
- [x] 4.5 实现 IntentRecognitionService 领域服务
- [x] 4.6 定义领域事件（MessageReceived, ConversationCompleted）
- [x] 4.7 编写 Consultation 聚合根的单元测试

## 5. 领域层实现 - HealthPlan 上下文

- [x] 5.1 实现 HealthPlan 聚合根
- [x] 5.2 实现 Prescription 基类
- [x] 5.3 实现 DietPrescription 实体
- [x] 5.4 实现 ExercisePrescription 实体
- [x] 5.5 实现 SleepPrescription 实体
- [x] 5.6 实现 MedicationPrescription 实体
- [x] 5.7 实现 PsychologicalPrescription 实体
- [x] 5.8 定义领域事件（HealthPlanGenerated）
- [x] 5.9 编写 HealthPlan 聚合根的单元测试

## 6. 领域层实现 - Recommendation 上下文

- [x] 6.1 实现 TriageRecommendation 值对象
- [x] 6.2 实现 MedicationRecommendation 值对象
- [x] 6.3 实现 ServiceRecommendation 值对象
- [x] 6.4 实现 Hospital, Department, Doctor 值对象
- [x] 6.5 实现 RecommendationAggregationService 领域服务

## 7. 基础设施层 - LLM 服务

- [x] 7.1 实现 LLMFactory 支持多模型切换
- [x] 7.2 实现 AnthropicLLM 适配器（GLM-5）
- [x] 7.3 实现 OpenAILLM 适配器
- [x] 7.4 编写 LLM 切换的单元测试
- [x] 7.5 实现模型降级策略

## 8. 基础设施层 - 记忆服务

- [x] 8.1 实现 Mem0Adapter
- [x] 8.2 实现记忆存储、检索、搜索功能
- [x] 8.3 编写记忆服务的集成测试

## 9. 基础设施层 - MCP 客户端

- [x] 9.1 实现 MCPClientFactory
- [x] 9.2 实现 BaseMCPClient
- [x] 9.3 实现 ProfileMCPClient（健康档案）
- [x] 9.4 实现 TriageMCPClient（分诊导医）
- [x] 9.5 实现 MedicationMCPClient（合理用药）
- [x] 9.6 实现 ServiceMCPClient（服务推荐）
- [x] 9.7 编写 MCP 客户端的集成测试

## 10. MCP Servers 实现

- [x] 10.1 实现 profile_server（健康档案 MCP Server）
- [x] 10.2 实现 triage_server（分诊导医 MCP Server）
- [x] 10.3 实现 medication_server（合理用药 MCP Server）
- [x] 10.4 实现 service_server（服务推荐 MCP Server）
- [x] 10.5 实现 MCP Servers 的启动脚本
- [x] 10.6 编写 MCP Servers 的健康检查端点

## 11. 基础设施层 - DSPy Skills

- [x] 11.1 实现 DSPy Signatures（base.py, four_highs.py, prescription.py）
- [x] 11.2 实现 SkillRegistry（从数据库动态加载）
- [x] 11.3 实现 SkillFactory
- [x] 11.4 实现 BaseSkill

## 12. DSPy Skills - 通用 Skills

- [x] 12.1 实现 HealthAssessmentSkill（通用健康评估）
- [x] 12.2 实现 RiskPredictionSkill（风险预测）
- [x] 12.3 实现 HealthProfileSkill（健康画像）
- [x] 12.4 编写通用 Skills 的单元测试

## 13. DSPy Skills - 四高一重专用 Skills

- [x] 13.1 实现 HypertensionSkill（高血压评估）
- [x] 13.2 实现 DiabetesSkill（糖尿病评估）
- [x] 13.3 实现 DyslipidemiaSkill（血脂评估）
- [x] 13.4 实现 GoutSkill（痛风评估）
- [x] 13.5 实现 ObesitySkill（肥胖评估）
- [x] 13.6 实现 MetabolicSyndromeSkill（代谢综合征）
- [x] 13.7 编写病种 Skills 的单元测试

## 14. DSPy Skills - 处方 Skills

- [x] 14.1 实现 DietPrescriptionSkill（饮食处方）
- [x] 14.2 实现 ExercisePrescriptionSkill（运动处方）
- [x] 14.3 实现 SleepPrescriptionSkill（睡眠处方）
- [x] 14.4 实现 MedicationPrescriptionSkill（用药处方）
- [x] 14.5 编写处方 Skills 的单元测试

## 15. DSPy Skills - MCP Tool Skills

- [x] 15.1 实现 TriageGuidanceSkill（分诊导医，调用 MCP）
- [x] 15.2 实现 MedicationCheckSkill（合理用药，调用 MCP）
- [x] 15.3 实现 ServiceRecommendSkill（服务推荐，调用 MCP）
- [x] 15.4 编写 MCP Tool Skills 的集成测试

## 16. 基础设施层 - LangGraph 工作流

- [x] 16.1 定义 AgentState
- [x] 16.2 实现 load_patient 节点（调用 MCP）
- [x] 16.3 实现 retrieve_memory 节点（调用 Mem0）
- [x] 16.4 实现 classify_intent 节点（支持 @skill_name）
- [x] 16.5 实现 route_skill 节点（条件路由）
- [x] 16.6 实现 aggregate_results 节点
- [x] 16.7 实现 save_memory 节点
- [x] 16.8 构建完整工作流图
- [x] 16.9 编写工作流的集成测试

## 17. 应用层服务

- [x] 17.1 实现 ChatApplicationService
- [x] 17.2 实现 HealthAssessmentApplicationService
- [x] 17.3 实现 HealthPlanApplicationService
- [x] 17.4 实现 SkillManagementApplicationService
- [x] 17.5 实现 Command 和 Query 定义
- [x] 17.6 实现 CommandHandlers 和 QueryHandlers
- [x] 17.7 编写应用服务的集成测试

## 18. 接口层 - REST API

- [x] 18.1 实现 FastAPI 应用入口和依赖注入
- [x] 18.2 实现 ChatController（POST /api/chat）
- [x] 18.3 实现 HealthController（GET /api/health/:patient_id）
- [x] 18.4 实现 PlanController（GET /api/plan/:patient_id）
- [x] 18.5 实现 ConsultationController（查询对话历史）
- [x] 18.6 实现 SkillController（Skill CRUD）
- [x] 18.7 实现 Request/Response DTOs
- [x] 18.8 实现认证和授权中间件
- [x] 18.9 实现错误处理中间件
- [x] 18.10 实现流式聊天 API (SSE)
- [x] 18.11 实现会话管理 (SessionManager)
- [x] 18.12 编写 API 的集成测试

## 19. 接口层 - WebSocket

- [x] 19.1 实现 WebSocketHandler
- [x] 19.2 实现 ConnectionManager
- [x] 19.3 实现消息广播功能
- [x] 19.4 实现会话状态同步
- [x] 19.5 编写 WebSocket 的集成测试

## 20. 前端实现

- [x] 20.1 搭建前端项目框架
- [x] 20.2 实现聊天界面组件
- [x] 20.3 实现 WebSocket 连接管理
- [x] 20.4 实现消息展示和发送功能
- [x] 20.5 实现个性化页面渲染（健康画像雷达图）
- [x] 20.6 实现风险预测图表渲染
- [x] 20.7 实现处方卡片展示
- [x] 20.8 实现分诊推荐列表展示
- [x] 20.9 实现 Skill 快捷输入功能
- [x] 20.10 实现消息历史加载
- [x] 20.11 编写前端组件的单元测试

## 21. Skill 管理功能

- [x] 21.1 实现 Skill CRUD API
- [x] 21.2 实现 Skill 启用/禁用功能
- [x] 21.3 实现 Skill 热重载功能
- [x] 21.4 实现意图关键词配置
- [x] 21.5 实现知识库关联配置
- [x] 21.6 实现 Skill 管理前端页面

## 22. 知识库和提示词管理

- [x] 22.1 插入四高一重防治指南数据
- [x] 22.2 插入体征指标标准数据
- [x] 22.3 实现 Skill 提示词模板
- [x] 22.4 实现知识库查询服务

## 23. DSPy Skills 优化

- [x] 23.1 实现 SkillOptimizer（DSPy Teleprompter）
- [x] 23.2 收集优化训练数据
- [x] 23.3 优化高血压评估 Skill 提示词
- [x] 23.4 优化糖尿病评估 Skill 提示词
- [x] 23.5 优化风险评估 Skill 提示词

## 24. 测试和质量保证

- [x] 24.1 编写端到端测试（E2E）场景
- [x] 24.2 实现性能测试（响应时间 < 3秒）
- [x] 24.3 实现负载测试
- [x] 24.4 测试覆盖率检查（> 80%）
- [x] 24.5 安全测试（数据隐私、认证授权）

## 25. 部署和运维

- [x] 25.1 编写 Docker 镜像构建脚本
- [x] 25.2 编写 Kubernetes 部署配置
- [x] 25.3 配置 Prometheus + Grafana 监控
- [x] 25.4 配置日志收集（ELK）
- [x] 25.5 编写部署文档
- [x] 25.6 实现灰度发布流程

## 26. 文档和培训

- [x] 26.1 编写 API 文档
- [x] 26.2 编写 Skill 开发指南
- [x] 26.3 编写运维手册
- [x] 26.4 编写用户使用手册
