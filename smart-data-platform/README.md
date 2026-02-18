# 智能大数据平台 (Smart Data Platform)

基于 Python + FastAPI + Next.js 的企业级智能大数据管理平台。

## 功能特性

### 六大核心子系统

1. **数据规划与元数据管理系统**
   - 多源数据源管理 (PostgreSQL, MySQL, Oracle, CSV, Excel, API)
   - 自动元数据扫描与版本管理
   - AI 智能字段含义推断

2. **数据感知汇聚系统**
   - 多源数据采集任务管理
   - 支持全量/增量同步
   - Cron 调度支持

3. **数据加工融合系统 (ETL)**
   - 基于 pandas 的可视化 ETL 管道
   - 14+ 内置转换步骤类型
   - AI 智能清洗规则推荐

4. **数据分析挖掘系统**
   - 自然语言转 SQL (Text-to-SQL)
   - AI 可视化建议
   - 时序预测与聚类分析

5. **数据资产系统**
   - 资产目录与分类管理
   - 数据血缘追踪
   - AI 资产搜索

6. **数据安全管理系统**
   - 敏感数据自动识别
   - 多种脱敏策略
   - 告警规则与审计日志

## 技术栈

### 后端
- **框架**: FastAPI
- **ORM**: SQLAlchemy 2.0 (async)
- **数据处理**: pandas, numpy
- **AI**: OpenAI API, LangChain
- **任务调度**: APScheduler, Celery
- **OCR**: Tesseract, pdf2image

### 前端
- **框架**: Next.js 14
- **UI 组件**: Ant Design 5
- **状态管理**: Zustand
- **HTTP 客户端**: Axios

### 基础设施
- **数据库**: PostgreSQL 15
- **缓存/队列**: Redis 7
- **对象存储**: MinIO
- **BI 可视化**: Apache Superset

## 快速开始

### 使用 Docker Compose (推荐)

```bash
# 克隆项目
git clone <repo-url>
cd smart-data-platform

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填写 OPENAI_API_KEY 等配置

# 启动所有服务
docker-compose up -d

# 访问
# - 后端 API: http://localhost:8000/api/v1/docs
# - 前端: http://localhost:3000
# - Superset: http://localhost:8088
# - MinIO Console: http://localhost:9001
```

### 本地开发

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 运行测试

```bash
cd backend

# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html
```

## API 文档

启动后端服务后访问:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### 主要 API 端点

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /api/v1/auth/login` | 用户登录 |
| 数据源 | `GET/POST /api/v1/sources` | 数据源管理 |
| 元数据 | `POST /api/v1/sources/{id}/scan` | 扫描元数据 |
| ETL | `POST /api/v1/etl/pipelines` | 创建 ETL 管道 |
| 分析 | `POST /api/v1/analysis/nl-query` | 自然语言查询 |
| 资产 | `GET /api/v1/assets` | 数据资产目录 |
| 告警 | `GET /api/v1/alerts` | 告警列表 |

## 项目结构

```
smart-data-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API 路由
│   │   ├── core/            # 核心配置
│   │   ├── models/          # 数据库模型
│   │   ├── schemas/         # Pydantic 模式
│   │   ├── services/        # 业务逻辑
│   │   ├── connectors/      # 数据源连接器
│   │   └── main.py          # 应用入口
│   ├── tests/               # 测试用例
│   ├── alembic/             # 数据库迁移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── services/        # API 服务
│   │   ├── stores/          # 状态管理
│   │   └── types/           # TypeScript 类型
│   └── package.json
└── docker-compose.yml
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | - |
| `REDIS_URL` | Redis 连接字符串 | - |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `SECRET_KEY` | JWT 签名密钥 | - |
| `MINIO_ENDPOINT` | MinIO 端点 | localhost:9000 |

## 许可证

MIT License
