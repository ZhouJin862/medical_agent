# 聊天交互界面能力规格

## ADDED Requirements

### Requirement: 聊天消息发送
系统 SHALL 允许健管师通过聊天界面发送消息给智能体。

#### Scenario: 发送健康咨询消息
- **WHEN** 健管师在聊天界面输入"评估张三的高血压风险"并发送
- **THEN** 系统将消息通过 WebSocket 发送到后端
- **THEN** 系统在界面显示"正在分析..."状态

### Requirement: 聊天消息接收
系统 SHALL 接收并显示智能体的响应消息。

#### Scenario: 接收健康评估结果
- **WHEN** 智能体完成健康评估分析
- **THEN** 系统在聊天界面显示自然语言回复
- **THEN** 系统在个性化展示区渲染结构化数据（健康画像、风险等级等）

### Requirement: 结构化数据渲染
系统 SHALL 根据智能体返回的结构化数据动态渲染个性化页面。

#### Scenario: 渲染健康画像
- **WHEN** 智能体返回包含 `health_profile` 类型的结构化数据
- **THEN** 系统渲染雷达图显示患者各项健康指标
- **THEN** 系统用不同颜色区分正常/异常指标

#### Scenario: 渲染风险预测
- **WHEN** 智能体返回包含 `risk_prediction` 类型的结构化数据
- **THEN** 系统渲染进度条或仪表盘显示风险等级
- **THEN** 系统显示具体的风险数值和解释

#### Scenario: 渲染健康方案
- **WHEN** 智能体返回包含处方类型的结构化数据
- **THEN** 系统以卡片形式展示饮食、运动等处方
- **THEN** 每个卡片包含具体可执行的建议

#### Scenario: 渲染分诊推荐
- **WHEN** 智能体返回包含 `triage` 类型的结构化数据
- **THEN** 系统渲染医院列表，显示医院名称、科室和医生信息

### Requirement: WebSocket 连接管理
系统 SHALL 维护与后端的 WebSocket 连接。

#### Scenario: 建立连接
- **WHEN** 健管师打开聊天页面
- **THEN** 系统自动建立 WebSocket 连接
- **THEN** 连接成功后显示"在线"状态

#### Scenario: 连接断开重连
- **WHEN** WebSocket 连接意外断开
- **THEN** 系统自动尝试重新连接
- **THEN** 显示"重连中..."状态

### Requirement: 对话上下文保持
系统 SHALL 在单次会话中保持对话上下文。

#### Scenario: 多轮对话上下文
- **WHEN** 健管师首先输入"评估张三"，然后继续输入"他的饮食要注意什么"
- **THEN** 系统能识别"他"指的是"张三"
- **THEN** 系统能基于之前的评估结果生成饮食建议

### Requirement: 输入提示
系统 SHALL 支持健管师快速输入常用指令。

#### Scenario: Skill 快捷指令
- **WHEN** 健管师输入 "@" 符号
- **THEN** 系统弹出可用的 Skill 列表（如 @hypertension_assessment）
- **WHEN** 健管师选择 Skill 并输入参数
- **THEN** 系统直接调用指定 Skill

### Requirement: 消息历史
系统 SHALL 显示当前会话的对话历史。

#### Scenario: 查看历史消息
- **WHEN** 健管师刷新页面或重新进入会话
- **THEN** 系统加载并显示该会话的历史消息
- **THEN** 消息按时间倒序排列
