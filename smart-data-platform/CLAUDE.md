# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 项目概述

智能大数据平台 (Smart Data Platform) - 基于 FastAPI 后端和 Next.js 前端构建的企业级智能大数据管理平台。使用基于 pandas 的 Python ETL 引擎替代 Kettle。

## 项目指南

- 目标：以强类型、可测试、分层解耦为核心，保证项目健壮性与可扩展性；以清晰可读、模式统一为核心，使大模型易于理解与改写。
- 语言约定：交流与文档使用中文；生成的代码使用英文；文档放在 `docs` 且使用 Markdown。
- 发布约定：
  - 发布固定在 `/release` 文件夹，如 rust 服务固定发布在 `/release/rust` 文件夹。
  - 发布的成果物必须且始终以生产环境为标准，要包含所有发布生产所应该包含的文件或数据（包含全量发布与增量发布，首次发布与非首次发布）。
- 环境约定：
  - 对于数据库、消息队列、缓存等，尽量使用docker部署环境
  - 如果是Python项目，尽量使用venv虚拟环境
  - 尽量为项目配置独立的网络，避免与其他项目网络冲突
- 文档约定：
  - 每次修改都必须延续上一次的进展，每次修改的进展都必须保存在对应的 `docs` 文件夹下的文档中。
  - 执行修改过程中，进展随时保存文档，带上实际修改的时间，便于追溯修改历史。
  - 未完成的修改，文档保存在 `/docs/progress` 文件夹下。
  - 已完成的修改，文档保存在 `/docs/reports/completed` 文件夹下。
  - 对修改进行验收，文档保存在 `/docs/reports` 文件夹下。
  - 对重复的、冗余的、不能体现实际情况的文档或文档内容，要保持更新和调整。
  - 文档模板和命名规范可以参考 `/docs/standards` 和 `docs/templates` 文件夹下的内容。

### 面向大模型的可改写性（LLM Friendly）

- 一致的分层与目录：相同功能在各应用/包中遵循相同结构与命名，使检索与大范围重构更可控。
- 明确边界与单一职责：函数/类保持单一职责；公共模块暴露极少稳定接口；避免隐式全局状态。
- 显式类型与契约优先：导出 API 均有显式类型；运行时与编译时契约一致（zod schema 即类型源）。
- 声明式配置：将重要行为转为数据驱动（配置对象 + `as const`/`satisfies`），减少分支与条件散落。
- 可搜索性：统一命名（如 `parseXxx`、`assertNever`、`safeJsonParse`、`createXxxService`），降低 LLM 与人类的检索成本。
- 小步提交与计划：通过 `IMPLEMENTATION_PLAN.md` 和小步提交让模型理解上下文、意图与边界。
- 变更安全策略：批量程序性改动前先将原文件备份至 `/backup` 相对路径；若错误数异常上升，立即回滚备份。

### 可观测性开发（Observability Driven Development）

- 为了能够完整追踪代码的执行流，请你遵循 "全链路可观测性 (Full-Lifecycle Observability)" 模式编写代码；
- 结构化日志： 所有的日志输出必须是 JSON 格式，包含字段：timestamp, trace_id (全链路唯一ID), span_id (当前步骤ID), event_type (Function_Start/End, Branch, Error), payload (变量状态)；
- 装饰器/切面模式： 请定义一个 LifecycleTracker 装饰器或上下文管理器；
- 在函数进入时：记录输入参数 (Args/Kwargs)；
- 在函数退出时：记录返回值 (Return Value) 和耗时 (Duration)；
- 在函数异常时：记录完整的堆栈信息 (Stack Trace)；
- 关键节点埋点： 在复杂的 if/else 分支、for/while 循环内部、以及外部 API 调用前后，必须手动添加埋点（Point）；
- 执行摘要： 代码运行结束时，必须能够生成一份“执行轨迹报告 (Execution Trace Report)”；
- 请确保埋点代码与业务逻辑解耦（尽量使用装饰器），不要让日志代码淹没业务逻辑；

### 记忆系统

本项目采用基于Markdown文件的透明双层记忆架构。禁止使用复杂的嵌入检索。 所有记忆操作必须对人类可读且对Git友好。

#### 存储结构

记忆分为两个独立的层："流"（日常）层和"沉积"（长期）层。

- 第一层：每日笔记（流）
  - 路径： `./memory/daily/{YYYY-MM-DD}.md`
  - 类型： 仅追加日志。
  - 目的： 记录上下文的"流动"。今天所说的一切、做出的决定以及完成的任务。
  - 格式： 按时间顺序排列的Markdown条目。

- 第二层：长期记忆（沉积）
  - 路径： `./memory/MEMORY.md`
  - 类型： 经过整理、结构化的知识。
  - 目的： 记录上下文的"沉积"。用户偏好、关键上下文、重要决策以及"经验教训"（避免过去的错误）。
  - 格式： 分类的Markdown（例如 `## 用户偏好`、`## 项目上下文`、`## 关键决策`）。

#### 操作规则

##### 上下文加载（读取）

当初始化会话或生成响应时，通过组合以下内容来构建系统提示：

1. 长期上下文： 读取 `MEMORY.md` 的全部内容。
2. 近期上下文： 读取当前（以及可选的之前）一天的每日笔记内容。

##### 记忆持久化（写入）

- 即时操作（日常）：
  - 每一次交互都需要确认当日的记忆存在，如果不存在，应先初始化当日记忆
  - 将每一次重要的交互、工具输出或决策追加到当天的每日笔记中。
  - 不要覆盖或删除每日笔记中的内容；将其视为不可变的日志。
- 整合操作（长期）：
  - 触发条件： 当检测到有意义的信息时（例如，用户陈述了偏好、发现了特定的错误修复模式、建立了项目规则）。
  - 操作： 更新 `MEMORY.md`。
  - 方法： 智能地将新信息合并到现有类别中。如果信息已过时，则移除或更新它。此文件代表*当前*的真实状态。

#### 维护与调试

- 透明度： 所有记忆文件都是标准的Markdown文件。如果代理因错误的上下文而行为异常，修复方法是手动编辑 `.md` 文件。
- 版本控制： 所有记忆文件都受Git跟踪。

## 常用命令

### 后端 (在 `backend/` 目录下执行)

```bash
# 启动开发服务器
uvicorn app.main:app --reload

# 运行所有测试并生成覆盖率报告
pytest

# 运行单个测试文件
pytest tests/test_etl_steps.py

# 运行特定测试用例
pytest tests/test_etl_steps.py::TestFilterStep::test_filter_eq

# 生成数据库迁移
alembic revision --autogenerate -m "description"

# 应用数据库迁移
alembic upgrade head
```

### 前端 (在 `frontend/` 目录下执行)

```bash
npm run dev      # 开发服务器
npm run build    # 生产构建
npm run lint     # ESLint 检查
npm test         # Jest 测试
```

### Docker

```bash
docker-compose up -d           # 启动所有服务
docker-compose logs -f backend # 查看后端日志
```

## 架构设计

### 后端分层架构

```
API 层 (app/api/v1/)
    ↓ Pydantic 模式 (app/schemas/)
服务层 (app/services/)
    ↓ SQLAlchemy 模型 (app/models/)
数据层 (app/connectors/ + app/core/database.py)
```

**核心服务:**

- `MetadataEngine` - 扫描数据源、提取表/列元数据、管理版本
- `ETLEngine` - 通过基于步骤的转换执行管道，使用 pandas DataFrame
- `AIService` - OpenAI 集成，用于字段分析、Text-to-SQL、清洗规则建议
- `AlertService` - 指标监控，包含条件评估和通知功能

### ETL 引擎模式

ETL 步骤实现 `BaseETLStep`，包含异步方法 `process(df: DataFrame) -> DataFrame`。`STEP_REGISTRY` 将 `ETLStepType` 枚举映射到步骤类。管道执行按顺序链接步骤，在步骤间传递 DataFrame。

### 连接器工厂

`get_connector(source_type, config)` 根据 `DataSourceType` 枚举返回相应的连接器 (`DatabaseConnector`、`FileConnector`、`APIConnector`)。所有连接器都实现 `BaseConnector` 抽象类。

### 前端状态管理

`src/stores/` 中的 Zustand stores 管理全局状态。`useAuthStore` 处理 JWT 令牌和用户会话。API 调用通过 `src/services/api.ts` 进行，自动注入认证头。

### 认证流程

通过 `/api/v1/auth/login` 签发 JWT 令牌。`app/api/deps.py` 中的 `get_current_user` 依赖验证令牌并返回用户。通过 `require_permission()` 依赖工厂检查 RBAC 权限。

## 数据库模型 (6 大子系统)

1. **元数据**: `DataSource`, `MetadataTable`, `MetadataColumn`, `MetadataVersion`
2. **数据采集**: `CollectTask`, `CollectExecution`
3. **ETL**: `ETLPipeline`, `ETLStep`, `ETLExecution`
4. **数据资产**: `DataAsset`, `AssetAccess`
5. **告警**: `AlertRule`, `Alert`
6. **安全**: `User`, `Role`, `UserRole`, `AuditLog`

## 关键配置

- `app/core/config.py` - 通过 pydantic-settings 从环境变量读取配置
- `backend/.env` - 本地环境配置 (从 `.env.example` 复制)
- 必需配置: `DATABASE_URL`, `OPENAI_API_KEY`, `SECRET_KEY`

## 添加新的 ETL 步骤类型

1. 在 `app/services/etl_engine.py` 中创建继承 `BaseETLStep` 的步骤类
2. 在 `app/models/etl.py` 中向 `ETLStepType` 添加枚举值
3. 在 etl_engine.py 的 `STEP_REGISTRY` 字典中注册
4. 在 `tests/test_etl_steps.py` 中添加测试

## 添加新的连接器

1. 在 `app/connectors/` 中创建继承 `BaseConnector` 的连接器类
2. 在 `app/models/metadata.py` 中向 `DataSourceType` 添加枚举值
3. 更新 `app/connectors/__init__.py` 中的 `get_connector()` 工厂函数
