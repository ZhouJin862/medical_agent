# 技能分类标准与存储策略

## 技能分类标准

### 文件系统技能 (Claude Skills)

**适用场景**:
- ✅ 通用医学知识
- ✅ 标准临床指南
- ✅ 跨机构通用的评估流程
- ✅ 开源共享的技能
- ✅ 相对稳定的内容

**示例**:
```
skills/
├── hypertension-risk-assessment/      # 高血压风险评估 (标准指南)
├── hyperglycemia-risk-assessment/     # 高血糖风险评估 (标准指南)
├── hyperlipidemia-risk-assessment/    # 高血脂风险评估 (标准指南)
├── hyperuricemia-risk-assessment/     # 高尿酸风险评估 (标准指南)
├── obesity-risk-assessment/           # 肥胖风险评估 (标准指南)
├── chronic-disease-risk-assessment/   # 慢性病综合风险评估 (标准指南)
├── medication-reminder/                # 用药提醒 (通用)
└── health-education/                   # 健康教育 (通用内容)
```

**特点**:
- 文件系统存储: `skills/{skill-name}/SKILL.md`
- 版本控制: Git 管理
- 内容开放: 可开源共享
- 更新频率: 低 (医学指南更新较慢)

---

### 数据库技能 (Enterprise Skills)

**适用场景**:
- ✅ 企业定制流程
- ✅ 个性化配置
- ✅ 动态业务规则
- ✅ 需要API管理的技能
- ✅ 包含私有数据的技能

**示例**:
```
database_skills/
├── custom_bp_assessment/         # 定制血压评估流程
├── hospital_triage/              # 医院分诊流程
├── personalized_report/          # 个性化报告生成
├── insurance_assessment/         # 保险评估
├── vip_health_plan/              # VIP健康计划
└── custom_medication_check/      # 定制用药检查
```

**数据库表结构**:
```sql
CREATE TABLE enterprise_skills (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    skill_type ENUM('standard', 'custom') DEFAULT 'custom',

    -- 业务配置
    business_rules JSON,              -- 业务规则
    workflow_config JSON,             -- 工作流配置
    customization_params JSON,         -- 个性化参数

    -- 引用文件技能 (可组合)
    base_skills JSON,                 -- 引用的基础技能列表
    override_settings JSON,           -- 覆盖设置

    -- 权限控制
    tenant_id VARCHAR(50),
    access_level ENUM('public', 'private', 'restricted'),

    -- 状态
    enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by VARCHAR(100),

    INDEX idx_tenant_type (tenant_id, skill_type)
);
```

---

## 混合执行策略

### 执行优先级

```
请求处理: "VIP用户做综合健康评估"

1. 检查数据库技能
   → 找到: vip_health_plan (定制)

2. vip_health_plan 配置:
   - base_skills: ["hypertension-risk-assessment", "hyperglycemia-risk-assessment"]
   - override_settings: {"response_style": "vip_detailed"}

3. 执行流程:
   ┌─────────────────────────────────────────────────────┐
   │ 1. 加载文件技能 (基础层)                            │
   │    → hypertension-risk-assessment/SKILL.md           │
   │    → hyperglycemia-risk-assessment/SKILL.md          │
   │    → obesity-risk-assessment/SKILL.md                 │
   │                                                          │
   │ 2. 应用数据库技能 (定制层)                          │
   │    → vip_health_plan 的业务规则                     │
   │    → 个性化参数                                       │
   │    → 覆盖响应样式                                     │
   │                                                          │
   │ 3. 组合输出                                            │
   │    → 基础评估 (标准) + VIP 个性化建议                  │
   └─────────────────────────────────────────────────────┘
```

---

## 技能组合机制

### 数据库技能组合文件技能

```yaml
# enterprise_skill: vip_health_plan

# 引用基础技能
base_skills:
  - hypertension-risk-assessment
  - hyperglycemia-risk-assessment
  - hyperlipidemia-risk-assessment
  - obesity-risk-assessment

# 覆盖设置
overrides:
  response_style: "vip_detailed"
  include_recommendations: true
  add_personal_notes: true

# 业务规则
business_rules:
  priority_queue: true
  dedicated_specialist: true
  follow_up_reminder: true

# 工作流配置
workflow:
  steps:
    - name: comprehensive_assessment
      skills: ["hypertension-risk-assessment", "hyperglycemia-risk-assessment"]
    - name: personalized_plan
      template: "vip_health_plan_template"
    - name: specialist_consultation
      trigger: "risk_level == high"
```

---

## 具体实施

### 1. 保持现有两套系统

```python
# skills/ - 文件系统 (通用技能)
hypertension-risk-assessment/SKILL.md
hyperglycemia-risk-assessment/SKILL.md
hyperlipidemia-risk-assessment/SKILL.md
hyperuricemia-risk-assessment/SKILL.md
obesity-risk-assessment/SKILL.md
chronic-disease-risk-assessment/SKILL.md
...

# database - 数据库技能 (个性化技能)
enterprise_skills 表
```

### 2. 扩展 UnifiedSkillsRepository

```python
class UnifiedSkillsRepository:

    async def get_composite_skill(
        self,
        enterprise_skill_name: str
    ) -> CompositeSkillDefinition:
        """
        获取组合技能定义

        1. 加载数据库技能配置
        2. 加载引用的基础技能
        3. 合并配置和内容
        """
        # 加载企业技能
        enterprise_skill = await self._load_enterprise_skill(name)

        # 加载基础技能
        base_skills = []
        for skill_name in enterprise_skill.base_skills:
            base_skill = await self.get_skill(skill_name)
            base_skills.append(base_skill)

        # 合并
        return CompositeSkillDefinition(
            enterprise=enterprise_skill,
            base_skills=base_skills,
            merged_config=self._merge_configs(enterprise_skill, base_skills)
        )
```

### 3. Agent 执行逻辑

```python
async def execute_skill_with_priority(state: AgentState):
    """
    按优先级执行技能

    1. 先检查是否有匹配的企业定制技能
    2. 如果没有，使用通用技能
    3. 组合技能需要合并执行
    """
    # 1. 检查企业技能
    enterprise_skill = await find_enterprise_skill(
        user_id=state.patient_id,
        intent=state.intent
    )

    if enterprise_skill:
        # 组合执行
        return await execute_composite_skill(enterprise_skill, state)

    # 2. 使用通用技能
    return await execute_claude_skill(state.suggested_skill, state)
```

---

## 总结

### 推荐架构

| 技能类型 | 存储位置 | 管理方式 | 更新频率 |
|---------|---------|---------|---------|
| **通用技能** | 文件系统 (Claude Skills) | 文件编辑 + Git | 低 (季度/年) |
| **个性化技能** | 数据库 (Enterprise Skills) | API + Web界面 | 高 (实时) |
| **组合技能** | 数据库 (引用文件技能) | API 组合配置 | 中 |

### 优势

1. **灵活性** - 通用知识标准化，个性化需求可定制
2. **可维护性** - 通用技能版本控制，定制技能 API 管理
3. **可扩展性** - 新增通用技能无需改代码
4. **兼容性** - 保持现有投资，平滑演进

### 是否需要改造？

**不需要大改**，只需：

1. ✅ **明确分类标准** - 制定技能分类指南
2. ✅ **扩展组合机制** - 支持数据库技能引用文件技能
3. ✅ **优化执行逻辑** - 按优先级执行
4. ✅ **前端分层** - 通用技能固定展示，定制技能可编辑

**当前的 UnifiedSkillsRepository 已经支持**，只需要补充组合执行逻辑。

---

这个方案是否更符合你的需求？需要我实现组合执行逻辑吗？
