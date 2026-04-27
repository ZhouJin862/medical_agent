# 慢病管理智能体

## 项目结构

```
medical_agent/
├── agent/           # 智能体核心代码
├── config/          # 配置管理
├── db/              # 数据库模型和会话
├── memory/          # 记忆存储
├── api/             # API 接口
├── tests/           # 测试
├── alembic/         # 数据库迁移
└── requirements.txt # 依赖
```

## 安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入配置
```

## 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE medical_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 初始化 Alembic
alembic init alembic

# 编辑 alembic.ini 设置数据库连接
# sqlalchemy.url = mysql+pymysql://user:password@localhost:3306/medical_agent

# 生成迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

## 使用示例

```python
from agent import MedicalAgent
from db import init_db

# 初始化数据库
init_db()

# 创建智能体
agent = MedicalAgent()

# 对话
response = agent.sync_chat(
    patient_id="patient_001",
    message="我今天血压有点高，150/95，需要担心吗？",
    session_id="session_001"
)

print(response)
```

## 技术栈

- **LangGraph**: 智能体编排框架
- **Mem0**: 长期记忆管理
- **SQLAlchemy**: ORM 和数据库连接
- **MySQL**: 数据存储
