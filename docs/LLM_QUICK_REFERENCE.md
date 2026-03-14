# Smart Data Platform - LLM 快速参考

> 本文档为 LLM 优化格式，便于大模型快速理解项目结构和执行常见任务

## 项目路径索引

### 核心目录结构

```
smart-data-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API 端点路由
│   │   ├── core/            # 配置、数据库、可观测性
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── services/        # 业务逻辑层
│   │   ├── connectors/      # 数据源连接器
│   │   └── middleware/      # 中间件（限流、验证、审计）
│   ├── tests/               # pytest 测试
│   ├── requirements.txt     # Python 依赖
│   └── Dockerfile           # 后端容器构建
│
├── frontend/
│   └── src/
│       ├── components/      # React 组件
│       ├── pages/           # Next.js 页面
│       ├── services/        # API 客户端
│       └── stores/          # Zustand 状态管理
│
├── docs/                    # 项目文档
├── docker-compose.ops.yml   # 生产环境 Docker Compose
└── memory/                  # AI 记忆系统
```

## 文件路径 → 功能映射

### 配置与入口

| 路径 | 功能 | 关键类/函数 |
|------|------|-------------|
| `app/main.py` | FastAPI 应用入口 | `app = FastAPI()` |
| `app/core/config.py` | 环境配置 | `settings: Settings` |
| `app/core/database.py` | 数据库会话 | `async_session_factory` |
| `app/core/observability.py` | 可观测性 | `@LifecycleTracker` |
| `app/core/scheduler.py` | APScheduler 配置 | `scheduler: AsyncIOScheduler` |
| `app/core/security.py` | 安全工具 | `hash_password, verify_password` |

### API 路由 (v1)

| 路径 | 功能 | 主要端点 |
|------|------|----------|
| `api/v1/__init__.py` | 路由注册 | `include_router` |
| `api/v1/auth.py` | JWT 认证 | `/login`, `/register` |
| `api/v1/metadata.py` | 元数据管理 | `/sources`, `/tables`, `/columns` |
| `api/v1/etl.py` | ETL 管理 | `/pipelines`, `/run` |
| `api/v1/collect.py` | 数据采集 | `/tasks`, `/executions` |
| `api/v1/asset.py` | 数据资产 | `/assets`, `/export` |
| `api/v1/analysis.py` | AI 分析 | `/nl2sql`, `/forecast`, `/anomalies` |
| `api/v1/quality.py` | 数据质量 | `/assessment`, `/issues` |
| `api/v1/report.py` | 报表服务 | `/generate`, `/schedule` |
| `api/v1/lineage.py` | 数据血缘 | `/graph`, `/upstream`, `/downstream` |

### 服务层

| 路径 | 功能 | 主要类/方法 |
|------|------|-------------|
| `services/metadata_engine.py` | 元数据扫描 | `MetadataEngine.scan_source()` |
| `services/etl_engine.py` | ETL 执行 | `ETLEngine.run_pipeline()` |
| `services/ai_service.py` | AI 分析 | `AIService.natural_language_to_sql()` |
| `services/ml_utils.py` | ML 工具 | `TimeSeriesForecaster`, `AnomalyDetector`, `EnhancedClustering` |
| `services/quality_service.py` | 质量评估 | `DataQualityService.calculate_quality_score()` |
| `services/asset_service.py` | 资产管理 | `AssetService.export_asset_data()` |
| `services/lineage_service.py` | 血缘追踪 | `LineageService.get_lineage_graph()` |
| `services/report_service.py` | 报表生成 | `ReportService.generate_report()` |
| `services/scheduler_service.py` | 任务调度 | `SchedulerService.add_collect_job()` |
| `services/bi_service.py` | BI 集成 | `BIService.sync_to_superset()` |

### 中间件

| 路径 | 功能 | 主要类 |
|------|------|--------|
| `middleware/rate_limit.py` | 限流 | `RateLimitMiddleware` |
| `middleware/validation.py` | 输入验证 | `ValidationMiddleware` |
| `middleware/__init__.py` | 导出 | `__all__` |

### 数据模型

| 路径 | 主要模型 |
|------|----------|
| `models/user.py` | `User`, `Role`, `UserRole` |
| `models/metadata.py` | `DataSource`, `MetadataTable`, `MetadataColumn`, `MetadataVersion` |
| `models/etl.py` | `ETLPipeline`, `ETLStep`, `ETLExecution` |
| `models/collect.py` | `CollectTask`, `CollectExecution` |
| `models/asset.py` | `DataAsset`, `AssetAccess` |
| `models/alert.py` | `AlertRule`, `Alert` |
| `models/lineage.py` | `LineageNode`, `LineageEdge` |

### 连接器

| 路径 | 功能 |
|------|------|
| `connectors/base.py` | `BaseConnector` 抽象类 |
| `connectors/database.py` | `DatabaseConnector` (PostgreSQL, MySQL) |
| `connectors/file.py` | `FileConnector` (CSV, Excel, JSON) |
| `connectors/__init__.py` | `get_connector()` 工厂函数 |

## API 端点完整列表

### 公开端点 (无需认证)

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录，返回 JWT |
| POST | `/api/v1/auth/register` | 用户注册 |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/docs` | Swagger UI 文档 |
| GET | `/redoc` | ReDoc 文档 |

### 认证端点 (需要 JWT)

#### 元数据管理
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/metadata/sources` | 数据源列表 |
| POST | `/api/v1/metadata/sources` | 创建数据源 |
| GET | `/api/v1/metadata/sources/{id}` | 获取数据源详情 |
| PATCH | `/api/v1/metadata/sources/{id}` | 更新数据源 |
| DELETE | `/api/v1/metadata/sources/{id}` | 删除数据源 |
| POST | `/api/v1/metadata/sources/{id}/scan` | 扫描元数据 |
| GET | `/api/v1/metadata/tables` | 表列表 |
| GET | `/api/v1/metadata/columns` | 列列表 |
| GET | `/api/v1/metadata/versions` | 元数据版本列表 |

#### ETL 管理
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/etl/pipelines` | 管道列表 |
| POST | `/api/v1/etl/pipelines` | 创建管道 |
| GET | `/api/v1/etl/pipelines/{id}` | 获取管道详情 |
| PATCH | `/api/v1/etl/pipelines/{id}` | 更新管道 |
| DELETE | `/api/v1/etl/pipelines/{id}` | 删除管道 |
| POST | `/api/v1/etl/pipelines/{id}/run` | 执行管道 |
| GET | `/api/v1/etl/executions` | 执行历史 |
| GET | `/api/v1/etl/executions/{id}` | 执行详情 |
| GET | `/api/v1/etl/steps/types` | 可用步骤类型 |

#### 数据采集
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/collect/tasks` | 采集任务列表 |
| POST | `/api/v1/collect/tasks` | 创建采集任务 |
| POST | `/api/v1/collect/tasks/{id}/run` | 手动执行采集 |
| GET | `/api/v1/collect/executions` | 执行历史 |

#### AI 分析
| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/analysis/nl2sql` | 自然语言转 SQL |
| POST | `/api/v1/analysis/field-meanings` | 字段含义分析 |
| POST | `/api/v1/analysis/cleaning-rules` | 清洗规则建议 |
| POST | `/api/v1/analysis/forecast` | 时间序列预测 (ML) |
| POST | `/api/v1/analysis/anomalies` | 异常检测 (ML) |
| POST | `/api/v1/analysis/cluster-enhanced` | 聚类分析 (ML) |
| POST | `/api/v1/analysis/search-assets` | 语义搜索资产 |
| POST | `/api/v1/analysis/predict-missing` | 预测缺失值 |
| POST | `/api/v1/analysis/detect-sensitive` | 敏感字段检测 |
| POST | `/api/v1/analysis/validate-sql` | SQL 验证 |

#### 数据质量
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/quality/assessment/{asset_id}` | 质量评估 |
| GET | `/api/v1/quality/issues` | 质量问题列表 |
| GET | `/api/v1/quality/trend/{asset_id}` | 质量趋势 |
| GET | `/api/v1/quality/report/{asset_id}` | 质量报告 |

#### 数据资产
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/assets` | 资产列表 |
| POST | `/api/v1/assets` | 创建资产 |
| GET | `/api/v1/assets/{id}` | 资产详情 |
| PATCH | `/api/v1/assets/{id}` | 更新资产 |
| DELETE | `/api/v1/assets/{id}` | 删除资产 |
| POST | `/api/v1/assets/export` | 导出数据 |
| GET | `/api/v1/assets/{id}/download` | 下载文件 |
| GET | `/api/v1/assets/{id}/lineage` | 资产值 |

#### 报表服务
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/report/templates` | 报表模板列表 |
| POST | `/api/v1/report/templates` | 创建模板 |
| POST | `/api/v1/report/generate` | 生成报表 |
| POST | `/api/v1/report/schedule` | 创建定时报表 |
| GET | `/api/v1/report/history` | 报表历史 |

#### 数据血缘
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/lineage/graph` | 获取血缘图 |
| GET | `/api/v1/lineage/upstream/{asset_id}` | 上游依赖 |
| GET | `/api/v1/lineage/downstream/{asset_id}` | 下游影响 |
| POST | `/api/v1/lineage/trace` | 追溯数据路径 |

## 服务层函数索引

### MetadataEngine

```python
from app.services import MetadataEngine

engine = MetadataEngine(db)
await engine.scan_source(source_id)           # 扫描数据源
await engine.extract_tables(source_id)        # 提取表信息
await engine.extract_columns(table_id)        # 提取列信息
await engine.get_metadata_version(source_id)  # 获取版本
```

### ETLEngine

```python
from app.services import ETLEngine

engine = ETLEngine(db)
result = await engine.run_pipeline(pipeline_id)  # 执行管道
# result = {
#     "execution_id": uuid,
#     "step_metrics": [...],
#     "rows_processed": 1000,
# }
```

### AIService

```python
from app.services import AIService

ai = AIService(db)
await ai.natural_language_to_sql("显示最近订单")       # NL2SQL
await ai.analyze_field_meanings(source_id, table)     # 字段分析
await ai.suggest_cleaning_rules(source_id, table)     # 清洗建议
await ai.predict_time_series_enhanced(data, date_col, value_col)  # 预测
await ai.detect_anomalies(data, features)             # 异常检测
await ai.cluster_analysis_enhanced(data, features)    # 聚类分析
await ai.search_assets("客户数据")                    # 语义搜索
```

### DataQualityService

```python
from app.services import DataQualityService

quality = DataQualityService(db)
score = await quality.calculate_quality_score(asset_id)  # 质量评分
issues = await quality.detect_quality_issues(asset_id)   # 问题检测
report = await quality.generate_quality_report(asset_id)  # 质量报告
trend = await quality.track_quality_trend(asset_id)      # 趋势追踪
```

### LineageService

```python
from app.services import LineageService

lineage = LineageService(db)
graph = await lineage.get_lineage_graph(asset_id)          # 血缘图
upstream = await lineage.get_upstream_dependencies(asset_id)  # 上游
downstream = await lineage.get_downstream_impacts(asset_id)   # 下游
```

## 关键配置项

### 环境变量 (backend/.env)

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | - |
| `REDIS_URL` | Redis 连接字符串 | - |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `OPENAI_MODEL` | OpenAI 模型名称 | gpt-4o-mini |
| `SECRET_KEY` | JWT 签名密钥 | - |
| `MINIO_ENDPOINT` | MinIO 地址 | - |
| `SUPERSET_URL` | Superset 地址 | - |

### 端口配置

| 服务 | 端口 |
|------|------|
| Backend API | 5500 |
| Frontend | 5501 |
| PostgreSQL | 5502 |
| Redis | 5503 |
| MinIO API | 5504 |
| MinIO Console | 5505 |
| Superset | 5506 |
| MySQL | 5510 |

## 常见任务执行步骤

### 添加新的 ETL 步骤

1. 在 `app/services/etl_engine.py` 创建步骤类，继承 `BaseETLStep`
2. 在 `app/models/etl.py` 添加枚举值到 `ETLStepType`
3. 在 `etl_engine.py` 的 `STEP_REGISTRY` 注册步骤
4. 在 `tests/test_etl_steps.py` 添加测试

### 添加新的数据源连接器

1. 在 `app/connectors/` 创建连接器类，继承 `BaseConnector`
2. 在 `app/models/metadata.py` 添加枚举值到 `DataSourceType`
3. 在 `connectors/__init__.py` 的 `get_connector()` 添加分支

### 添加新的 API 端点

1. 在 `app/api/v1/` 创建路由文件
2. 定义路由函数，使用依赖注入 `get_current_user`
3. 在 `app/api/v1/__init__.py` 注册路由 `include_router`
4. 在 `app/schemas/` 添加请求/响应模型

## 代码规范摘要

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `MetadataEngine` |
| 函数名 | snake_case | `scan_source` |
| 常量 | UPPER_SNAKE_CASE | `STEP_REGISTRY` |
| 私有成员 | 前缀下划线 | `_internal_method` |

### 类型注解

```python
from typing import Any

async def function_name(
    db: AsyncSession,
    id: uuid.UUID,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ...
```

### 错误处理

```python
try:
    result = await operation()
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal error")
```

### 可观测性装饰器

```python
from app.core.observability import LifecycleTracker

@LifecycleTracker(name="Service.method_name")
async def business_method(self, arg: str) -> dict[str, Any]:
    ...
```

## 测试命令

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_etl_steps.py

# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 在 Docker 中运行测试
docker compose -f docker-compose.ops.yml run backend pytest
```

## 部署命令

```bash
# 启动所有服务
docker compose -f docker-compose.ops.yml up -d

# 启动 Worker (Celery)
docker compose -f docker-compose.ops.yml --profile worker up -d

# 查看日志
docker compose -f docker-compose.ops.yml logs -f backend

# 停止服务
docker compose -f docker-compose.ops.yml down

# 重启服务
docker compose -f docker-compose.ops.yml restart backend
```
