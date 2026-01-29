# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 项目概述

ONE-DATA-STUDIO-LITE 是一个智能大数据平台，以 Cube-Studio（腾讯音乐开源）为基座，集成开源组件覆盖数据全生命周期管理。融合元数据智能识别、AI 增强与 BI 可视化三大能力。

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
