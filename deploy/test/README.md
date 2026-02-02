# ONE-DATA-STUDIO-LITE 测试环境部署方案

## 概述

本测试环境通过统一基础设施、优化资源配置，实现约 35 个容器的完整测试环境部署，内存占用约 8-9GB。

## 目录结构

```
deploy/test/
├── docker-compose.yml           # 主编排文件
├── docker-compose.infra.yml     # 基础设施层
├── docker-compose.platforms.yml  # 第三方平台层
├── docker-compose.services.yml   # 二开服务层
├── .env                          # 测试环境变量
├── start.sh                      # 启动脚本
├── stop.sh                       # 停止脚本
├── status.sh                     # 状态检查
├── logs.sh                       # 日志查看
├── config/
│   ├── mysql/
│   │   ├── init.sql             # 数据库初始化
│   │   └── databases.sql        # 多数据库创建
│   ├── postgres/
│   │   └── init.sh              # PostgreSQL 初始化
│   ├── seatunnel/               # SeaTunnel 配置
│   ├── shardingsphere/          # ShardingSphere 配置
│   └── cube/                    # Cube-Studio 配置
└── README.md                    # 本文件
```

## 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 16GB 内存
- 至少 8 CPU 核心

### 启动测试环境

```bash
cd deploy/test

# 一键启动所有服务
./start.sh

# 分阶段启动
./start.sh infra      # 仅基础设施
./start.sh platforms  # 仅第三方平台
./start.sh services   # 仅二开服务
```

### 停止测试环境

```bash
cd deploy/test

# 停止所有服务（保留数据）
./stop.sh

# 停止并清理数据
./stop.sh clean
```

### 查看状态

```bash
cd deploy/test

# 状态摘要
./status.sh

# 详细状态
./status.sh detailed

# 快速健康检查
./status.sh health

# 列出容器
./status.sh containers
```

### 查看日志

```bash
cd deploy/test

# 查看特定服务日志
./logs.sh portal
./logs.sh mysql
./logs.sh datahub-gms

# 持续跟踪日志
./logs.sh portal -f

# 跟踪所有服务
./logs.sh all -f

# 查看最近 N 行
./logs.sh superset --tail 50
```

## 服务访问地址

| 服务 | 地址 | 默认凭据 |
|------|------|----------|
| Portal (统一入口) | http://localhost:8010 | admin/admin123 |
| Superset (BI) | http://localhost:8088 | admin/admin123 |
| DataHub (元数据) | http://localhost:9002 | - |
| DataHub GMS (API) | http://localhost:8081 | - |
| DolphinScheduler (调度) | http://localhost:12345 | admin/dolphinscheduler123 |
| Hop (ETL) | http://localhost:8083 | - |
| SeaTunnel (数据同步) | http://localhost:5802 | - |
| Cube-Studio (AI平台) | http://localhost:30080 | - |
| ShardingSphere (脱敏) | localhost:3309 | - |

## 基础设施连接

| 组件 | 地址 | 凭据 |
|------|------|------|
| MySQL | localhost:3306 | root/test123456 |
| PostgreSQL | localhost:5432 | postgres/postgres123 |
| Redis | localhost:6379 | :test123456 |
| etcd | localhost:2379 | - |
| Elasticsearch | localhost:9200 | - |

## 数据库

测试环境使用单个 MySQL 容器托管多个数据库：

- `one_data_studio` - 应用数据库
- `cube` - Cube-Studio 数据库
- `datahub` - DataHub 数据库
- `dolphinscheduler` - DolphinScheduler 备用数据库

PostgreSQL 托管：
- `superset` - Superset 数据库
- `dolphinscheduler` - DolphinScheduler 数据库

## 资源优化

| 组件 | 内存限制 |
|------|----------|
| MySQL | 512MB |
| Redis | 128MB |
| Zookeeper | 256MB |
| Kafka | 512MB |
| Elasticsearch | 768MB |
| PostgreSQL | 256MB |
| etcd | 128MB |
| DataHub GMS | 768MB |
| Superset | 512MB |
| DolphinScheduler API | 768MB |
| Cube-Studio | 768MB |
| 二开服务 | 256MB/个 |

## 故障排查

### 服务启动失败

1. 检查容器状态: `./status.sh detailed`
2. 查看服务日志: `./logs.sh <service>`
3. 检查资源使用: `docker stats`

### 健康检查失败

某些服务启动时间较长，请等待：

- DataHub GMS: ~2-3 分钟
- DolphinScheduler: ~1-2 分钟
- Superset: ~1 分钟
- Elasticsearch: ~1 分钟

### 端口冲突

如果默认端口被占用，可修改 `.env` 文件中的端口配置：

```bash
# 修改 Portal 端口
PORTAL_PORT=8010

# 修改 Superset 端口
SUPERSET_WEB_PORT=8088
```

## 开发调试

### 本地运行服务

如果需要本地运行某个服务进行调试：

```bash
# 设置环境变量
export DATABASE_URL=mysql+aiomysql://root:test123456@localhost:3306/one_data_studio
export JWT_SECRET=test-jwt-secret-change-in-production-32chars

# 启动服务
cd /path/to/one-data-studio-lite
uvicorn services.portal.main:app --reload --host 0.0.0.0 --port 8010
```

### 更新服务代码

服务代码更新后，需要重新构建：

```bash
cd deploy/test
docker compose -f docker-compose.services.yml up -d --build
```

## Makefile 集成

测试环境已集成到主 Makefile：

```bash
# 在项目根目录
make test-up      # 启动测试环境
make test-down    # 停止测试环境
make test-status  # 查看测试环境状态
make test-logs    # 查看测试环境日志
```

## 清理

完全清理测试环境（包括所有数据）：

```bash
cd deploy/test
./stop.sh clean
docker network rm ods-test-network 2>/dev/null || true
```

## 持久化数据

以下数据通过 Docker volumes 持久化：

- MySQL 数据: `ods-test-mysql-data`
- Redis 数据: `ods-test-redis-data`
- Elasticsearch 数据: `ods-test-es-data`
- PostgreSQL 数据: `ods-test-postgres-data`
- etcd 数据: `ods-test-etcd-data`

容器重启后数据保留，使用 `./stop.sh clean` 可完全清理。
