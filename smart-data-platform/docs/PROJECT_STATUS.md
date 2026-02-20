# Smart Data Platform - 项目状态总览

> 本文档为 LLM 友好格式，便于大模型快速理解项目状态
>
> **更新日期**: 2026-02-19

## 快速参考

| 指标 | 状态 |
|-----|------|
| 项目阶段 | Phase 4 (基础设施增强已完成) |
| 测试状态 | 86/86 通过 (100%) |
| 代码覆盖率 | ~65% (需继续提升) |
| 最后验收 | 2026-02-19 (Phase 3) |
| Python版本 | 3.9+ |

## 项目阶段

| 阶段 | 状态 | 描述 | 完成日期 |
|------|------|------|----------|
| Phase 1 | ✅ 已完成 | 项目初始化、基础架构搭建 | 2025-02-15 |
| Phase 2 | ✅ 已完成 | 核心功能实现（元数据、ETL、AI分析） | 2025-02-16 |
| Phase 3 | ✅ 已完成 | 可观测性、安全性、数据质量增强 | 2026-02-19 |
| Phase 4 | 📝 进行中 | CI/CD、前端增强、测试覆盖 | - |
| Phase 5 | ⏳ 计划中 | 性能优化、负载测试 | - |

## 技术栈

- **后端**: FastAPI 0.109.2 + SQLAlchemy 2.0.25 + Pydantic 2.6.1
- **前端**: Next.js 14 + TypeScript + Zustand
- **数据库**: PostgreSQL 15 + Redis 7
- **存储**: MinIO (S3-compatible)
- **ETL引擎**: pandas 2.2.0 (替代 Kettle)
- **AI集成**: OpenAI API + scikit-learn
- **任务队列**: Celery 5.3.6 + Redis
- **BI**: Apache Superset

## 子系统完成度

| 子系统 | 核心模块 | 完成度 | 关键文件 | 测试状态 |
|-------|---------|--------|---------|---------|
| 元数据管理 | MetadataEngine | 95% | `services/metadata_engine.py` | ✅ |
| 数据采集 | Connectors + Scheduler | 90% | `connectors/*.py` | ✅ |
| ETL加工 | ETLEngine | 95% | `services/etl_engine.py` | ✅ |
| AI分析 | AIService + ML Utils | 85% | `services/ai_service.py` | ⚠️ |
| 数据资产 | AssetService | 80% | `services/asset_service.py` | ✅ |
| 数据质量 | QualityService | 90% | `services/quality_service.py` | ⚠️ 待测 |
| 数据血缘 | LineageService | 85% | `services/lineage_service.py` | ✅ |
| 报表服务 | ReportService | 80% | `services/report_service.py` | ⚠️ 待测 |
| BI集成 | BIService | 75% | `services/bi_service.py` | ✅ |
| 安全管理 | Security + Middleware | 90% | `core/security.py` + `middleware/` | ✅ |
| 可观测性 | Observability | 100% | `core/observability.py` | ✅ |

## 文件索引 (LLM检索用)

### 入口与配置

| 文件 | 路径 | 用途 |
|-----|------|------|
| 主入口 | `backend/app/main.py` | FastAPI 应用入口 |
| 配置 | `backend/app/core/config.py` | 环境配置 |
| 数据库 | `backend/app/core/database.py` | SQLAlchemy 会话 |
| 调度器 | `backend/app/core/scheduler.py` | APScheduler 配置 |
| 可观测性 | `backend/app/core/observability.py` | 全链路追踪 |
| 安全 | `backend/app/core/security.py` | 安全工具函数 |

### API 路由

| 路由 | 路径 | 功能 |
|-----|------|------|
| 认证 | `api/v1/auth.py` | JWT 登录/注册 |
| 元数据 | `api/v1/metadata.py` | 数据源元数据管理 |
| ETL | `api/v1/etl.py` | ETL 管道管理 |
| 采集 | `api/v1/collect.py` | 数据采集任务 |
| 资产 | `api/v1/asset.py` | 数据资产目录 |
| 分析 | `api/v1/analysis.py` | AI 分析接口 |
| 质量 | `api/v1/quality.py` | 数据质量评估 |
| 报表 | `api/v1/report.py` | 报表生成与调度 |
| 血缘 | `api/v1/lineage.py` | 数据血缘查询 |

### 中间件

| 中间件 | 路径 | 功能 |
|-------|------|------|
| 限流 | `middleware/rate_limit.py` | Token bucket 限流 |
| 验证 | `middleware/validation.py` | 输入验证、安全检测 |
| 审计 | `middleware/audit.py` | 操作审计日志 |

### 数据模型

| 模型 | 路径 | 包含实体 |
|-----|------|---------|
| 用户 | `models/user.py` | User, Role, UserRole |
| 元数据 | `models/metadata.py` | DataSource, MetadataTable, MetadataColumn, MetadataVersion |
| ETL | `models/etl.py` | ETLPipeline, ETLStep, ETLExecution |
| 采集 | `models/collect.py` | CollectTask, CollectExecution |
| 资产 | `models/asset.py` | DataAsset, AssetAccess |
| 告警 | `models/alert.py` | AlertRule, Alert |
| 血缘 | `models/lineage.py` | LineageNode, LineageEdge |

### 业务服务

| 服务 | 路径 | 功能 |
|-----|------|------|
| ETL引擎 | `services/etl_engine.py` | DataFrame 转换步骤 |
| 元数据引擎 | `services/metadata_engine.py` | 数据源扫描、版本管理 |
| AI服务 | `services/ai_service.py` | OpenAI 集成、NL2SQL |
| ML工具 | `services/ml_utils.py` | 时间序列、异常检测、聚类 |
| 告警服务 | `services/alert_service.py` | 条件评估、通知 |
| 质量服务 | `services/quality_service.py` | 质量评分、问题检测 |
| 资产服务 | `services/asset_service.py` | 资产管理、导出 |
| 血缘服务 | `services/lineage_service.py` | 依赖追踪 |
| 报表服务 | `services/report_service.py` | 报表生成、定时任务 |
| 调度服务 | `services/scheduler_service.py` | APScheduler 任务管理 |
| BI服务 | `services/bi_service.py` | Superset 集成 |

### 连接器

| 连接器 | 路径 | 支持类型 |
|-------|------|---------|
| 基类 | `connectors/base.py` | 抽象接口 |
| 数据库 | `connectors/database.py` | PostgreSQL, MySQL |
| 文件 | `connectors/file.py` | CSV, Excel, JSON, Parquet |

## API 端点速查

### 认证
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/refresh` - 刷新令牌

### 元数据
- `GET /api/v1/metadata/sources` - 数据源列表
- `POST /api/v1/metadata/sources` - 创建数据源
- `POST /api/v1/metadata/sources/{id}/scan` - 扫描元数据
- `GET /api/v1/metadata/tables` - 表列表
- `GET /api/v1/metadata/columns` - 列列表

### ETL
- `GET /api/v1/etl/pipelines` - 管道列表
- `POST /api/v1/etl/pipelines` - 创建管道
- `POST /api/v1/etl/pipelines/{id}/run` - 执行管道
- `GET /api/v1/etl/executions` - 执行历史

### AI 分析
- `POST /api/v1/analysis/nl2sql` - 自然语言转 SQL
- `POST /api/v1/analysis/field-meanings` - 字段含义分析
- `POST /api/v1/analysis/cleaning-rules` - 清洗规则建议
- `POST /api/v1/analysis/forecast` - 时间序列预测
- `POST /api/v1/analysis/anomalies` - 异常检测
- `POST /api/v1/analysis/cluster-enhanced` - 聚类分析
- `POST /api/v1/analysis/search-assets` - 语义搜索资产

### 数据质量
- `GET /api/v1/quality/assessment/{asset_id}` - 质量评估
- `GET /api/v1/quality/issues` - 质量问题列表
- `GET /api/v1/quality/trend/{asset_id}` - 质量趋势
- `GET /api/v1/quality/report/{asset_id}` - 质量报告

### 数据资产
- `GET /api/v1/assets` - 资产列表
- `POST /api/v1/assets/export` - 导出数据
- `GET /api/v1/assets/{id}/download` - 下载文件

## 已知问题

| 优先级 | 问题 | 影响 | 计划修复 |
|--------|------|------|----------|
| 高 | ML 工具类未导出 | 模块可访问性 | Phase 4 |
| 中 | ML 工具缺少测试 | 代码质量保障 | Phase 4 |
| 中 | 质量服务缺少测试 | 代码质量保障 | Phase 4 |
| 中 | 调度器系统冗余 | 维护复杂度 | Phase 4 |
| 低 | SQL 安全器位置 | 代码组织 | Phase 4 |

更多问题详见 [ISSUES.md](./ISSUES.md)

## 依赖兼容性

- `bcrypt`: 必须 <5.0.0 (与 passlib 兼容)
- `eval_type_backport`: 必须安装 (Python 3.9 + Pydantic)
- `greenlet`: 必须 >=3.0.0 (SQLAlchemy async)
- APScheduler: 3.10.4 (考虑迁移到 Celery)
- Celery: 5.3.6 (分布式任务队列)

## 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| Backend API | 5500 | FastAPI 后端 |
| Frontend | 5501 | Next.js 前端 |
| PostgreSQL | 5502 | 主数据库 |
| Redis | 5503 | 缓存/队列 |
| MinIO API | 5504 | 对象存储 |
| MinIO Console | 5505 | 存储管理界面 |
| Superset | 5506 | BI 界面 |
| MySQL | 5510 | 测试数据库 |

## 部署命令

```bash
# 启动所有服务
docker compose -f docker-compose.ops.yml up -d

# 启动 Worker 服务 (含 Celery Worker + Beat)
docker compose -f docker-compose.ops.yml --profile worker up -d

# 查看日志
docker compose -f docker-compose.ops.yml logs -f backend

# 停止所有服务
docker compose -f docker-compose.ops.yml down
```

## 下一步工作 (Phase 4)

1. ✅ 文档整理与项目清理
2. 创建 CI/CD 流水线
3. 扩展集成测试覆盖
4. 前端 UI 增强（新功能页面）
5. ML 工具测试补充
6. 调度器系统整合 (APScheduler → Celery)
