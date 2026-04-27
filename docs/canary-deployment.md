# 灰度发布指南 (Canary Deployment Guide)

本文档介绍 Medical Agent 的灰度发布流程和最佳实践。

## 目录

- [概述](#概述)
- [发布策略](#发布策略)
- [灰度发布流程](#灰度发布流程)
- [监控和验证](#监控和验证)
- [回滚程序](#回滚程序)
- [最佳实践](#最佳实践)

## 概述

### 什么是灰度发布？

灰度发布（Canary Deployment）是一种渐进式发布策略，新版本先部署到少量实例，接收少量流量，验证无误后再逐步扩大流量。

### 为什么使用灰度发布？

- **降低风险**：新版本问题只影响少量用户
- **快速反馈**：可以在生产环境验证新版本
- **平滑过渡**：逐步切换而非一次性切换
- **易于回滚**：问题发现后可以快速回滚

### 发布策略对比

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 滚动更新 | 简单 | 难以验证 | 小版本更新 |
| 蓝绿部署 | 快速切换 | 资源消耗大 | 重大版本 |
| 灰度发布 | 风险最低 | 配置复杂 | 生产环境 |

## 发布策略

### 阶段 1: 准备阶段

**Pre-deployment 检查清单：**

```bash
# 1. 测试新版本
pytest -xvs tests/e2e/

# 2. 性能测试
python scripts/run_performance_tests.py

# 3. 安全扫描
bandit -r src/

# 4. 构建镜像
./scripts/docker_build.sh --tag v1.1.0
```

### 阶段 2: 灰度阶段

**流量分配策略：**

| 阶段 | 流量比例 | 持续时间 | 验证项 |
|------|----------|----------|--------|
| 初始 | 10% | 5 分钟 | 无错误，延迟正常 |
| 扩大 | 25% | 5 分钟 | 无错误，延迟 < 基线 |
| 扩大 | 50% | 10 分钟 | 无错误，延迟 < 基线 |
| 扩大 | 75% | 10 分钟 | 无错误，延迟 < 基线 |
| 完成 | 100% | - | 全量切换 |

### 阶段 3: 验证阶段

**关键指标监控：**

- 错误率 < 1%
- P95 延迟 < 基线 × 1.2
- P99 延迟 < 基线 × 1.5
- 资源使用正常
- 无异常日志

## 灰度发布流程

### 自动化流程

使用提供的脚本：

```bash
# 完全自动化流程
./scripts/canary_deploy.sh \
  --image medical-agent:v1.1.0 \
  --traffic 10

# 交互式流程
./scripts/canary_deploy.sh --interactive
```

### 手动流程

#### 步骤 1: 部署 Canary 版本

```bash
# 更新 canary deployment
kubectl set image deployment/medical-agent-canary \
  medical-agent=medical-agent:v1.1.0 \
  -n medical-agent

# 检查部署状态
kubectl rollout status deployment/medical-agent-canary -n medical-agent
kubectl get pods -n medical-agent -l variant=canary
```

#### 步骤 2: 初始流量切换 (10%)

```bash
# 调整副本数比例
kubectl scale deployment/medical-agent-primary --replicas=3 -n medical-agent
kubectl scale deployment/medical-agent-canary --replicas=1 -n medical-agent

# 验证流量分配
kubectl get pods -n medical-agent -l app=medical-agent
```

#### 步骤 3: 监控和验证

```bash
# 查看 canary 日志
kubectl logs -f deployment/medical-agent-canary -n medical-agent

# 查看 canary 指标
kubectl top pod -n medical-agent -l variant=canary

# 在 Grafana 中查看:
# - canary vs primary 错误率
# - canary vs primary 延迟
# - canary 资源使用
```

#### 步骤 4: 逐步增加流量

```bash
# 25% 流量
kubectl scale deployment/medical-agent-primary --replicas=3 -n medical-agent
kubectl scale deployment/medical-agent-canary --replicas=1 -n medical-agent

# 50% 流量
kubectl scale deployment/medical-agent-primary --replicas=2 -n medical-agent
kubectl scale deployment/medical-agent-canary --replicas=2 -n medical-agent

# 75% 流量
kubectl scale deployment/medical-agent-primary --replicas=1 -n medical-agent
kubectl scale deployment/medical-agent-canary --replicas=3 -n medical-agent
```

#### 步骤 5: 全量切换

```bash
# 更新 primary 为新版本
kubectl set image deployment/medical-agent-primary \
  medical-agent=medical-agent:v1.1.0 \
  -n medical-agent

# 等待滚动更新完成
kubectl rollout status deployment/medical-agent-primary -n medical-agent

# 清理 canary
kubectl scale deployment/medical-agent-canary --replicas=0 -n medical-agent
```

## 监控和验证

### 关键指标

#### 业务指标

```promql
# 错误率
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100

# P95 延迟
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# 请求速率
sum(rate(http_requests_total[5m]))
```

#### 资源指标

```bash
# CPU 使用
kubectl top pods -n medical-agent -l variant=canary

# 内存使用
kubectl get pods -n medical-agent -l variant=canary \
  -o jsonpath='{.items[*].spec.containers[0].resources}'

# 数据库连接
kubectl exec -it <canary-pod> -n medical-agent -- \
  python -c "from src.infrastructure.database import engine; print(len(engine.pool._all_connections))"
```

#### 日志分析

```bash
# 查看错误日志
kubectl logs deployment/medical-agent-canary -n medical-agent | grep ERROR

# 统计错误类型
kubectl logs deployment/medical-agent-canary -n medical-agent | \
  grep ERROR | awk '{print $NF}' | sort | uniq -c | sort -rn
```

### A/B 测试

使用 HTTP Header 进行 A/B 测试：

```yaml
# Istio VirtualService 示例
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: medical-agent
spec:
  http:
  - match:
    - headers:
        x-user-group:
          exact: beta-testers
    route:
    - destination:
        host: medical-agent-canary
  - route:
    - destination:
        host: medical-agent-primary
      weight: 90
    - destination:
        host: medical-agent-canary
      weight: 10
```

## 回滚程序

### 自动回滚

配置自动回滚：

```yaml
analysis:
  metrics:
  - name: success-rate
    thresholdRange:
      min: 99
    # 低于 99% 成功率自动回滚
  alerting:
    # 告警时回滚
    webhook: http://alertmanager/api/v1/alerts
```

### 手动回滚

```bash
# 快速回滚到 primary
kubectl scale deployment/medical-agent-canary --replicas=0 -n medical-agent
kubectl scale deployment/medical-agent-primary --replicas=3 -n medical-agent

# 或者回滚到之前的版本
kubectl rollout undo deployment/medical-agent-primary -n medical-agent
```

### 回滚后验证

```bash
# 验证 primary 健康
kubectl rollout status deployment/medical-agent-primary -n medical-agent

# 检查错误率恢复
# 在 Grafana 中查看指标

# 查看日志
kubectl logs deployment/medical-agent-primary -n medical-agent --tail=100
```

## 最佳实践

### 1. 灰度前检查

- ✅ 所有测试通过
- ✅ 性能基准测试
- ✅ 安全扫描
- ✅ 代码审查
- ✅ 文档更新

### 2. 灰度中监控

- ✅ 实时监控指标
- ✅ 定期检查日志
- ✅ 准备快速回滚
- ✅ 通知相关人员

### 3. 灰度后总结

- ✅ 记录发布过程
- ✅ 分析性能数据
- ✅ 总结经验教训
- ✅ 更新文档

### 4. 版本管理

```bash
# 版本命名规范
major.minor.patch

# 示例
1.0.0  # 主版本
1.1.0  # 次版本（新功能）
1.1.1  # 补丁版本（bug 修复）

# 灰度版本
v1.1.0-canary-20240115
```

### 5. 流量切换策略

**保守策略（推荐生产环境）：**
- 5% → 10% → 25% → 50% → 75% → 100%
- 每阶段 5-10 分钟

**激进策略（测试环境）：**
- 10% → 50% → 100%
- 每阶段 2-5 分钟

### 6. 自动化程度

**手动模式（首次发布）：**
- 每步手动操作
- 充分验证后继续
- 记录详细过程

**半自动模式（常规发布）：**
- 自动部署和监控
- 手动验证和确认
- 自动切换流量

**全自动模式（高频发布）：**
- 完全自动流程
- 自动回滚机制
- 需要完善的测试覆盖

## 工具集成

### Flagger (推荐)

[Flagger](https://flagger.app) 是一个渐进式交付工具，支持：

- 自动化灰度发布
- 指标驱动的自动回滚
- A/B 测试
- 蓝绿部署

**安装 Flagger：**

```bash
kubectl apply -k github.com/fluxcd/flagger//kustomize/istio
```

**配置 Flagger：**

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: medical-agent
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: medical-agent
  service: medical-agent
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: success-rate
      thresholdRange:
        min: 99
      query: |
        sum(
          rate(http_requests_total{
            namespace="{{ namespace }}",
            deployment="{{ name }}",
            status!~"5.."
          }[1m])
        ) /
        sum(
          rate(http_requests_total{
            namespace="{{ namespace }}",
            deployment="{{ name }}"
          }[1m])
        )
```

### Argo Rollouts

[Argo Rollouts](https://argoproj.github.io/argo-rollouts/) 提供更高级的发布策略。

## 故障场景

### 场景 1: 错误率飙升

**症状：** Canary 错误率 > 5%

**处理：**
```bash
# 立即停止流量切换
kubectl scale deployment/medical-agent-canary --replicas=0 -n medical-agent

# 分析错误日志
kubectl logs deployment/medical-agent-canary -n medical-agent | grep ERROR

# 修复后重新发布
```

### 场景 2: 延迟增加

**症状：** P95 延迟 > 基线 × 1.5

**处理：**
```bash
# 暂停流量增加
# 不增加 canary 副本数

# 检查性能问题
kubectl top pod -n medical-agent -l variant=canary

# 必要时回滚
kubectl scale deployment/medical-agent-canary --replicas=0 -n medical-agent
```

### 场景 3: 资源不足

**症状：** Canary Pod OOMKilled

**处理：**
```bash
# 增加资源限制
kubectl set resources deployment/medical-agent-canary \
  --limits=memory=4Gi --requests=memory=2Gi -n medical-agent

# 检查内存泄漏
kubectl logs <canary-pod> -n medical-agent --previous
```

## 附录

### A. 灰度发布检查清单

**发布前：**
- [ ] 代码审查完成
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] E2E 测试通过
- [ ] 性能测试通过
- [ ] 安全扫描通过
- [ ] 文档更新
- [ ] 发布计划评审

**发布中：**
- [ ] Canary 部署成功
- [ ] 初始流量正常
- [ ] 错误率正常
- [ ] 延迟正常
- [ ] 资源使用正常
- [ ] 无异常日志

**发布后：**
- [ ] 全量切换完成
- [ ] 指标正常
- [ ] 用户反馈良好
- [ ] 文档已归档
- [ ] 经验已总结

### B. 相关文档

- [部署文档](deployment.md)
- [故障排除](troubleshooting.md)
- [监控指南](../k8s/prometheus-configmap.yaml)
- [Flagger 文档](https://flagger.app)
