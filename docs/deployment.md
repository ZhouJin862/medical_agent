# Medical Agent 部署文档

本指南介绍如何在不同环境中部署 Medical Agent 慢病健康管理智能体系统。

## 目录

- [环境要求](#环境要求)
- [本地开发环境](#本地开发环境)
- [Docker 部署](#docker-部署)
- [Kubernetes 部署](#kubernetes-部署)
- [生产环境配置](#生产环境配置)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)
- [回滚程序](#回滚程序)

## 环境要求

### 硬件要求

**最小配置（开发环境）**
- CPU: 2 核
- 内存: 4GB
- 磁盘: 20GB

**推荐配置（生产环境）**
- CPU: 4+ 核
- 内存: 8GB+
- 磁盘: 100GB+ SSD

### 软件要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.11+ |
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| Kubernetes | 1.25+ (生产环境) |
| Helm | 3.0+ (可选) |

### 外部依赖

| 服务 | 用途 |
|------|------|
| MySQL 8.0+ | 数据存储 |
| Redis 7+ | 缓存 |
| LLM API | 智能体推理 |
| Mem0 API | 记忆服务 |

## 本地开发环境

### 1. 克隆代码

```bash
git clone https://github.com/your-org/medical-agent.git
cd medical-agent
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

### 5. 初始化数据库

```bash
alembic upgrade head
python scripts/insert_disease_types.py
python scripts/insert_vital_signs_standards.py
python scripts/insert_skill_data.py
```

### 6. 启动服务

```bash
uvicorn src.interface.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. 验证部署

```bash
curl http://localhost:8000/health
```

## Docker 部署

### 1. 构建镜像

```bash
# Linux/Mac
./scripts/docker_build.sh

# Windows
./scripts/docker_build.ps1

# 或使用 docker 命令
docker build -t medical-agent:latest .
```

### 2. 配置环境

创建 `.env` 文件：

```env
# Database
DB_HOST=mysql
DB_PORT=3306
DB_USER=medical_user
DB_PASSWORD=your_password_here
DB_NAME=medical_agent

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# LLM
ANTHROPIC_API_KEY=your_api_key_here
MODEL=glm-5

# Memory
MEM0_API_KEY=your_mem0_key
```

### 3. 启动服务栈

```bash
docker-compose up -d
```

### 4. 初始化数据库

```bash
docker-compose exec medical-agent alembic upgrade head
docker-compose exec medical-agent python scripts/insert_disease_types.py
```

### 5. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f medical-agent

# 健康检查
curl http://localhost:8000/health
```

### 6. 常用命令

```bash
# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f [service_name]

# 进入容器
docker-compose exec medical-agent bash

# 重建镜像
docker-compose build --no-cache

# 删除所有数据
docker-compose down -v
```

## Kubernetes 部署

### 前置条件

- 配置好 kubectl 连接到目标集群
- 安装 Helm (可选)
- 准备镜像仓库访问权限

### 1. 准备镜像

```bash
# 构建并推送镜像
docker build -t your-registry.com/medical-agent:latest .
docker push your-registry.com/medical-agent:latest
```

### 2. 创建命名空间

```bash
kubectl create namespace medical-agent
```

### 3. 配置密钥

编辑 `k8s/secret.yaml`，填入真实的密钥值：

```yaml
stringData:
  DB_PASSWORD: "your_secure_password"
  REDIS_PASSWORD: "your_redis_password"
  ANTHROPIC_API_KEY: "your_api_key"
  # ... 其他密钥
```

应用密钥：

```bash
kubectl apply -f k8s/secret.yaml
```

### 4. 部署应用

使用部署脚本：

```bash
./scripts/k8s_deploy.sh --image your-registry.com/medical-agent:latest
```

或手动部署：

```bash
# Namespace
kubectl apply -f k8s/namespace.yaml

# ConfigMap
kubectl apply -f k8s/configmap.yaml

# ServiceAccount & RBAC
kubectl apply -f k8s/serviceaccount.yaml

# Deployment
kubectl apply -f k8s/deployment.yaml

# Service
kubectl apply -f k8s/service.yaml

# HPA
kubectl apply -f k8s/hpa.yaml

# Ingress
kubectl apply -f k8s/ingress.yaml
```

### 5. 验证部署

```bash
# 查看 Pod 状态
kubectl get pods -n medical-agent

# 查看 Service
kubectl get svc -n medical-agent

# 查看 Ingress
kubectl get ingress -n medical-agent

# 查看日志
kubectl logs -f deployment/medical-agent -n medical-agent

# 端口转发测试
kubectl port-forward svc/medical-agent 8000:80 -n medical-agent
curl http://localhost:8000/health
```

### 6. 扩容

```bash
# 手动扩容
kubectl scale deployment medical-agent --replicas=5 -n medical-agent

# 使用 HPA 自动扩容（已配置）
kubectl get hpa -n medical-agent
```

### 7. 更新部署

```bash
# 更新镜像
kubectl set image deployment/medical-agent \
    medical-agent=your-registry.com/medical-agent:v1.0.1 \
    -n medical-agent

# 查看滚动更新状态
kubectl rollout status deployment/medical-agent -n medical-agent

# 如需回滚
kubectl rollout undo deployment/medical-agent -n medical-agent
```

## 生产环境配置

### 数据库配置

**MySQL 生产配置：**

```ini
[mysqld]
# InnoDB 配置
innodb_buffer_pool_size = 2G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT

# 连接池
max_connections = 500
max_connect_errors = 100000

# 查询缓存（MySQL 5.7 及以下）
query_cache_size = 0
query_cache_type = 0

# 二进制日志
log_bin = /var/log/mysql/mysql-bin.log
binlog_format = ROW
expire_logs_days = 7
```

### Redis 配置

```conf
# 内存配置
maxmemory 1gb
maxmemory-policy allkeys-lru

# 持久化
save 900 1
save 300 10
save 60 10000

# AOF
appendonly yes
appendfsync everysec

# 集群模式（生产环境推荐）
cluster-enabled yes
cluster-config-file nodes.conf
```

### 应用配置

```yaml
# 工作进程数
WORKERS: 4

# 数据库连接池
DB_POOL_SIZE: 20
DB_MAX_OVERFLOW: 10
DB_POOL_TIMEOUT: 30
DB_POOL_RECYCLE: 3600

# 缓存配置
CACHE_TTL: 300
CACHE_MAX_SIZE: 10000

# 日志级别
LOG_LEVEL: INFO
# 生产环境使用 INFO，不使用 DEBUG

# 请求限制
RATE_LIMIT_ENABLED: true
RATE_LIMIT_PER_MINUTE: 100

# 超时配置
LLM_TIMEOUT: 30
DB_TIMEOUT: 10
CACHE_TIMEOUT: 5
```

## 监控和日志

### Prometheus 监控

部署监控栈：

```bash
# Elasticsearch
kubectl apply -f k8s/elasticsearch-statefulset.yaml

# Kibana
kubectl apply -f k8s/kibana-deployment.yaml

# Filebeat
kubectl apply -f k8s/filebeat-daemonset.yaml

# Prometheus
kubectl apply -f k8s/prometheus-configmap.yaml
kubectl apply -f k8s/prometheus-deployment.yaml

# Grafana
kubectl apply -f k8s/grafana-configmap.yaml
kubectl apply -f k8s/grafana-deployment.yaml

# Alertmanager
kubectl apply -f k8s/alertmanager-configmap.yaml
kubectl apply -f k8s/alertmanager-deployment.yaml
```

访问监控界面：

```bash
# Grafana
kubectl port-forward svc/grafana 3000:3000 -n medical-agent
# 浏览器: http://localhost:3000
# 默认用户名: admin，密码见 Secret

# Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n medical-agent
# 浏览器: http://localhost:9090

# Kibana
kubectl port-forward svc/kibana 5601:5601 -n medical-agent
# 浏览器: http://localhost:5601
```

### 关键指标

**应用指标：**
- 请求速率 (RPS)
- 响应时间 (P50, P95, P99)
- 错误率
- 活跃连接数
- 数据库连接池使用率

**资源指标：**
- CPU 使用率
- 内存使用率
- 磁盘 I/O
- 网络 I/O

**业务指标：**
- 对话数量
- Skill 调用次数
- LLM API 调用次数
- 平均响应长度

### 告警规则

系统已配置以下告警：

| 告警名称 | 触发条件 | 严重级别 |
|---------|---------|----------|
| MedicalAgentDown | 服务下线超过 1 分钟 | Critical |
| MedicalAgentHighErrorRate | 错误率 > 5% | Warning |
| MedicalAgentHighLatency | P95 延迟 > 3 秒 | Warning |
| DatabasePoolExhausted | 连接池使用率 > 90% | Critical |
| LLMAPIHighErrorRate | LLM API 错误率 > 10% | Warning |

## 故障排除

### 常见问题

#### 1. 服务无法启动

**症状：** Pod 一直处于 CrashLoopBackOff 状态

**排查步骤：**

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name> -n medical-agent

# 查看容器日志
kubectl logs <pod-name> -n medical-agent

# 查看之前实例的日志
kubectl logs <pod-name> --previous -n medical-agent
```

**常见原因：**
- 配置错误（Secret 未配置）
- 依赖服务不可用（数据库、Redis）
- 资源限制（内存不足）

#### 2. 数据库连接失败

**症状：** 日志显示 "Can't connect to MySQL server"

**解决方案：**

```bash
# 检查数据库 Pod
kubectl get pods -n medical-agent | grep mysql

# 测试数据库连接
kubectl run -it --rm mysql-client --image=mysql:8.0 --restart=Never \
  -- mysql -h mysql.medical-agent.svc.cluster.local \
  -u medical_user -p

# 检查 Service
kubectl get svc mysql -n medical-agent
```

#### 3. 高延迟

**症状：** API 响应时间 > 3 秒

**排查步骤：**

```bash
# 检查资源使用
kubectl top pods -n medical-agent

# 查看 LLM 调用统计
# 在 Grafana 中查看 "LLM API Performance" 面板

# 检查数据库慢查询
kubectl exec -it <mysql-pod> -n medical-agent -- \
  mysql -u root -p -e "SHOW PROCESSLIST;"
```

#### 4. 内存泄漏

**症状：** 内存使用持续增长

**排查步骤：**

```bash
# 检查内存趋势
kubectl top pod <pod-name> -n medical-agent --containers

# 重启 Pod 以临时缓解
kubectl rollout restart deployment/medical-agent -n medical-agent
```

### 日志查询

**Kibana 查询示例：**

```json
// 查询错误日志
log.level: "ERROR"

// 查询特定 Pod
kubernetes.pod.name: "medical-agent-7d9f8c7b5-x2k4h"

// 查询慢请求
message: "duration" AND response_time: >3000

// 查询 LLM 调用失败
message: "LLM" AND status: "error"
```

## 回滚程序

### Docker Compose 回滚

```bash
# 1. 停止当前服务
docker-compose down

# 2. 切换到之前的版本
git checkout <previous-tag>

# 3. 重新构建
docker-compose build

# 4. 启动服务
docker-compose up -d

# 5. 恢复数据库（如需要）
docker-compose exec db mysql -u root -p < backup.sql
```

### Kubernetes 回滚

```bash
# 查看更新历史
kubectl rollout history deployment/medical-agent -n medical-agent

# 回滚到上一版本
kubectl rollout undo deployment/medical-agent -n medical-agent

# 回滚到指定版本
kubectl rollout undo deployment/medical-agent --to-revision=3 -n medical-agent

# 验证回滚
kubectl rollout status deployment/medical-agent -n medical-agent
```

### 数据库回滚

```bash
# 1. 备份当前数据库
kubectl exec -it <mysql-pod> -n medical-agent -- \
  mysqldump -u root -p medical_agent > backup.sql

# 2. 停止应用（防止新数据写入）
kubectl scale deployment medical-agent --replicas=0 -n medical-agent

# 3. 执行 Alembic 回滚
kubectl exec -it <medical-agent-pod> -n medical-agent -- \
  alembic downgrade -1

# 4. 恢复应用
kubectl scale deployment medical-agent --replicas=3 -n medical-agent
```

### 灾难恢复

**完整恢复流程：**

1. **准备新环境**
   ```bash
   # 创建新集群或命名空间
   kubectl create namespace medical-agent-dr
   ```

2. **恢复数据库**
   ```bash
   # 从备份恢复
   kubectl exec -i <new-mysql-pod> -n medical-agent-dr -- \
     mysql -u root -p medical_agent < backup.sql
   ```

3. **部署应用**
   ```bash
   # 使用之前的稳定版本
   kubectl apply -f k8s/ -n medical-agent-dr
   ```

4. **切换流量**
   ```bash
   # 更新 Ingress 指向新环境
   kubectl patch ingress medical-agent-ingress -n medical-agent \
     -p '{"spec":{"rules":[{"host":"medical-api.example.com"}]}}'
   ```

## 性能优化

### 应用层优化

1. **启用缓存**
   ```yaml
   ENABLE_CACHE: true
   CACHE_TTL: 300
   ```

2. **调整工作进程数**
   ```yaml
   WORKERS: 4  # 根据 CPU 核心数调整
   ```

3. **数据库连接池**
   ```yaml
   DB_POOL_SIZE: 20
   DB_MAX_OVERFLOW: 10
   ```

### 数据库优化

1. **添加索引**
   ```sql
   CREATE INDEX idx_consultations_patient_id ON consultations(patient_id);
   CREATE INDEX idx_messages_created_at ON messages(created_at);
   ```

2. **分区表**
   ```sql
   ALTER TABLE messages PARTITION BY RANGE (YEAR(created_at)) (
     PARTITION p2023 VALUES LESS THAN (2024),
     PARTITION p2024 VALUES LESS THAN (2025),
     PARTITION p_future VALUES LESS THAN MAXVALUE
   );
   ```

3. **定期清理**
   ```sql
   -- 删除 90 天前的对话记录
   DELETE FROM consultations
   WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
   ```

### 网络优化

1. **启用压缩**
   ```nginx
   gzip on;
   gzip_types application/json;
   ```

2. **配置 CDN**（静态资源）

3. **启用 HTTP/2**

## 安全加固

### 1. 网络策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: medical-agent-netpol
  namespace: medical-agent
spec:
  podSelector:
    matchLabels:
      app: medical-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: mysql
    ports:
    - protocol: TCP
      port: 3306
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### 2. Pod 安全策略

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop:
    - ALL
```

### 3. 密钥管理

使用 Kubernetes Secrets 或外部密钥管理系统（如 Vault）：

```bash
# 从 Vault 读取密钥
kubectl create secret generic medical-agent-secret \
  --from-literal=api-key=$(vault kv get -field=value secret/medical-agent/api-key)
```

## 附录

### A. 端口列表

| 服务 | 端口 | 用途 |
|------|------|------|
| Medical Agent API | 8000 | HTTP API |
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存 |
| Prometheus | 9090 | 监控 |
| Grafana | 3000 | 可视化 |
| Kibana | 5601 | 日志 |
| Alertmanager | 9093 | 告警 |

### B. 目录结构

```
medical-agent/
├── src/                  # 源代码
├── tests/                # 测试
├── k8s/                  # Kubernetes 配置
├── scripts/              # 部署脚本
├── alembic/              # 数据库迁移
├── requirements.txt      # Python 依赖
├── Dockerfile           # Docker 镜像
├── docker-compose.yml   # Docker Compose
└── .env.example         # 环境变量模板
```

### C. 相关文档

- [API 文档](./docs/api.md)
- [Skill 开发指南](./docs/skill-development.md)
- [运维手册](./docs/operations.md)
- [用户手册](./docs/user-guide.md)
