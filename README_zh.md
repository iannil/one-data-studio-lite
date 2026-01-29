# ONE-DATA-STUDIO-LITE

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)

[English](README.md)

**ONE-DATA-STUDIO-LITE** 是一个智能大数据平台，以 [Cube-Studio](https://github.com/tencentmusic/cube-studio)（腾讯音乐开源）为基座，集成业界优秀的开源组件，覆盖数据全生命周期管理。平台融合三大核心能力：元数据智能识别、AI 增强处理、BI 可视化分析。

## 核心特性

- **元数据智能识别** - 基于 DataHub 的元数据管理与数据血缘追踪
- **AI 增强处理** - LLM 驱动的清洗规则推荐、NL2SQL 自然语言查询
- **BI 可视化** - Apache Superset 交互式数据分析
- **端到端数据管道** - Apache Hop、SeaTunnel、DolphinScheduler 实现从数据采集到洞察
- **数据安全** - Apache ShardingSphere 透明数据脱敏

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     统一门户 (Portal)                         │
├─────────────────────────────────────────────────────────────┤
│  二开服务: NL2SQL · AI清洗 · 元数据同步 · 数据API · 敏感检测 · 审计│
├─────────────────────────────────────────────────────────────┤
│  AI引擎: Cube-Studio (Ollama/vLLM) · PaddleOCR              │
├─────────────────────────────────────────────────────────────┤
│  ETL: Apache Hop + SeaTunnel  │  调度: DolphinScheduler     │
├─────────────────────────────────────────────────────────────┤
│  元数据: DataHub  │  BI: Superset  │  安全: ShardingSphere   │
├─────────────────────────────────────────────────────────────┤
│  基础设施: K3s · MySQL/PostgreSQL · MinIO · Redis           │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Docker 24.0+ 和 Docker Compose
- 8GB+ 内存（完整部署建议 16GB）
- 50GB+ 可用磁盘空间

### 一键部署

```bash
# 克隆项目
git clone https://github.com/your-org/one-data-studio-lite.git
cd one-data-studio-lite

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置密码和密钥

# 部署所有组件
make deploy
```

### 本地开发

```bash
# 安装 Python 依赖
make dev-install

# 本地启动门户服务
make dev-portal

# 或启动其他服务
make dev-nl2sql      # NL2SQL 服务
make dev-cleaning    # AI 清洗服务
make dev-dataapi     # 数据 API 服务
```

### 访问地址

| 服务 | 地址 | 账号密码 |
|------|------|----------|
| 统一门户 | http://localhost:8010 | admin / admin123 |
| Cube-Studio | http://localhost:30080 | - |
| Apache Superset | http://localhost:8088 | admin / admin123 |
| DataHub | http://localhost:9002 | datahub / datahub |
| DolphinScheduler | http://localhost:12345 | admin / dolphinscheduler123 |
| Apache Hop | http://localhost:8083 | - |
| SeaTunnel API | http://localhost:5801 | - |

## 项目结构

```
├── deploy/                    # 部署配置
│   ├── k3s/                   # K3s 安装脚本
│   ├── cube-studio/           # Cube-Studio Helm values
│   ├── superset/              # Apache Superset 部署
│   ├── datahub/               # DataHub 部署 + 采集配置
│   ├── hop/                   # Apache Hop ETL 引擎
│   ├── seatunnel/             # SeaTunnel 数据同步
│   ├── dolphinscheduler/      # DolphinScheduler 调度
│   └── shardingsphere/        # ShardingSphere 数据脱敏
├── services/                  # 二开微服务 (Python/FastAPI)
│   ├── common/                # 共享库 (auth, db, http, middleware)
│   ├── portal/                # 统一入口门户 (:8010)
│   ├── nl2sql/                # 自然语言查询 (:8011)
│   ├── ai_cleaning/           # AI 清洗规则推荐 (:8012)
│   ├── metadata_sync/         # 元数据联动 ETL (:8013)
│   ├── data_api/              # 数据资产 API 网关 (:8014)
│   ├── sensitive_detect/      # 敏感数据检测 (:8015)
│   └── audit_log/             # 统一审计日志 (:8016)
├── docs/                      # 文档
├── configs/                   # 配置文件
├── deploy.sh                  # 一键部署脚本
└── Makefile                   # 常用命令
```

## 六大子系统

| 子系统 | 核心组件 | 功能 |
|--------|----------|------|
| **数据规划与元数据管理** | DataHub | 元数据识别、标签管理、数据血缘 |
| **数据感知汇聚** | SeaTunnel + DolphinScheduler + Hop | 多源采集、批流一体、CDC 实时同步 |
| **数据加工融合** | SeaTunnel Transform + LLM | AI 清洗规则、数据质量检测 |
| **数据分析挖掘 (AI+BI)** | Superset + NL2SQL | BI 可视化、自然语言查询 |
| **数据资产** | DataHub + 数据 API | 资产编目、服务网关 |
| **数据安全管理** | ShardingSphere + AI | 透明脱敏、敏感数据识别 |

## 技术栈

| 类别 | 组件 | 用途 |
|------|------|------|
| 基座平台 | Cube-Studio | AI/MLOps、Jupyter、Pipeline 编排 |
| ETL 引擎 | Apache Hop | 可视化 ETL 设计（Kettle 开源替代） |
| 数据集成 | Apache SeaTunnel | 高性能数据同步，支持 200+ 数据源 |
| 任务调度 | Apache DolphinScheduler | 工作流调度 |
| 元数据 | DataHub | 元数据管理与血缘追踪 |
| BI 分析 | Apache Superset | 交互式可视化 |
| AI/LLM | Ollama / vLLM | 通过 Cube-Studio 部署 LLM 推理 |
| 数据安全 | Apache ShardingSphere | 透明数据脱敏 |
| 二开服务 | Python 3.11 + FastAPI | 微服务开发 |

## 常用命令

```bash
make help              # 显示所有命令
make deploy            # 一键部署
make stop              # 停止所有服务
make status            # 查看服务状态
make info              # 显示访问地址

# 组件管理
make superset-up       # 启动 Superset
make datahub-up        # 启动 DataHub
make services-up       # 启动二开服务

# 本地开发
make dev-install       # 安装 Python 依赖
make dev-portal        # 本地启动门户
make dev-nl2sql        # 本地启动 NL2SQL
```

## API 文档

每个二开服务都提供 OpenAPI 文档：

- 门户服务: http://localhost:8010/docs
- NL2SQL: http://localhost:8011/docs
- AI 清洗: http://localhost:8012/docs
- 元数据同步: http://localhost:8013/docs
- 数据 API: http://localhost:8014/docs
- 敏感检测: http://localhost:8015/docs
- 审计日志: http://localhost:8016/docs

## 配置说明

复制 `.env.example` 为 `.env` 并配置以下内容：

```bash
# 数据库连接
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/one_data_studio

# JWT 认证密钥
JWT_SECRET=your-secure-secret-key

# LLM 配置 (Ollama)
LLM_BASE_URL=http://localhost:31434
LLM_MODEL=qwen2.5:7b
```

完整配置项请参考 [.env.example](.env.example)。

## 文档

- [架构设计](docs/architecture.md)
- [技术选型](docs/tech-stack.md)
- [部署指南](docs/deployment.md)
- [开发指南](docs/development.md)
- [API 文档](docs/api/services.md)

## 数据流向

```
数据源 (MySQL/PostgreSQL/文件/API)
    │
    ▼
SeaTunnel (数据同步/CDC)  ←→  DolphinScheduler (调度)
    │
    ▼
Apache Hop (复杂 ETL 转换)  ←  AI 清洗规则推荐 (LLM)
    │
    ▼
数据仓库  ←→  DataHub (元数据管理)
    │                │
    ├──→ Superset (BI 分析)    ├──→ 数据资产 API
    ├──→ NL2SQL (自然语言查询)  └──→ 血缘追踪
    └──→ ShardingSphere (脱敏代理)
```

## 贡献指南

欢迎贡献代码！提交 PR 前请先阅读贡献指南。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 致谢

本项目集成了以下优秀的开源项目：

- [Cube-Studio](https://github.com/tencentmusic/cube-studio) - 腾讯音乐
- [Apache Superset](https://superset.apache.org/) - Apache 软件基金会
- [DataHub](https://datahubproject.io/) - LinkedIn
- [Apache Hop](https://hop.apache.org/) - Apache 软件基金会
- [Apache SeaTunnel](https://seatunnel.apache.org/) - Apache 软件基金会
- [Apache DolphinScheduler](https://dolphinscheduler.apache.org/) - Apache 软件基金会
- [Apache ShardingSphere](https://shardingsphere.apache.org/) - Apache 软件基金会
