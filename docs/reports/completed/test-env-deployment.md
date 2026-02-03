# 测试环境部署方案 - 完成报告

**完成日期**: 2026-02-02
**实施人员**: Claude Code
**文档版本**: 1.0

## 1. 背景与目标

### 1.1 背景
原有部署环境存在以下问题：
- 网络不统一（`ods-network` 和 `one-data-studio-network` 混用）
- 多个独立 docker-compose.yml 文件，管理复杂
- MySQL 实例重复（应用、Cube-Studio、DataHub 各自一个）
- Zookeeper 实例重复（DataHub 和 DolphinScheduler 各自一个）
- 监控组件占用资源较多
- 资源限制未针对测试环境优化

### 1.2 目标
创建一个精简的测试环境部署方案，用于集成测试：
- 保留所有功能组件
- 通过优化配置降低资源占用
- 提供一键启动脚本
- 统一网络和基础设施

## 2. 实施内容

### 2.1 创建的文件结构

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
    ├── seatunnel/                   # SeaTunnel 配置
    ├── shardingsphere/              # ShardingSphere 配置
    └── cube/                        # Cube-Studio 配置
```

### 2.2 优化措施

1. **禁用监控组件**（节省 5 容器）
   - 移除 Loki, Promtail, Grafana 监控堆栈
   - 移除 Prometheus, Alertmanager

2. **共享基础设施**
   - MySQL：整合为单个容器，多数据库（one_data_studio, cube, datahub）
   - Zookeeper：DataHub 和 DolphinScheduler 共享
   - Redis：Cube-Studio 和 Superset 共享
   - PostgreSQL：Superset 和 DolphinScheduler 共享
   - Elasticsearch：DataHub 专用
   - etcd：配置中心

3. **降低资源限制**
   - Elasticsearch: 1g → 768M
   - DataHub GMS: 1g → 768M
   - DolphinScheduler API: 1g → 768M
   - Superset: 默认 → 512M
   - 二开服务: 默认 → 256M

4. **统一网络**
   - 使用 `ods-test-network` 作为统一网络

### 2.3 实施效果

| 项目 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| 网络数量 | 2 个 | 1 个 | -50% |
| MySQL 实例 | 3 个 | 1 个 | -67% |
| Zookeeper 实例 | 2 个 | 1 个 | -50% |
| Redis 实例 | 2 个 | 1 个 | -50% |
| 监控容器 | ~5 个 | 0 个 | -100% |
| 总容器数量 | ~45 | ~35 | -22% |
| 内存占用 | ~12GB | ~8-9GB | -25% |

## 3. 使用指南

### 3.1 快速启动

```bash
# 方式 1: 使用脚本
cd deploy/test
./start.sh

# 方式 2: 使用 Makefile（项目根目录）
make test-up
```

### 3.2 分阶段启动

```bash
# 仅启动基础设施
./start.sh infra

# 仅启动第三方平台
./start.sh platforms

# 仅启动二开服务
./start.sh services
```

### 3.3 状态检查

```bash
# 状态摘要
./status.sh

# 详细状态
./status.sh detailed

# 快速健康检查
./status.sh health
```

### 3.4 日志查看

```bash
# 查看特定服务
./logs.sh portal

# 跟踪所有日志
./logs.sh all -f
```

### 3.5 停止与清理

```bash
# 停止（保留数据）
./stop.sh

# 停止并清理数据
./stop.sh clean
```

## 4. 服务访问

### 4.1 Web 界面

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

### 4.2 数据库连接

| 组件 | 地址 | 凭据 |
|------|------|------|
| MySQL | localhost:3306 | root/test123456 |
| PostgreSQL | localhost:5432 | postgres/postgres123 |
| Redis | localhost:6379 | :test123456 |
| etcd | localhost:2379 | - |
| Elasticsearch | localhost:9200 | - |

### 4.3 二开服务 API

| 服务 | 端口 |
|------|------|
| Portal | 8010 |
| NL2SQL | 8011 |
| AI Cleaning | 8012 |
| Metadata Sync | 8013 |
| Data API | 8014 |
| Sensitive Detect | 8015 |
| Audit Log | 8016 |

## 5. Makefile 集成

新增命令已集成到主 Makefile：

```bash
make test-up        # 启动测试环境
make test-down      # 停止测试环境
make test-clean     # 停止并清理数据
make test-status    # 查看状态
make test-logs      # 查看日志
make test-infra     # 仅启动基础设施
make test-platforms # 仅启动第三方平台
make test-services  # 仅启动二开服务
make test-clean-all # 完全清理
```

## 6. 技术细节

### 6.1 启动顺序

1. 网络 (ods-test-network)
2. 基础设施 (30s)
   - MySQL, Redis, Zookeeper, Kafka, Elasticsearch, PostgreSQL, etcd
3. 依赖服务 (60s)
   - Schema Registry
4. 核心平台 (120-180s)
   - DataHub, Superset, DolphinScheduler, Hop, SeaTunnel, ShardingSphere, Cube-Studio
5. 二开服务 (30s)
   - 7 个 FastAPI 服务

### 6.2 资源分配

| 类别 | 组件 | 内存 |
|------|------|------|
| 基础设施 | MySQL, Redis, ZK, Kafka, ES, PG, etcd | ~2.5GB |
| DataHub | GMS, Frontend, Actions | ~1GB |
| Superset | Web, Worker | ~1GB |
| DolphinScheduler | API, Master, Worker, Alert | ~1.5GB |
| Cube-Studio | Frontend, MyApp | ~1GB |
| Hop + SeaTunnel | - | ~1GB |
| ShardingSphere | - | ~512MB |
| 二开服务 | 7 个服务 | ~1.75GB |
| **总计** | | **~9GB** |

### 6.3 数据持久化

数据通过 Docker volumes 持久化：
- `ods-test-mysql-data` - MySQL 数据
- `ods-test-redis-data` - Redis 数据
- `ods-test-es-data` - Elasticsearch 数据
- `ods-test-postgres-data` - PostgreSQL 数据
- `ods-test-etcd-data` - etcd 数据

## 7. 验证方法

### 7.1 容器状态检查

```bash
docker ps --filter "name=ods-test-"
```

### 7.2 健康检查

```bash
cd deploy/test
./status.sh health
```

### 7.3 功能验证

1. 访问 Portal: http://localhost:8010
2. 登录 Superset: http://localhost:8088
3. 访问 DataHub: http://localhost:9002
4. 访问 DolphinScheduler: http://localhost:12345

## 8. 后续建议

1. 根据实际运行情况调整资源限制
2. 添加 CI/CD 集成测试脚本
3. 创建测试数据初始化脚本
4. 考虑添加健康检查自动修复机制

## 9. 相关文档

- 部署脚本: `deploy/test/start.sh`
- 状态检查: `deploy/test/status.sh`
- 使用说明: `deploy/test/README.md`
- 进度记录: `docs/progress/test-env-deployment-20260202.md`
