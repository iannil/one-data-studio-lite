# 项目状态总览

> 本文档为 LLM 友好格式，便于大模型快速理解项目状态

## 快速参考

| 指标 | 状态 |
|-----|------|
| 项目阶段 | Phase 1 (MVP) - 基础框架完成 |
| 测试状态 | 86/86 通过 (100%) |
| 代码覆盖率 | 62% |
| 最后验收 | 2026-02-16 |
| Python版本 | 3.9+ (需要兼容性处理) |

## 技术栈

- **后端**: FastAPI + SQLAlchemy + Pydantic
- **前端**: Next.js + TypeScript + Zustand
- **数据库**: PostgreSQL + Redis + MinIO
- **ETL引擎**: pandas (替代 Kettle)
- **AI集成**: OpenAI API + LangChain

## 六大子系统完成度

| 子系统 | 核心模块 | 完成度 | 关键文件 | 测试状态 |
|-------|---------|--------|---------|---------|
| 元数据管理 | MetadataEngine | 90% | `services/metadata_engine.py` | ✅ 91%覆盖 |
| 数据采集 | Connectors | 90% | `connectors/*.py` | ✅ |
| ETL加工 | ETLEngine | 95% | `services/etl_engine.py` | ✅ 58%覆盖 |
| 分析挖掘 | AIService | 30% | `services/ai_service.py` | ⚠️ 16%覆盖 |
| 数据资产 | API | 50% | `api/v1/asset.py` | ✅ |
| 安全管理 | Security | 70% | `core/security.py` | ✅ |

## 文件索引 (LLM检索用)

### 入口与配置

| 文件 | 路径 | 用途 |
|-----|------|------|
| 主入口 | `backend/app/main.py` | FastAPI 应用入口 |
| 配置 | `backend/app/core/config.py` | 环境配置 |
| 数据库 | `backend/app/core/database.py` | SQLAlchemy 会话 |
| 调度器 | `backend/app/core/scheduler.py` | APScheduler 配置 |

### API 路由

| 路由 | 路径 | 功能 |
|-----|------|------|
| 认证 | `api/v1/auth.py` | JWT 登录/注册 |
| 元数据 | `api/v1/metadata.py` | 数据源元数据管理 |
| ETL | `api/v1/etl.py` | ETL 管道管理 |
| 采集 | `api/v1/collect.py` | 数据采集任务 |
| 资产 | `api/v1/asset.py` | 数据资产目录 |
| 分析 | `api/v1/analysis.py` | AI 分析接口 |
| 安全 | `api/v1/security.py` | 安全管理 |

### 数据模型

| 模型 | 路径 | 包含实体 |
|-----|------|---------|
| 用户 | `models/user.py` | User, Role, UserRole |
| 元数据 | `models/metadata.py` | DataSource, MetadataTable, MetadataColumn |
| ETL | `models/etl.py` | ETLPipeline, ETLStep, ETLExecution |
| 采集 | `models/collect.py` | CollectTask, CollectExecution |
| 资产 | `models/asset.py` | DataAsset, AssetAccess |
| 告警 | `models/alert.py` | AlertRule, Alert |
| 审计 | `models/audit.py` | AuditLog |

### 业务服务

| 服务 | 路径 | 功能 |
|-----|------|------|
| ETL引擎 | `services/etl_engine.py` | DataFrame 转换步骤 |
| 元数据引擎 | `services/metadata_engine.py` | 数据源扫描、版本管理 |
| AI服务 | `services/ai_service.py` | OpenAI 集成 |
| 告警服务 | `services/alert_service.py` | 条件评估、通知 |
| OCR服务 | `services/ocr_service.py` | 图像文字识别 |

### 连接器

| 连接器 | 路径 | 支持类型 |
|-------|------|---------|
| 基类 | `connectors/base.py` | 抽象接口 |
| 数据库 | `connectors/database.py` | PostgreSQL, MySQL |
| 文件 | `connectors/file.py` | CSV, Excel, JSON |
| API | `connectors/api.py` | REST API |

## 已知问题

详见 [ISSUES.md](./ISSUES.md)

### 测试状态

所有 86 个测试通过 (100%)

### 依赖兼容性

- `bcrypt`: 必须 <5.0.0 (与 passlib 兼容)
- `eval_type_backport`: 必须安装 (Python 3.9 + Pydantic)
- `greenlet`: 必须安装 (SQLAlchemy async)
- Redis 端口: 使用 6380 (避免冲突)

## 下一步工作

1. 完善 AI 分析功能 (当前覆盖率 16%)
2. 提升整体测试覆盖率至 80%
3. 添加集成测试
4. 完善 OCR 服务测试 (当前覆盖率 30%)
