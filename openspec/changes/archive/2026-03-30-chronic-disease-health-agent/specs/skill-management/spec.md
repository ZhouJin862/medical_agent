# Skill 管理能力规格

## ADDED Requirements

### Requirement: Skill 动态加载
系统 SHALL 从数据库动态加载 Skills，无需重启服务。

#### Scenario: 启动时加载 Skills
- **WHEN** 系统启动时
- **THEN** 系统从数据库加载所有 enabled=true 的 Skills
- **THEN** 系统注册 Skill 到 SkillRegistry

#### Scenario: 热重载 Skills
- **WHEN** 管理员调用重载接口
- **THEN** 系统重新从数据库加载 Skills
- **THEN** 新增的 Skills 立即可用，删除的 Skills 停止服务

### Requirement: Skill CRUD 操作
系统 SHALL 支持 Skills 的增删改查操作。

#### Scenario: 创建新 Skill
- **WHEN** 管理员创建新 Skill
- **THEN** 系统保存 Skill 配置到数据库
- **THEN** 系统支持设置 Skill 名称、类型、分类、提示词等

#### Scenario: 更新 Skill
- **WHEN** 管理员修改 Skill 配置
- **THEN** 系统更新数据库中的 Skill 记录
- **THEN** 系统支持修改提示词、模型配置等

#### Scenario: 删除 Skill
- **WHEN** 管理员删除 Skill
- **THEN** 系统将 Skill 标记为 enabled=false
- **THEN** 系统不再加载该 Skill

#### Scenario: 查询 Skills
- **WHEN** 管理员查询 Skill 列表
- **THEN** 系统返回所有 Skills 的信息
- **THEN** 系统支持按类型、分类、状态筛选

### Requirement: Skill 启用/禁用
系统 SHALL 支持 Skill 的启用和禁用。

#### Scenario: 启用 Skill
- **WHEN** 管理员启用一个 Skill
- **THEN** 系统设置 enabled=true
- **THEN** 下次重载后该 Skill 可用

#### Scenario: 禁用 Skill
- **WHEN** 管理员禁用一个 Skill
- **THEN** 系统设置 enabled=false
- **THEN** 智能体不再调用该 Skill

### Requirement: Skill 配置管理
系统 SHALL 支持 Skill 的各项配置。

#### Scenario: 配置提示词
- **WHEN** 管理员配置 Skill 提示词
- **THEN** 系统支持 system_prompt、user_template、knowledge 三种类型
- **THEN** 系统支持多语言提示词

#### Scenario: 配置模型
- **WHEN** 管理员配置 Skill 使用的模型
- **THEN** 系统支持选择模型提供商（internal/openai/glm）
- **THEN** 系统支持设置 temperature、max_tokens 等参数

#### Scenario: 配置知识库
- **WHEN** 管理员关联知识库到 Skill
- **THEN** 系统支持选择一个或多个知识库
- **THEN** 系统支持设置知识库优先级

### Requirement: Skill 意图映射
系统 SHALL 支持 Skill 与意图关键词的映射。

#### Scenario: 配置意图关键词
- **WHEN** 管理员为 Skill 配置意图关键词
- **THEN** 系统支持添加多个关键词
- **THEN** 系统支持设置正则表达式模式

#### Scenario: 意图识别
- **WHEN** 用户的查询匹配意图关键词
- **THEN** 系统路由到对应的 Skill
- **THEN** 系统支持 @skill_name 显式指定

### Requirement: Skill 优化
系统 SHALL 支持 DSPy 优化 Skills。

#### Scenario: 优化 Skill 提示词
- **WHEN** 管理员提供训练数据
- **THEN** 系统使用 DSPy Teleprompter 优化提示词
- **THEN** 系统保存优化后的提示词版本
