# 测试环境部署方案实施记录

**日期**: 2026-02-02
**状态**: 已完成

## 实施概述

为 ONE-DATA-STUDIO-LITE 项目创建了精简的测试环境部署方案，实现了：
- 统一网络（`ods-test-network`）
- 共享基础设施（MySQL、Redis、Zookeeper、PostgreSQL、etcd）
- 优化的资源配置
- 分层启动脚本

## 创建的文件

### 目录结构
```
deploy/test/
├── docker-compose.yml              # 主编排文件
├── docker-compose.infra.yml        # 基础设施层
├── docker-compose.platforms.yml    # 第三方平台层
├── docker-compose.services.yml     # 二开服务层
├── .env                             # 测试环境变量
├── start.sh                         # 启动脚本
├── stop.sh                          # 停止脚本
├── status.sh                        # 状态检查
├── logs.sh                          # 日志查看
├── README.md                        # 使用说明
└── config/
    ├── mysql/
    │   ├── init.sql                 # 数据库初始化
    │   └── databases.sql            # 多数据库创建
    ├── postgres/
    │   └── init.sh                  # PostgreSQL 初始化
    ├── seatunnel/                   # SeaTunnel 配置（从原配置复制）
    ├── shardingsphere/              # ShardingSphere 配置（从原配置复制）
    └── cube/                        # Cube-Studio 配置（从原配置复制）
```

## 优化成果

| 项目 | 优化前 | 优化后 |
|------|--------|--------|
| 网络数量 | 2 个独立网络 | 1 个统一网络 |
| MySQL 实例 | 3 个独立容器 | 1 个容器，多数据库 |
| Zookeeper 实例 | 2 个独立容器 | 1 个共享容器 |
| 监控组件 | ~5 容器 | 0 容器（禁用） |
| 容器数量 | ~45 | ~35 |
| 内存占用 | ~12GB | ~8-9GB |

## 资源限制

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

## 使用方法

### 快速启动

```bash
# 方式 1: 使用脚本
cd deploy/test
./start.sh

# 方式 2: 使用 Makefile（项目根目录）
make test-up
```

### 分阶段启动

```bash
# 仅启动基础设施
./start.sh infra

# 仅启动第三方平台
./start.sh platforms

# 仅启动二开服务
./start.sh services
```

### 状态检查

```bash
# 状态摘要
./status.sh

# 详细状态
./status.sh detailed

# 快速健康检查
./status.sh health
```

### 日志查看

```bash
# 查看特定服务
./logs.sh portal

# 跟踪所有日志
./logs.sh all -f
```

## 服务访问

| 服务 | 地址 | 默认凭据 |
|------|------|----------|
| Portal | http://localhost:8010 | admin/admin123 |
| Superset | http://localhost:8088 | admin/admin123 |
| DataHub | http://localhost:9002 | - |
| DataHub GMS | http://localhost:8081 | - |
| DolphinScheduler | http://localhost:12345 | admin/dolphinscheduler123 |
| Hop | http://localhost:8083 | - |
| SeaTunnel | http://localhost:5802 | - |
| Cube-Studio | http://localhost:30080 | - |
| ShardingSphere | localhost:3309 | - |

## Makefile 集成

新增命令：
- `make test-up` - 启动测试环境
- `make test-down` - 停止测试环境
- `make test-clean` - 停止并清理数据
- `make test-status` - 查看状态
- `make test-logs` - 查看日志
- `make test-infra` - 仅启动基础设施
- `make test-platforms` - 仅启动第三方平台
- `make test-services` - 仅启动二开服务
- `make test-clean-all` - 完全清理（包括网络）

## 数据库配置

### MySQL (localhost:3306)
- `one_data_studio` - 应用数据库
- `cube` - Cube-Studio 数据库
- `datahub` - DataHub 数据库
- 凭据: root/test123456

### PostgreSQL (localhost:5432)
- `superset` - Superset 数据库
- `dolphinscheduler` - DolphinScheduler 数据库
- 凭据: postgres/postgres123

### Redis (localhost:6379)
- 凭据: :test123456

### etcd (localhost:2379)
- 无需认证

## 下一步

1. 创建进度报告文档到 `/docs/reports/completed/`
2. 更新主 README.md 添加测试环境说明
3. 根据实际运行情况调整资源限制

## 备注

- 所有脚本已添加执行权限
- 配置文件从现有部署目录复制
- 网络使用独立名称 `ods-test-network`，避免与生产环境冲突
