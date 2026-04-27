# Medical Agent 运维手册

本文档面向运维工程师，提供系统日常运维、监控、故障处理等方面的指导。

## 目录

- [运维概述](#运维概述)
- [日常运维](#日常运维)
- [监控告警](#监控告警)
- [故障处理](#故障处理)
- [备份恢复](#备份恢复)
- [性能调优](#性能调优)
- [安全管理](#安全管理)

## 运维概述

### 系统架构

```
                    ┌─────────────────┐
                    │   Ingress/Gateway │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼────┐   ┌─────▼──────┐   ┌───▼────────┐
    │ Medical    │   │  Prometheus │   │ Grafana    │
    │ Agent Pod  │   │             │   │            │
    │ (HPA:3-10) │   │   Alertmgr   │   │            │
    └────────────┘   └─────────────┘   └────────────┘
            │                │
    ┌───────▼────────────────▼─────────┐
    │              Service Mesh           │
    └─────────────────┬─────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐    ┌──────▼──────┐    ┌──────▼──────┐
│ MySQL  │    │   Redis    │    │ Elasticsearch│
│ (主从) │    │  (哨兵)    │    │    (集群)    │
└────────┘    └─────────────┘    └─────────────┘
```

### 组件版本

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行环境 |
| FastAPI | 0.104+ | Web 框架 |
| MySQL | 8.0+ | 数据库 |
| Redis | 7+ | 缓存 |
| Prometheus | 2.48+ | 监控 |
| Grafana | 10.2+ | 可视化 |
| Elasticsearch | 8.11+ | 日志存储 |
| Kubernetes | 1.25+ | 容器编排 |

### SLA 定义

| 指标 | 目标 | 说明 |
|------|------|------|
| 可用性 | 99.9% | 月度可用性 |
| 响应时间 | P95 < 3s | API 响应时间 |
| 错误率 | < 1% | 错误请求比例 |
| 数据持久性 | 99.999% | 数据不丢失 |

## 日常运维

### 1. 每日检查清单

#### 早班检查（9:00）

```bash
#!/bin/bash
# daily_check.sh

echo "=== Medical Agent 每日检查 ==="

# 1. 检查 Pod 状态
echo "1. 检查 Pod 状态..."
kubectl get pods -n medical-agent | grep -v Running
if [ $? -ne 0 ]; then
    echo "❌ 有非 Running 状态的 Pod"
else
    echo "✅ 所有 Pod 正常运行"
fi

# 2. 检查资源使用
echo -e "\n2. 检查资源使用..."
kubectl top pods -n medical-agent

# 3. 检查服务端点
echo -e "\n3. 检查服务端点..."
kubectl get endpoints -n medical-agent

# 4. 检查最近错误
echo -e "\n4. 检查最近错误日志..."
kubectl logs -l deployment=medical-agent -n medical-agent --tail=100 | grep ERROR

# 5. 检查数据库连接
echo -e "\n5. 检查数据库连接..."
kubectl exec -it mysql-0 -n medical-agent -- \
  mysqladmin -u root -p$(kubectl get secret mysql-secret -n medical-agent -o jsonpath='{.data.password}' | base64 -d) ping
```

#### 晚班检查（17:00）

```bash
# 检查日志量
kubectl logs deployment/medical-agent -n medical-agent --since=1h | wc -l

# 检查异常重启
kubectl get pods -n medical-agent -o json | jq '.items[] | select(.status.containerStatuses[].restartCount > 0)'

# 检查磁盘使用
kubectl exec -it <pod> -- df -h
```

### 2. 周期性维护

#### 每周任务

**数据库维护：**

```sql
-- 慢查询分析
SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;

-- 索引优化
ANALYZE TABLE consultations;
ANALYZE TABLE messages;
OPTIMIZE TABLE consultations;

-- 检查表空间
SELECT table_schema, table_name, table_rows,
  ROUND(data_length / 1024 / 1024, 2) AS "Data MB",
  ROUND(index_length / 1024 / 1024, 2) AS "Index MB"
FROM information_schema.tables
WHERE table_schema = 'medical_agent'
ORDER BY data_length DESC;
```

**备份验证：**

```bash
# 验证备份完整性
mysqlbackupcheck --backup-dir=/backups/mysql --show-stats

# 测试恢复（在测试环境）
mysqlbackuprestore --backup-dir=/backups/mysql --target-dir=/tmp/test_restore
```

#### 每月任务

**性能评估：**

```bash
# 导出 Prometheus 月度报告
prometheus_tool --url=http://prometheus:9090 \
  --time-range="now-30d" --output=monthly_report.json

# 分析趋势
python scripts/analyze_metrics.py monthly_report.json
```

**容量规划：**

```bash
# 资源使用趋势
kubectl top nodes --use-metrics
kubectl top pods -n medical-agent --use-metrics

# 历史数据分析
python scripts/capacity_planning.py --days=30
```

### 3. 日志管理

#### 日志轮转

```yaml
# logging_config.yml
version: 1
formatters:
  default:
    format: '%(asctime)s %(name)s %(levelname)s %(message)s'
handlers:
  rotating_file:
    class: logging.handlers.RotatingFileHandler
    formatter: default
    filename: /app/logs/medical-agent.log
    maxBytes: 100MB
    backupCount: 10
loggers:
  src:
    level: INFO
    handlers: [rotating_file]
```

#### 日志归档

```bash
#!/bin/bash
# archive_logs.sh

# 归档30天前的日志
find /app/logs -name "*.log" -mtime +30 -exec gzip {} \;

# 上传到对象存储
# aws s3 sync /app/logs/ s3://medical-agent-logs/$(date +%Y%m%d)/

# 清理本地归档
find /app/logs -name "*.gz" -mtime +90 -delete
```

### 4. 配置管理

#### 配置更新流程

```bash
# 1. 备份当前配置
kubectl get configmap medical-agent-config -n medical-agent -o yaml > backup-config.yaml

# 2. 更新配置
kubectl edit configmap medical-agent-config -n medical-agent

# 3. 滚动重启
kubectl rollout restart deployment/medical-agent -n medical-agent

# 4. 验证配置
kubectl logs deployment/medical-agent -n medical-agent --tail=50
```

#### 密钥轮换

```bash
# 1. 生成新密钥
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. 更新 Secret
kubectl create secret generic db-secret \
  --from-literal=password="$NEW_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. 更新应用连接
kubectl rollout restart deployment/medical-agent -n medical-agent

# 4. 验证连接
kubectl logs deployment/medical-agent -n medical-agent --tail=20 | grep -i "database\|connection"
```

## 监控告警

### 监控指标

#### 应用层指标

```promql
# 请求速率
sum(rate(http_requests_total{namespace="medical-agent"}[5m]))

# 错误率
sum(rate(http_requests_total{namespace="medical-agent",status=~"5.."}[5m])) /
sum(rate(http_requests_total{namespace="medical-agent"}[5m]))

# P95 响应时间
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{namespace="medical-agent"}[5m])) by (le)
)

# 数据库连接池使用率
medical_agent_db_pool_active{namespace="medical-agent"} /
medical_agent_db_pool_size{namespace="medical-agent"}
```

#### 基础设施指标

```promql
# Pod 状态
up{namespace="medical-agent"}

# CPU 使用率
sum(rate(container_cpu_usage_seconds_total{namespace="medical-agent"}[5m])) /
sum(kube_pod_container_resource_limits{namespace="medical-agent",resource="cpu"})

# 内存使用率
sum(container_memory_working_set_bytes{namespace="medical-agent"}) /
sum(kube_pod_container_resource_limits{namespace="medical-agent",resource="memory"})

# 磁盘使用率
sum(node_filesystem_avail_bytes{mountpoint="/var/lib"}) /
sum(node_filesystem_size_bytes{mountpoint="/var/lib"})
```

### 告警规则

#### 告警分级

| 级别 | 响应时间 | 示例 |
|------|----------|------|
| P0 - Critical | 15 分钟 | 服务完全不可用 |
| P1 - High | 1 小时 | 核心功能不可用 |
| P2 - Medium | 4 小时 | 部分功能不可用 |
| P3 - Low | 1 天 | 非关键问题 |

#### 告警配置

```yaml
# alerts.yml
groups:
- name: medical_agent_alerts
  rules:
  # 服务可用性
  - alert: MedicalAgentDown
    expr: up{namespace="medical-agent", job="medical-agent-api"} == 0
    for: 1m
    labels:
      severity: critical
      team: platform
    annotations:
      summary: "Medical Agent 服务下线"
      description: "服务 {{ $labels.instance }} 已下线超过 1 分钟"

  # 高错误率
  - alert: HighErrorRate
    expr: |
      sum(rate(http_requests_total{namespace="medical-agent",status=~"5.."}[5m])) /
      sum(rate(http_requests_total{namespace="medical-agent"}[5m])) > 0.05
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "错误率超过 5%"
      description: "错误率: {{ $value | humanizePercentage }}"

  # 高延迟
  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(http_request_duration_seconds_bucket{namespace="medical-agent"}[5m])) by (le)
      ) > 3
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "P95 延迟超过 3 秒"
      description: "当前 P95: {{ $value }}s"
```

### 告警通知

#### 配置通知渠道

**Slack 通知：**

```yaml
receivers:
- name: slack-critical
  slack_configs:
  - channel: '#medical-agent-critical'
    title: '🚨 [CRITICAL]'
    text: |
      *告警:* {{ .CommonLabels.alertname }}
      *摘要:* {{ .CommonAnnotations.summary }}
      *描述:* {{ range .Alerts }}{{ .Annotations.description }}{{ end }}

    actions:
    - type: button
      text: '查看 Grafana'
      url: '{{ .ExternalURL }}'
    - type: button
      text: '确认'
      url: 'mailto:oncall@medical-agent.com'
```

**邮件通知：**

```yaml
- name: email-high
  email_configs:
  - to: 'ops-team@medical-agent.com'
    from: 'alertmanager@medical-agent.com'
    subject: '[WARNING] {{ .GroupLabels.alertname }}'
    html: |
      <h2>{{ .CommonAnnotations.summary }}</h2>
      <p>{{ .CommonAnnotations.description }}</p>
      <table>
        <tr><th>Severity</th><td>{{ .CommonLabels.severity }}</td></tr>
        <tr><th>Namespace</th><td>{{ .CommonLabels.namespace }}</td></tr>
        <tr><th>Pod</th><td>{{ .CommonLabels.pod }}</td></tr>
      </table>
```

## 故障处理

### 故障分类

#### 故障分级矩阵

| 影响 | 范围 | 响应时间 | 处理优先级 |
|------|------|----------|-----------|
| 严重 | 所有用户 | 15 分钟 | P0 |
| 高 | 大部分用户 | 1 小时 | P1 |
| 中 | 部分用户 | 4 小时 | P2 |
| 低 | 少数用户 | 1 天 | P3 |

### 常见故障场景

#### 场景 1: Pod CrashLoopBackOff

**症状：**
```
kubectl get pods -n medical-agent
# medical-agent-xxx   0/1     CrashLoopBackOff   x 3
```

**诊断步骤：**

```bash
# 1. 查看 Pod 状态
kubectl describe pod medical-agent-xxx -n medical-agent

# 2. 查看日志
kubectl logs medical-agent-xxx -n medical-agent

# 3. 查看之前日志
kubectl logs medical-agent-xxx -n medical-agent --previous

# 4. 进入容器调试
kubectl exec -it medical-agent-xxx -n medical-agent -- bash
```

**常见原因和解决方案：**

| 原因 | 诊断 | 解决方案 |
|------|------|----------|
| 启动失败 | 日志有 ImportError | 修复依赖 |
| 内存不足 | OOMKilled | 增加内存限制 |
| 健康检查失败 | ReadinessProbe failed | 修复健康检查端点 |
| 配置错误 | 无法连接数据库 | 修复配置 |

#### 场景 2: 数据库连接泄漏

**症状：**
```
# 逐步增加数据库连接
# 最终连接数达到上限
# 新请求失败
```

**诊断：**

```sql
-- 查看当前连接
SHOW PROCESSLIST;

-- 查看连接统计
SHOW STATUS WHERE `variable_name` = 'Threads_connected';
SHOW STATUS WHERE `variable_name` = 'Max_used_connections';

-- 查看连接来源
SELECT user, host, db, command, time
FROM information_schema.processlist
WHERE user != 'system user'
ORDER BY time;
```

**解决方案：**

```bash
# 1. 短期：重启应用释放连接
kubectl rollout restart deployment/medical-agent -n medical-agent

# 2. 长期：修复连接池配置
# 确保 connection.close() 被正确调用
# 使用连接池超时设置
```

#### 场景 3: 内存泄漏

**症状：**
```
# 内存使用持续增长
# Pod 被 OOMKilled
# 频繁重启
```

**诊断：**

```bash
# 1. 监控内存趋势
kubectl top pod <pod-name> -n medical-agent

# 2. Python 内存分析
kubectl exec -it <pod> -n medical-agent -- \
  python -c "import tracemalloc; tracemalloc.start(); ...; print(tracemalloc.get_traced_memory())"

# 3. 使用 memory-profiler
pip install memory-profiler
python -m memory_profiler src/
```

**解决方案：**

```python
# 确保资源被正确释放

# 1. 关闭数据库连接
@contextmanager
async def get_db():
    async with engine.begin() as conn:
        yield conn
    # 自动关闭

# 2. 清理缓存
CACHE.clear()

# 3. 使用 __del__ 方法
class ResourceManager:
    def __del__(self):
        self.cleanup()
```

### 故障处理流程

```
┌─────────────────┐
│  故障发现        │
│  (告警/用户报告)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  初步评估        │
│  - 影响范围      │
│  - 严重程度      │
│  - 是否需要上报  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  快速止损        │
│  - 扩容/回滚     │
│  - 切流/降级     │
│  - 通知用户      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  根因分析        │
│  - 查看日志      │
│  - 检查指标      │
│  - 复现问题      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  实施修复        │
│  - 代码修复      │
│  - 配置调整      │
│  - 重启服务      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  验证恢复        │
│  - 功能测试      │
│  - 性能检查      │
│  - 监控观察      │
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│  复盘总结        │
│  - 记录问题      │
│  - 改进流程      │
│  - 更新文档      │
└─────────────────┘
```

## 备份恢复

### 备份策略

#### 数据库备份

```bash
#!/bin/bash
# mysql_backup.sh

BACKUP_DIR="/backups/mysql/$(date +%Y%m%d)"
RETENTION_DAYS=30

# 全量备份（每周日）
if [ $(date +%u) -eq 0 ]; then
  mysqldump -u root -p$(cat /run/secrets/MYSQL_ROOT_PASSWORD) \
    --all-databases \
    --single-transaction \
    --routines \
    --triggers \
    | gzip > "$BACKUP_DIR/full_$(date +%Y%m%d).sql.gz"
fi

# 增量备份（每日）
mysqldump -u root -p$(cat /run/secrets/MYSQL_ROOT_PASSWORD) \
  medical_agent \
  --single-transaction \
  --flush-logs \
  --master-data=2 \
  | gzip > "$BACKUP_DIR/incremental_$(date +%Y%m%d).sql.gz"

# 清理旧备份
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete
```

#### 快照备份

```bash
# 持久卷快照
kubectl create snapshot pvc-$(date +%s) \
  --source=medical-agent-data \
  --volume-snapshot-class=fast

# 恢复测试
kubectl create volume pvc-test --snapshot-name=pvc-xxx
```

### 恢复流程

#### 数据库恢复

```bash
#!/bin/bash
# mysql_restore.sh

BACKUP_FILE=$1

# 1. 停止应用
kubectl scale deployment medical-agent --replicas=0 -n medical-agent

# 2. 恢复数据库
gunzip < $BACKUP_FILE | mysql -u root -p medical_agent

# 3. 验证数据
mysql -u root -p medical_agent -e "SELECT COUNT(*) FROM consultations;"

# 4. 重启应用
kubectl scale deployment medical-agent --replicas=3 -n medical-agent

# 5. 验证服务
kubectl get pods -n medical-agent
curl http://medical-agent/health
```

## 性能调优

### 应用层优化

#### 1. 缓存优化

```python
# Redis 缓存配置
CACHE_CONFIG = {
    "default_ttl": 300,  # 5分钟
    "user_cache_ttl": 1800,  # 30分钟
    "static_cache_ttl": 3600,  # 1小时
}

# 缓存策略
@lru_cache(maxsize=1000)
def get_health_assessment(patient_id: str):
    # 缓存健康评估结果
    pass
```

#### 2. 数据库优化

```sql
-- 1. 添加索引
CREATE INDEX idx_consultations_patient_created
ON consultations(patient_id, created_at);

CREATE INDEX idx_messages_consultation_created
ON messages(consultation_id, created_at);

-- 2. 分区表
ALTER TABLE messages PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

#### 3. 异步处理

```python
# 使用后台任务处理耗时操作
from celery import Celery

app = Celery('medical_agent')

@app.task
async def generate_health_plan(consultation_id: str):
    # 异步生成健康计划
    pass

# 在 API 中调用
generate_health_plan.delay(consultation_id)
```

### 基础设施优化

#### 资源限制

```yaml
resources:
  requests:
    cpu: 500m    # 确保基本性能
    memory: 512Mi
  limits:
    cpu: 2000m   # 防止资源占用
    memory: 2Gi
```

#### 自动扩缩容

```yaml
# HPA 配置
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 0.7
```

## 安全管理

### 1. 访问控制

```yaml
# RBAC 配置
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: medical-agent-admin
rules:
- apiGroups: [""]
  resources: ["*"]
  verbs: ["*"]
```

### 2. 网络策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: medical-agent-netpol
spec:
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: medical-agent
```

### 3. 安全扫描

```bash
# 镜像扫描
trivy image medical-agent:latest

# 代码扫描
bandit -r src/

# 依赖检查
safety check
```

## 附录

### A. 运维脚本

```bash
scripts/operations/
├── daily_check.sh       # 每日检查
├── backup.sh            # 备份脚本
├── restore.sh           # 恢复脚本
├── scale.sh             # 扩容脚本
└── emergency_rollback.sh # 紧急回滚
```

### B. 值班安排

| 时间 | 值班方式 | 响应时间 |
|------|----------|----------|
| 工作日 9:00-18:00 | 在岗 | 15 分钟 |
| 工作日 18:00-次日9:00 | 待命 | 30 分钟 |
| 周末 | 轮流 | 1 小时 |

### C. 应急联系人

| 角色 | 姓名 | 联系方式 |
|------|------|----------|
| 值班负责人 | 张三 | 138xxxx xxxx |
| 技术负责人 | 李四 | 139xxxx xxxx |
| 业务负责人 | 王五 | 136xxxx xxxx |
| 安全负责人 | 赵六 | 135xxxx xxxx |

---

**版本：** 1.0.0
**更新日期：** 2024年1月15日
