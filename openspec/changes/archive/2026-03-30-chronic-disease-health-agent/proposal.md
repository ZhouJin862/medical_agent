# 慢病健康管理智能体系统

## Why

当前健康档案系统缺乏智能化的健康评估和管理能力，健管师需要手工分析患者数据，效率低且易遗漏风险。随着"四高一重"（高血压、高血糖、高血脂、高尿酸、肥胖）慢病患者数量持续增长，亟需引入 AI 智能体实现自动化健康评估、风险预测和个性化健康方案生成。

## What Changes

### 核心功能
- **聊天交互式界面**：健管师通过自然语言与智能体交互，获取健康评估和管理建议
- **四高一重专项评估**：针对高血压、糖尿病、高血脂、痛风/高尿酸、肥胖的专项健康评估和风险管理
- **个性化健康方案生成**：自动生成饮食、运动、睡眠、用药等处方
- **分诊导医服务**：高风险患者智能推荐医院、科室和医生
- **合理用药校验**：用药适应症和用量校验，推荐合理用药方案
- **保险及服务推荐**：推荐司内保险产品和医健服务

### 技术架构
- **DDD 架构**：清晰分层（接口层、应用层、领域层、基础设施层）
- **LangGraph 工作流**：编排智能体处理流程（检索记忆→意图识别→Skill执行→结果聚合）
- **DSPy Skills**：数据库动态加载、可组合的技能模块
- **MCP 集成**：调用外部 Java 服务（分诊、用药、服务推荐、健康档案）
- **模型动态切换**：配置驱动，支持司内/外部模型切换
- **Mem0 记忆**：患者上下文长期记忆

## Capabilities

### New Capabilities
- `chat-interface`: 聊天交互界面，支持 WebSocket 实时通信和结构化输出渲染
- `health-assessment`: 健康评估能力，综合评估患者健康状况，生成健康画像
- `risk-prediction`: 风险预测能力，预测患病率、恶化率、并发症、失能率、残疾率、死亡率、医疗成本
- `health-promotion`: 健康促进能力，生成饮食、运动、睡眠、心理干预处方和保健品推荐
- `triage-guidance`: 分诊导医能力，推荐科室、医生和医院
- `medication-check`: 合理用药能力，适应症校验、用量校验、用药方案推荐
- `service-recommendation`: 服务推荐能力，推荐保险产品和医健服务
- `skill-management`: Skill 管理能力，动态加载、启用/禁用、优化 Skills
- `patient-data-mcp`: 患者数据 MCP，通过 MCP 协议从健康档案系统获取患者数据
- `model-switching`: 模型切换能力，配置驱动的多模型支持

### Modified Capabilities
- *None (new system)*

## Impact

### 技术影响
- **新增依赖**：LangGraph、DSPy、Mem0、MCP SDK、FastAPI、SQLAlchemy
- **数据库**：MySQL 新增对话历史、健康方案、Skills 配置表
- **MCP Servers**：4 个独立进程的 MCP Servers（profile、triage、medication、service）
- **外部集成**：与现有 Java 服务（健康档案、分诊导医、合理用药、服务推荐）集成

### API 影响
- **新增 API**：
  - `POST /api/chat` - 聊天接口
  - `GET /api/health/:patient_id` - 健康评估
  - `GET /api/plan/:patient_id` - 健康方案
  - `GET /api/skills` - Skill 列表
  - `POST /api/skills` - 创建 Skill
  - `POST /api/skills/{id}/reload` - 热重载 Skills
- **WebSocket**：`/ws/chat` 实时聊天

### 成功指标
- 健康评估准确率 > 85%
- 聊天响应时间 < 3 秒
- Skill 动态加载成功率 > 99%
- 测试覆盖率 > 80%
