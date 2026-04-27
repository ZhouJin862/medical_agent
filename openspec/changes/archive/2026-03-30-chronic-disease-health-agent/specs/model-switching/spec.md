# 模型切换能力规格

## ADDED Requirements

### Requirement: 多模型支持
系统 SHALL 支持多种大语言模型的切换。

#### Scenario: 使用司内模型
- **WHEN** 配置指定使用司内模型
- **THEN** 系统使用 GLM-5 模型
- **THEN** 系统调用智谱 API 端点

#### Scenario: 使用 OpenAI 模型
- **WHEN** 配置指定使用 OpenAI
- **THEN** 系统使用 GPT-4 等模型
- **THEN** 系统调用 OpenAI API 端点

#### Scenario: 使用 Anthropic 模型
- **WHEN** 配置指定使用 Anthropic
- **THEN** 系统使用 Claude 模型
- **THEN** 系统调用 Anthropic API 端点

### Requirement: 配置驱动的模型切换
系统 SHALL 通过配置文件控制模型选择。

#### Scenario: 默认模型配置
- **WHEN** 系统启动时
- **THEN** 系统加载 model_config.yaml 配置
- **THEN** 系统使用配置中指定的默认模型

#### Scenario: 按用户/租户切换
- **WHEN** 不同客户配置了不同的模型
- **THEN** 系统根据用户ID使用对应模型
- **THEN** 系统 A 使用司内模型，客户 B 使用 OpenAI

### Requirement: Skill 级别的模型配置
系统 SHALL 支持为不同 Skill 配置不同的模型。

#### Scenario: Skill 使用指定模型
- **WHEN** Skill 配置中指定了 model_provider
- **THEN** 该 Skill 使用指定的模型
- **THEN** 其他 Skill 使用默认模型

#### Scenario: 敏感数据使用司内模型
- **WHEN** 处理包含敏感患者数据的 Skill
- **THEN** 系统自动使用司内部署的模型
- **THEN** 敏感数据不发送到外部 API

### Requirement: 模型参数配置
系统 SHALL 支持配置模型参数。

#### Scenario: 配置 temperature
- **WHEN** Skill 需要确定性输出
- **THEN** 系统配置低 temperature (如 0.3)
- **WHEN** Skill 需要创造性输出
- **THEN** 系统配置高 temperature (如 0.8)

#### Scenario: 配置 max_tokens
- **WHEN** Skill 需要简短回复
- **THEN** 系统配置较小的 max_tokens (如 500)
- **WHEN** Skill 需要详细分析
- **THEN** 系统配置较大的 max_tokens (如 2000)

### Requirement: 模型降级策略
系统 SHALL 在主模型失败时自动降级。

#### Scenario: 主模型超时
- **WHEN** 调用主模型超时
- **THEN** 系统自动切换到备用模型
- **THEN** 系统记录降级日志

#### Scenario: 主模型限流
- **WHEN** 主模型返回 API 限流错误
- **THEN** 系统切换到其他可用模型
- **THEN** 系统确保服务不中断

### Requirement: 模型使用统计
系统 SHALL 记录模型使用情况。

#### Scenario: 记录调用次数
- **WHEN** 系统调用模型
- **THEN** 系统记录模型名称、调用时间、token消耗

#### Scenario: 统计分析
- **WHEN** 管理员查看模型使用统计
- **THEN** 系统展示各模型的调用量和成本
