# 患者数据 MCP 能力规格

## ADDED Requirements

### Requirement: 患者档案查询
系统 SHALL 通过 MCP 协议从健康档案系统获取患者基本信息。

#### Scenario: 获取患者基本信息
- **WHEN** 系统需要患者ID为"P001"的患者信息
- **THEN** 系统 MCP 客户端调用 profile_server 的 get_patient_profile 工具
- **THEN** 系统返回患者的姓名、性别、年龄等信息

#### Scenario: 获取患者体征数据
- **WHEN** 系统需要患者的体征指标
- **THEN** 系统 MCP 客户端调用 get_vital_signs 工具
- **THEN** 系统返回血压、血糖、血脂、尿酸、BMI等数据

#### Scenario: 获取患者医疗记录
- **WHEN** 系统需要患者的病史信息
- **THEN** 系统 MCP 客户端调用 get_medical_records 工具
- **THEN** 系统返回患者的诊断记录、手术史等

#### Scenario: 获取患者检验结果
- **WHEN** 系统需要患者的实验室检验数据
- **THEN** 系统 MCP 客户端调用 get_lab_results 工具
- **THEN** 系统返回血常规、生化检查等检验数据

### Requirement: MCP 通信
系统 SHALL 通过标准 MCP 协议与外部服务通信。

#### Scenario: 建立 MCP 连接
- **WHEN** 系统启动时
- **THEN** 系统 MCP 客户端连接到 profile_server
- **THEN** 系统支持通过 stdio 或 SSE 方式通信

#### Scenario: 调用 MCP 工具
- **WHEN** 系统需要调用 MCP 工具
- **THEN** 系统 MCP 客户端发送标准格式的请求
- **THEN** 系统 MCP 客户端接收并解析响应

### Requirement: 数据缓存策略
系统 SHALL 支持患者数据的会话级缓存。

#### Scenario: 首次获取数据
- **WHEN** 会话中首次查询患者数据
- **THEN** 系统 MCP 客户端调用外部接口获取数据
- **THEN** 系统将数据缓存到会话上下文

#### Scenario: 使用缓存数据
- **WHEN** 同一会话中再次查询同一患者数据
- **THEN** 系统优先使用缓存的 ContextSnapshot
- **THEN** 系统减少不必要的 MCP 调用

#### Scenario: 数据失效
- **WHEN** 会话结束后
- **THEN** 系统清除该会话的数据缓存

### Requirement: 错误处理
系统 SHALL 处理 MCP 调用失败的情况。

#### Scenario: MCP 服务不可用
- **WHEN** profile_server 无响应
- **THEN** 系统记录错误日志
- **THEN** 系统返回友好的错误提示给用户

#### Scenario: 患者数据不存在
- **WHEN** 查询的患者ID在档案系统中不存在
- **THEN** 系统 MCP 客户端返回空结果
- **THEN** 系统提示用户检查患者ID
