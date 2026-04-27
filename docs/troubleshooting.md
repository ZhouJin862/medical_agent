# Medical Agent 故障排除指南

本文档提供了常见问题的诊断和解决方案。

## 快速诊断流程

```
问题报告
    ↓
收集信息 → 查看日志、指标、状态
    ↓
定位根因 → 应用、数据库、网络、依赖
    ↓
实施修复 → 临时缓解 + 根本解决
    ↓
验证效果 → 确认问题已解决
    ↓
文档更新 → 记录问题和解决方案
```

## 按症状分类

### 服务不可用

#### 症状：API 完全无响应

**检查清单：**

```bash
# 1. 检查 Pod 状态
kubectl get pods -n medical-agent
kubectl describe pod <pod-name> -n medical-agent

# 2. 检查服务
kubectl get svc -n medical-agent
kubectl describe svc medical-agent -n medical-agent

# 3. 检查端点
kubectl get endpoints -n medical-agent

# 4. 检查 Ingress
kubectl get ingress -n medical-agent
kubectl describe ingress medical-agent-ingress -n medical-agent

# 5. 测试网络连通性
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never \
  -- curl http://medical-agent.medical-agent.svc.cluster.local:8000/health
```

**常见原因和解决方案：**

| 原因 | 诊断 | 解决方案 |
|------|------|----------|
| Pod 未启动 | kubectl get pods | 检查配置、资源限制 |
| 服务未暴露 | kubectl get svc | 创建或修复 Service |
| Ingress 配置错误 | kubectl get ingress | 修正 Ingress 规则 |
| 端口冲突 | kubectl describe pod | 更改端口配置 |
| 健康检查失败 | kubectl logs | 修复健康检查端点 |

#### 症状：间歇性 502/504 错误

**检查清单：**

```bash
# 1. 检查应用负载
kubectl top pods -n medical-agent

# 2. 检查数据库连接
kubectl logs <pod-name> -n medical-agent | grep -i "database\|connection"

# 3. 检查 LLM API 响应时间
# 查看 Grafana "LLM Performance" 面板

# 4. 检查超时配置
kubectl get deployment medical-agent -n medical-agent -o yaml | grep -i timeout
```

**解决方案：**

1. **增加超时时间**
   ```yaml
   env:
   - name: LLM_TIMEOUT
     value: "60"
   ```

2. **扩展 Pod**
   ```bash
   kubectl scale deployment medical-agent --replicas=5 -n medical-agent
   ```

3. **检查数据库性能**
   ```bash
   kubectl exec -it <mysql-pod> -- mysqladmin -u root -p processlist
   ```

### 性能问题

#### 症状：响应缓慢

**诊断步骤：**

```bash
# 1. 查看资源使用
kubectl top pods -n medical-agent
kubectl top nodes

# 2. 查看响应时间分布
# Prometheus 查询：
# histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# 3. 检查数据库慢查询
kubectl exec -it <mysql-pod> -- \
  mysql -u root -p -e "SHOW FULL PROCESSLIST;"

# 4. 检查缓存命中率
# Prometheus 查询：cache_hit_rate / (cache_hit_rate + cache_miss_rate)
```

**优化建议：**

1. **启用或增加缓存**
   ```yaml
   ENABLE_CACHE: "true"
   CACHE_TTL: "600"
   ```

2. **数据库索引优化**
   ```sql
   ANALYZE TABLE consultations;
   SHOW INDEX FROM consultations;
   ```

3. **水平扩展**
   ```bash
   kubectl autoscale deployment medical-agent \
    --min=3 --max=10 --cpu-percent=70 -n medical-agent
   ```

#### 症状：内存使用持续增长

**诊断：**

```bash
# 1. 查看内存趋势
kubectl top pod <pod-name> -n medical-agent --containers

# 2. 进入容器检查
kubectl exec -it <pod-name> -n medical-agent -- \
  cat /proc/meminfo

# 3. 检查 Python 内存使用
kubectl exec -it <pod-name> -n medical-agent -- \
  python -c "import psutil; p = psutil.Process(); print(p.memory_info())"
```

**可能原因和解决方案：**

| 原因 | 检查 | 解决方案 |
|------|------|----------|
| 内存泄漏 | 监控持续增长 | 重启 Pod，分析代码 |
| 缓存过大 | 检查缓存配置 | 设置 CACHE_MAX_SIZE |
| 连接未关闭 | 查看连接数 | 确保正确关闭 |
| 数据集过大 | 检查数据加载 | 使用分页或流式处理 |

### 数据库问题

#### 症状：数据库连接失败

**诊断：**

```bash
# 1. 检查数据库状态
kubectl get pods -n medical-agent | grep mysql
kubectl logs <mysql-pod> -n medical-agent

# 2. 测试连接
kubectl run -it --rm mysql-client --image=mysql:8.0 --restart=Never \
  -- mysql -h mysql.medical-agent.svc.cluster.local -u medical_user -p

# 3. 检查数据库资源
kubectl exec -it <mysql-pod> -n medical-agent -- \
  mysql -u root -p -e "SHOW PROCESSLIST; SHOW ENGINE INNODB STATUS;"
```

**解决方案：**

1. **检查 Secret 配置**
   ```bash
   kubectl get secret medical-agent-secret -n medical-agent -o yaml
   ```

2. **验证数据库服务**
   ```bash
   kubectl get svc mysql -n medical-agent
   kubectl get endpoints mysql -n medical-agent
   ```

3. **检查连接池设置**
   ```yaml
   DB_POOL_SIZE: "20"
   DB_MAX_OVERFLOW: "10"
   ```

#### 症状：查询缓慢

**诊断：**

```sql
-- 查看当前执行的查询
SHOW PROCESSLIST;

-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query%';
SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;

-- 分析查询执行计划
EXPLAIN SELECT * FROM consultations WHERE patient_id = 'xxx';

-- 查看表统计信息
SHOW TABLE STATUS LIKE 'consultations';
```

**优化方法：**

1. **添加索引**
   ```sql
   CREATE INDEX idx_patient_created ON consultations(patient_id, created_at);
   ```

2. **优化查询**
   ```python
   # 使用 select_related/prefetch 减少查询次数
   # 使用 only/defer 只加载需要的字段
   # 使用分页避免加载大量数据
   ```

3. **定期维护**
   ```sql
   ANALYZE TABLE consultations;
   OPTIMIZE TABLE consultations;
   ```

### LLM API 问题

#### 症状：LLM 调用失败或超时

**诊断：**

```bash
# 1. 查看日志中的 LLM 错误
kubectl logs <pod-name> -n medical-agent | grep -i "llm\|anthropic"

# 2. 检查 API 密钥
kubectl get secret medical-agent-secret -n medical-agent -o jsonpath='{.data.ANTHROPIC_API_KEY}' | base64 -d

# 3. 测试 API 连接
kubectl exec -it <pod-name> -n medical-agent -- \
  curl -I https://api.anthropic.com
```

**解决方案：**

1. **验证 API 密钥**
   ```bash
   # 更新 Secret
   kubectl create secret generic medical-agent-secret \
     --from-literal=ANTHROPIC_API_KEY=new_key \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. **增加超时和重试**
   ```yaml
   LLM_TIMEOUT: "60"
   LLM_MAX_RETRIES: "3"
   ```

3. **使用降级策略**
   ```python
   # 配置备用模型或缓存响应
   ```

### MCP 服务问题

#### 症状：MCP 调用失败

**诊断：**

```bash
# 1. 检查 MCP 服务状态
# 检查配置文件中的 MCP 端点

# 2. 查看 MCP 客户端日志
kubectl logs <pod-name> -n medical-agent | grep -i "mcp"

# 3. 测试 MCP 服务连通性
kubectl exec -it <pod-name> -n medical-agent -- \
  curl http://<mcp-server-url>/health
```

**解决方案：**

1. **检查 MCP 服务地址**
   ```yaml
   MCP_SERVER_URL: "http://mcp-server.default.svc.cluster.local:8080"
   ```

2. **验证网络策略**
   ```bash
   kubectl get networkpolicy -n medical-agent
   ```

## 诊断工具

### kubectl 插件

```bash
# 安装常用插件
kubectl krew install kv
kubectl krew install kubectl-trace

# 查看资源使用
kubectl top pods -n medical-agent
kubectl top nodes

# 查看事件
kubectl get events -n medical-agent --sort-by='.lastTimestamp'

# 追踪请求
kubectl trace <pod-name> -n medical-agent
```

### 日志分析

```bash
# 实时日志
kubectl logs -f deployment/medical-agent -n medical-agent

# 所有 Pod 的日志
kubectl logs -l app=medical-agent -n medical-agent

# 之前的日志（容器重启后）
kubectl logs <pod-name> --previous -n medical-agent

# 查看特定时间的日志
kubectl logs <pod-name> -n medical-agent --since-time=2024-01-15T10:00:00Z

# 过滤日志
kubectl logs <pod-name> -n medical-agent | grep ERROR
```

### 性能分析

```bash
# 进入容器进行性能分析
kubectl exec -it <pod-name> -n medical-agent -- bash

# 在容器内运行
python -m cProfile -o profile.stats src/interface/api/main.py
python -m pstats profile.stats
```

## 常见错误代码

### HTTP 状态码

| 代码 | 含义 | 可能原因 |
|------|------|----------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 认证失败 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 500 | Internal Server Error | 服务器错误 |
| 502 | Bad Gateway | 后端服务不可用 |
| 503 | Service Unavailable | 服务过载 |
| 504 | Gateway Timeout | 后端超时 |

### 应用错误

| 错误 | 含义 | 解决方案 |
|------|------|----------|
| `Database connection failed` | 数据库连接失败 | 检查数据库状态和连接配置 |
| `LLM API timeout` | LLM API 超时 | 增加超时或检查网络 |
| `Skill not found` | Skill 不存在 | 检查 Skill 注册 |
| `Memory service error` | 记忆服务错误 | 检查 Mem0 API |
| `MCP call failed` | MCP 调用失败 | 检查 MCP 服务 |

## 预防措施

### 1. 监控和告警

确保以下告警已配置：

- ✅ 服务下线告警
- ✅ 高错误率告警
- ✅ 高延迟告警
- ✅ 资源使用告警
- ✅ 数据库连接告警

### 2. 健康检查

```yaml
livenessProbe:
  httpGet:
    path: /health
  failureThreshold: 3
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
  failureThreshold: 3
  periodSeconds: 5
```

### 3. 资源限制

```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

### 4. 自动扩展

```yaml
# HPA
minReplicas: 3
maxReplicas: 10
targetCPUUtilizationPercentage: 70
targetMemoryUtilizationPercentage: 80
```

### 5. 定期维护

- 每周：检查日志和告警
- 每月：审查性能指标
- 每季度：评估容量需求
- 每年：灾难恢复演练

## 紧急联系

### 严重等级定义

| 等级 | 响应时间 | 示例 |
|------|----------|------|
| P0 - Critical | 15 分钟 | 服务完全不可用 |
| P1 - High | 1 小时 | 核心功能不可用 |
| P2 - Medium | 4 小时 | 部分功能不可用 |
| P3 - Low | 1 天 | 非关键问题 |

### 升级流程

```
1. 初次响应 (15 分钟内)
   ↓
2. 诊断中 (每小时更新)
   ↓
3. 修复方案 (提供 ETA)
   ↓
4. 实施修复
   ↓
5. 验证和关闭
```

### 联系方式

- **技术支持**: support@medical-agent.com
- **紧急热线**: +86 xxx xxxx xxxx
- **值班手机**: (7x24)
