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
│   ├── k3s/                   # k3s 安装脚本
│   ├── cube-studio/           # Cube-Studio Helm values
│   ├── superset/              # Apache Superset 部署
│   ├── datahub/               # DataHub 部署 + 采集配置
│   ├── hop/                   # Apache Hop ETL引擎
│   ├── seatunnel/             # SeaTunnel 数据同步
│   ├── dolphinscheduler/      # DolphinScheduler 调度
│   └── shardingsphere/        # ShardingSphere 数据脱敏
├── services/                  # 二开微服务 (Python/FastAPI)
│   ├── common/                # 共享库 (auth, db, http, middleware)
│   ├── portal/                # 统一入口门户 (:8010)
│   ├── nl2sql/                # 自然语言查询 (:8011)
│   ├── ai_cleaning/           # AI清洗规则推荐 (:8012)
│   ├── metadata_sync/         # 元数据联动ETL (:8013)
│   ├── data_api/              # 数据资产API网关 (:8014)
│   ├── sensitive_detect/       # 敏感数据检测 (:8015)
│   └── audit_log/             # 统一审计日志 (:8016)
├── docs/                      # 文档
├── deploy.sh                  # 一键部署脚本
└── Makefile                   # 常用命令
```

## 核心技术栈

- 基座: Cube-Studio (K8s/AI/监控/调度)
- ETL: Apache Hop (Kettle开源替代) + Apache SeaTunnel
- 调度: Apache DolphinScheduler
- 元数据: DataHub
- BI: Apache Superset
- AI/LLM: Ollama/vLLM (通过 Cube-Studio 部署)
- 数据安全: Apache ShardingSphere
- 二开服务: Python 3.11 + FastAPI + SQLAlchemy

## 常用命令

```bash
make help              # 显示所有命令
make deploy            # 一键部署
make stop              # 停止所有服务
make status            # 查看状态
make services-up       # 启动二开服务
make dev-install       # 安装 Python 依赖
make dev-portal        # 本地启动门户
```

## 开发指南

- 二开服务使用 FastAPI，统一风格：config.py (配置)、models.py (模型)、main.py (路由)
- 共享代码在 `services/common/`：数据库、认证、HTTP客户端、异常处理、中间件
- 所有服务通过 `services/common/middleware.py` 自动上报审计日志
- LLM 调用统一走 Ollama API (`http://localhost:31434`)

## 六大子系统

1. 数据规划与元数据管理系统 → DataHub
2. 数据感知汇聚系统 → SeaTunnel + DolphinScheduler + Hop
3. 数据加工融合系统 → SeaTunnel Transform + Great Expectations + PaddleOCR + LLM
4. 数据分析挖掘系统(AI+BI) → Superset + NL2SQL + Cube-Studio Pipeline
5. 数据资产系统 → DataHub + 数据API网关
6. 数据安全管理系统 → ShardingSphere + 敏感数据检测
