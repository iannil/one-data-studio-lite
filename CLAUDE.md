# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 项目概述

ONE-DATA-STUDIO-LITE 是一个智能大数据平台，以 Cube-Studio（腾讯音乐开源）为基座，集成开源组件覆盖数据全生命周期管理。融合元数据智能识别、AI 增强与 BI 可视化三大能力。

## 项目指南

- 目标：以强类型、可测试、分层解耦为核心，保证项目健壮性与可扩展性；以清晰可读、模式统一为核心，使大模型易于理解与改写。
- 语言约定：交流与文档使用中文；生成的代码使用英文；文档放在 `docs` 且使用 Markdown。
- 发布约定：
  - 发布固定在 `/release` 文件夹，如 rust 服务固定发布在 `/release/rust` 文件夹。
  - 发布的成果物必须且始终以生产环境为标准，要包含所有发布生产所应该包含的文件或数据（包含全量发布与增量发布，首次发布与非首次发布）。
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

## 项目结构

```
├── deploy/                    # 部署配置
│   ├── cube-studio/           # Cube-Studio Helm values
│   ├── superset/              # Apache Superset 部署
│   ├── openmetadata/          # OpenMetadata 元数据管理
│   ├── hop/                   # Apache Hop ETL引擎
│   ├── seatunnel/             # SeaTunnel 数据同步
│   ├── dolphinscheduler/      # DolphinScheduler 调度
│   ├── loki/                  # Loki + Grafana 日志监控
│   ├── prometheus/            # Prometheus 监控
│   └── etcd/                  # etcd 配置中心
├── services/                  # 二开微服务 (Python/FastAPI)
│   ├── common/                # 共享库 (auth, db, http, middleware)
│   ├── portal/                # 统一入口门户 (:8010)
│   ├── nl2sql/                # 自然语言查询 (:8011)
│   ├── ai_cleaning/           # AI清洗规则推荐 (:8012)
│   ├── metadata_sync/         # 元数据联动ETL (:8013)
│   ├── data_api/              # 数据资产API网关 (:8014)
│   ├── sensitive_detect/      # 敏感数据检测 (:8015)
│   └── audit_log/             # 统一审计日志 (:8016)
├── scripts/                   # 运维脚本
│   ├── lib/common.sh          # 公共函数库
│   ├── infra.sh               # 基础设施启动/停止
│   ├── platforms.sh           # 平台服务启动/停止
│   ├── services.sh            # 微服务启动/停止
│   ├── web.sh                 # 前端启动/停止
│   ├── health.sh              # 健康检查
│   ├── init-data.sh           # 初始化数据
│   └── test-lifecycle.sh      # 生命周期测试
├── web/                       # 前端 (React + Vite + TypeScript)
├── tests/                     # 测试
│   ├── test_portal/           # Portal 单元测试
│   └── test_lifecycle/        # 生命周期集成测试
├── docs/                      # 文档
├── ods.sh                     # 统一运维入口脚本
└── Makefile                   # 常用命令
```

## 核心技术栈

- 基座: Cube-Studio (K8s/AI/监控/调度)
- ETL: Apache Hop (Kettle开源替代) + Apache SeaTunnel
- 调度: Apache DolphinScheduler
- 元数据: OpenMetadata
- BI: Apache Superset
- AI/LLM: Ollama/vLLM (通过 Cube-Studio 部署)
- 二开服务: Python 3.11 + FastAPI + SQLAlchemy

## 常用命令

### 统一入口 (ods.sh)

```bash
# 启动服务
./ods.sh start all              # 启动所有服务
./ods.sh start infra            # 启动基础设施 (MySQL, Redis, MinIO)
./ods.sh start platforms        # 启动平台服务 (OpenMetadata, Superset等)
./ods.sh start services         # 启动微服务
./ods.sh start web              # 启动前端开发服务器

# 停止服务
./ods.sh stop all               # 停止所有服务
./ods.sh stop infra             # 停止基础设施
./ods.sh stop platforms         # 停止平台服务
./ods.sh stop services          # 停止微服务
./ods.sh stop web               # 停止前端

# 状态与健康检查
./ods.sh status all             # 查看所有服务状态
./ods.sh health all             # 健康检查
./ods.sh info                   # 显示访问地址

# 初始化与测试
./ods.sh init-data seed         # 初始化种子数据
./ods.sh init-data verify       # 验证数据完整性
./ods.sh test all               # 运行所有测试
./ods.sh test lifecycle         # 按生命周期顺序测试
```

### Make 命令

```bash
make help                       # 显示所有命令
make start                      # 启动所有服务
make stop                       # 停止所有服务
make status                     # 查看服务状态
make health                     # 健康检查

# 分层启动
make start-infra                # 启动基础设施
make start-platforms            # 启动平台服务
make start-services             # 启动微服务
make start-web                  # 启动前端

# 测试
make test                       # 运行所有测试
make test-lifecycle             # 生命周期测试
make test-foundation            # 系统基础测试
make test-planning              # 数据规划测试

# 本地开发
make dev-portal                 # 本地启动门户
make dev-nl2sql                 # 本地启动 NL2SQL
make web-dev                    # 启动前端开发服务器
```

## 开发指南

- 二开服务使用 FastAPI，统一风格：config.py (配置)、models.py (模型)、main.py (路由)
- 共享代码在 `services/common/`：数据库、认证、HTTP客户端、异常处理、中间件
- 所有服务通过 `services/common/middleware.py` 自动上报审计日志
- LLM 调用统一走 Ollama API (`http://localhost:31434`)

## 六大子系统

1. 数据规划与元数据管理系统 → OpenMetadata
2. 数据感知汇聚系统 → SeaTunnel + DolphinScheduler + Hop
3. 数据加工融合系统 → SeaTunnel Transform + Great Expectations + PaddleOCR + LLM
4. 数据分析挖掘系统(AI+BI) → Superset + NL2SQL + Cube-Studio Pipeline
5. 数据资产系统 → OpenMetadata + 数据API网关
6. 数据安全管理系统 → 敏感数据检测
