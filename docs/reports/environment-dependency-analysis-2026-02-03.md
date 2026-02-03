# ONE-DATA-STUDIO-LITE 环境依赖关系分析报告

**生成日期**: 2026-02-03
**分析状态**: 已完成

---

## 概述

本项目支持四种部署环境，每种环境有不同的配置、依赖和用途：

| 环境类型 | 用途 | 启动脚本 | Docker 网络 |
|---------|------|---------|-------------|
| 生产环境 (Production) | 线上部署 | `scripts/production-deploy.sh` | `ods-network` |
| 开发环境 (Development) | 本地开发 | `start-all.sh all/dev` | `ods-network` |
| 测试环境-完整版 (Test) | 集成测试 | `deploy/test/start.sh` | `ods-test-network` |
| 测试环境-精简版 (Test-Env) | 快速验证 | `deploy/test-env.sh` | `test-env-network` |

---

## 一、环境配置文件依赖

### 1.1 配置文件层级关系

```
┌─────────────────────────────────────────────────────────────────┐
│                    配置文件继承关系                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  .env.example (模板)                                            │
│       │                                                         │
│       ├──→ .env (开发环境默认配置)                              │
│       │                                                         │
│       └──→ .env.production.template                             │
│                 │                                               │
│                 └──→ .env.production (生产环境配置)             │
│                                                                 │
│  deploy/test/.env.example                                       │
│       │                                                         │
│       └──→ deploy/test/.env (测试环境配置)                      │
│                                                                 │
│  deploy/test-env/.env.example                                   │
│       │                                                         │
│       └──→ deploy/test-env/.env (精简测试环境配置)              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 环境变量差异对比

| 配置项 | 开发环境 | 测试环境 | 生产环境 |
|--------|---------|---------|---------|
| `ENVIRONMENT` | development | test | production |
| `DEBUG` | true | false | false |
| `JWT_SECRET` | 简单字符串 | 固定测试值 | 强随机字符串 (≥32位) |
| `DATABASE_URL` | localhost:3306 | mysql:3306 (容器内) | 生产数据库地址 |
| `REDIS_URL` | localhost:6379 | redis:6379 (容器内) | 生产Redis地址 |
| `LLM_BASE_URL` | localhost:31434 | host.docker.internal:31434 | ollama:11434 (容器内) |
| `ETCD_ENDPOINTS` | localhost:2379 | etcd:2379 (容器内) | 生产etcd集群 |
| `ENABLE_CONFIG_CENTER` | true | true | true |
| `ENABLE_TRACING` | false | false | true |
| `ENABLE_METRICS` | false | true | true |

---

## 二、Docker 网络依赖

### 2.1 网络拓扑

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Docker 网络架构                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐    ┌─────────────────────┐                    │
│  │    ods-network      │    │  ods-test-network   │                    │
│  │  (开发/生产环境)    │    │   (完整测试环境)    │                    │
│  │                     │    │                     │                    │
│  │  • 所有 ods-* 容器  │    │  • 所有 ods-test-*  │                    │
│  │  • external: true   │    │      容器           │                    │
│  │  • 手动创建         │    │  • external: false  │                    │
│  │                     │    │  • 自动创建         │                    │
│  └─────────────────────┘    └─────────────────────┘                    │
│                                                                         │
│  ┌─────────────────────┐                                                │
│  │ test-env-network    │                                                │
│  │ (精简测试环境)      │                                                │
│  │                     │                                                │
│  │  • 精简版容器       │                                                │
│  │  • 独立隔离         │                                                │
│  └─────────────────────┘                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 网络创建依赖

| 环境 | 网络名称 | 创建方式 | 创建脚本 |
|------|---------|---------|---------|
| 开发/生产 | `ods-network` | 手动创建 (external: true) | `docker network create ods-network` |
| 完整测试 | `ods-test-network` | 自动创建 (docker-compose.infra.yml) | `docker compose up` |
| 精简测试 | `test-env-network` | 手动创建 | `deploy/test-env.sh` |

---

## 三、启动脚本依赖链

### 3.1 生产环境启动流程

```
scripts/production-deploy.sh
│
├── 1. 前置检查
│   ├── 检查 .env.production 存在
│   ├── 加载环境变量
│   └── 安全配置检查
│       ├── JWT_SECRET 不能是默认值
│       ├── JWT_SECRET 长度 ≥ 32
│       └── DATABASE_URL 不能包含默认密码
│
├── 2. 创建备份
│   └── backup/production-YYYYMMDD-HHMMSS/
│
├── 3. 创建网络
│   └── docker network create ods-network
│
├── 4. 启动基础设施 (顺序启动)
│   ├── deploy/etcd/docker-compose.yml
│   ├── deploy/mysql/docker-compose.yml
│   └── deploy/redis/docker-compose.yml
│   └── sleep 10 (等待就绪)
│
├── 5. 启动外部组件 (并行启动)
│   ├── deploy/datahub/docker-compose.yml
│   ├── deploy/superset/docker-compose.yml
│   └── deploy/dolphinscheduler/docker-compose.yml
│   └── sleep 30 (等待就绪)
│
├── 6. 启动内部服务
│   └── services/docker-compose.yml --env-file .env.production
│
├── 7. 启动监控
│   ├── deploy/loki/docker-compose.yml
│   ├── deploy/prometheus/docker-compose.yml
│   └── deploy/alertmanager/docker-compose.yml
│
└── 8. 启动反向代理
    └── deploy/nginx/docker-compose.yml
```

### 3.2 开发环境启动流程

```
start-all.sh all
│
├── 1. 检查依赖
│   ├── Docker
│   ├── Docker Compose
│   ├── Node.js (可选)
│   └── npm (可选)
│
├── 2. 创建网络
│   └── docker network create ods-network
│
├── 3. 启动第三方平台 (start_platforms)
│   ├── k3s (可选，SKIP_K3S=1 跳过)
│   ├── Cube-Studio (可选，SKIP_CUBE_STUDIO=1 跳过)
│   ├── Superset → 等待 :8088/health (180s)
│   ├── DataHub → 等待 :9002 (240s)
│   ├── Hop
│   ├── SeaTunnel
│   ├── DolphinScheduler → 等待 :12345 (180s)
│   └── ShardingSphere
│
├── 4. 启动后端服务 (start_services)
│   └── services/docker-compose.yml --build
│   └── 等待 Portal :8010/health (60s)
│
└── 5. 启动前端 (可选)
    └── npm run dev (后台运行)
```

### 3.3 本地开发模式

```
start-all.sh dev
│
├── 1. 检查 Python 环境
│
├── 2. 安装依赖
│   └── pip install -r services/requirements.txt
│
├── 3. 启动 7 个微服务 (uvicorn 直接启动)
│   ├── portal         :8010 → logs/portal.log
│   ├── nl2sql         :8011 → logs/nl2sql.log
│   ├── ai_cleaning    :8012 → logs/ai_cleaning.log
│   ├── metadata_sync  :8013 → logs/metadata_sync.log
│   ├── data_api       :8014 → logs/data_api.log
│   ├── sensitive_detect :8015 → logs/sensitive_detect.log
│   └── audit_log      :8016 → logs/audit_log.log
│
└── 4. 启动前端
    └── npm run dev (后台运行)
```

### 3.4 完整测试环境启动流程

```
deploy/test/start.sh all
│
├── 阶段 1/3: 基础设施 (stage1_infra)
│   └── docker-compose.infra.yml
│       ├── mysql → 等待 healthy (60s)
│       ├── redis → 等待 healthy (30s)
│       ├── zookeeper → 等待 healthy (30s)
│       ├── kafka → depends_on: zookeeper
│       ├── schema-registry → depends_on: kafka
│       ├── elasticsearch → 等待 healthy (120s)
│       ├── postgres → 等待 healthy (30s)
│       └── etcd → 等待 healthy (30s)
│
├── 阶段 2/3: 第三方平台 (stage2_platforms)
│   └── docker-compose.infra.yml + docker-compose.platforms.yml
│       ├── DataHub (mysql-setup → es-setup → kafka-setup → gms → frontend/actions)
│       │   └── 等待 datahub-gms healthy (180s)
│       ├── Superset (init → superset)
│       │   └── 等待 superset healthy (120s)
│       ├── DolphinScheduler (schema-init → api/master/worker/alert)
│       │   └── 等待 ds-api healthy (120s)
│       ├── Hop
│       ├── SeaTunnel
│       ├── ShardingSphere
│       └── Cube-Studio (myapp → frontend)
│           └── 等待 cube-myapp healthy (120s)
│
└── 阶段 3/3: 二开服务 (stage3_services)
    └── docker-compose.infra.yml + docker-compose.platforms.yml + docker-compose.services.yml
        └── 7 个微服务 → 等待 portal healthy (60s)
```

---

## 四、环境间服务地址映射

### 4.1 服务地址对照表

| 服务 | 开发环境 (本地) | 开发环境 (Docker) | 测试环境 | 生产环境 |
|------|---------------|------------------|---------|---------|
| MySQL | localhost:3306 | mysql:3306 | mysql:3306 | mysql:3306 |
| Redis | localhost:6379 | redis:6379 | redis:6379 | redis:6379 |
| etcd | localhost:2379 | etcd:2379 | etcd:2379 | etcd:2379 |
| DataHub GMS | localhost:8081 | datahub-gms:8080 | datahub-gms:8080 | datahub-gms:8080 |
| DataHub UI | localhost:9002 | datahub-frontend:9002 | datahub-frontend:9002 | localhost:9002 |
| Superset | localhost:8088 | superset:8088 | superset:8088 | localhost:8088 |
| DolphinScheduler | localhost:12345 | dolphinscheduler-api:12345 | dolphinscheduler-api:12345 | localhost:12345 |
| Cube-Studio | localhost:30080 | cube-frontend:80 | cube-frontend:80 | localhost:30080 |
| Hop | localhost:8083 | hop:8080 | hop:8080 | localhost:8083 |
| SeaTunnel | localhost:5802 | seatunnel:5802 | seatunnel:5802 | localhost:5802 |
| ShardingSphere | localhost:3309 | shardingsphere:3307 | shardingsphere:3307 | localhost:3309 |
| LLM (Ollama) | localhost:31434 | host.docker.internal:31434 | host.docker.internal:31434 | ollama:11434 |

### 4.2 容器命名规则

| 环境 | 容器名前缀 | 示例 |
|------|----------|------|
| 开发/生产 | `ods-` | ods-portal, ods-superset |
| 完整测试 | `ods-test-` | ods-test-portal, ods-test-mysql |
| 精简测试 | `test-env-` | test-env-portal |

---

## 五、资源配置依赖

### 5.1 内存需求对比

| 环境 | 最小内存 | 推荐内存 | 说明 |
|------|---------|---------|------|
| 本地开发模式 | 4GB | 8GB | 仅运行 7 个微服务 |
| Docker 开发环境 | 8GB | 16GB | 包含第三方平台 |
| 完整测试环境 | 12GB | 24GB | 所有服务 + 资源限制 |
| 生产环境 | 16GB+ | 32GB+ | 高可用配置 |

### 5.2 测试环境资源限制

测试环境 (`deploy/test/`) 配置了明确的资源限制：

| 服务类别 | limits.memory | reservations.memory |
|---------|--------------|-------------------|
| MySQL | 512M | 256M |
| Redis | 128M | 64M |
| Zookeeper | 256M | 128M |
| Kafka | 512M | 256M |
| Elasticsearch | 768M | 512M |
| PostgreSQL | 256M | 128M |
| etcd | 128M | 64M |
| DataHub GMS | 768M | 512M |
| DataHub Frontend | 128M | - |
| Superset | 512M | 256M |
| DolphinScheduler API | 768M | - |
| 微服务 (each) | 256M | 128M |

---

## 六、环境间依赖关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        环境依赖关系总览                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                    生产环境 (Production)                       │     │
│  │  scripts/production-deploy.sh                                  │     │
│  │  .env.production                                               │     │
│  │  ods-network                                                   │     │
│  │                                                                │     │
│  │  依赖:                                                         │     │
│  │  • 所有 Docker Compose 配置                                    │     │
│  │  • Nginx 反向代理                                              │     │
│  │  • 监控系统 (Loki/Prometheus/Alertmanager)                     │     │
│  │  • 安全配置校验                                                │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ▲                                          │
│                              │ 配置升级                                 │
│  ┌───────────────────────────┴───────────────────────────────────┐     │
│  │                    开发环境 (Development)                      │     │
│  │  start-all.sh / deploy.sh                                      │     │
│  │  services/.env                                                 │     │
│  │  ods-network                                                   │     │
│  │                                                                │     │
│  │  模式:                                                         │     │
│  │  • Docker 模式: start-all.sh all                              │     │
│  │  • 本地模式: start-all.sh dev (uvicorn 直接启动)              │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ▲                                          │
│                              │ 配置隔离                                 │
│  ┌───────────────────────────┴───────────────────────────────────┐     │
│  │                   完整测试环境 (Test)                          │     │
│  │  deploy/test/start.sh                                          │     │
│  │  deploy/test/.env                                              │     │
│  │  ods-test-network                                              │     │
│  │                                                                │     │
│  │  特点:                                                         │     │
│  │  • 三阶段启动 (infra → platforms → services)                  │     │
│  │  • 资源限制配置                                                │     │
│  │  • 共享基础设施 (MySQL/Redis/Zookeeper)                        │     │
│  │  • 健康检查完善                                                │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ▲                                          │
│                              │ 精简版                                   │
│  ┌───────────────────────────┴───────────────────────────────────┐     │
│  │                  精简测试环境 (Test-Env)                       │     │
│  │  deploy/test-env.sh                                            │     │
│  │  deploy/test-env/.env                                          │     │
│  │  test-env-network                                              │     │
│  │                                                                │     │
│  │  特点:                                                         │     │
│  │  • 快速启动                                                    │     │
│  │  • 精简服务集                                                  │     │
│  │  • Cube-Studio Lite (静态页面)                                │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 七、环境切换注意事项

### 7.1 从开发环境到测试环境

```bash
# 1. 停止开发环境
./start-all.sh stop

# 2. 启动测试环境
cd deploy/test
./start.sh all
```

**注意事项**:
- 网络隔离: `ods-network` vs `ods-test-network`
- 容器名不同: `ods-*` vs `ods-test-*`
- 端口相同，不能同时运行

### 7.2 从开发环境到生产环境

```bash
# 1. 复制并配置生产环境变量
cp services/.env.production.template services/.env.production
# 编辑 .env.production，替换所有 __CHANGE_ME__ 值

# 2. 运行生产部署
bash scripts/production-deploy.sh
```

**必须修改的配置**:
- `JWT_SECRET`: 使用 `openssl rand -hex 32` 生成
- `DATABASE_URL`: 生产数据库连接
- `SERVICE_SECRET` / `INTERNAL_TOKEN`: 服务间通信密钥
- `CONFIG_ENCRYPTION_KEY`: etcd 加密密钥
- 各平台 Token (DataHub, DolphinScheduler, Superset)

### 7.3 本地开发模式 vs Docker 模式

| 对比项 | 本地开发模式 (`dev`) | Docker 模式 (`all`) |
|--------|---------------------|-------------------|
| 启动方式 | uvicorn 直接启动 | docker compose up |
| 热重载 | 支持 (--reload) | 需重建镜像 |
| 调试 | 方便 | 需要 attach |
| 依赖服务 | 需手动启动 | 自动启动 |
| 资源占用 | 低 | 高 |
| 环境一致性 | 差 | 好 |

---

## 八、常见问题排查

### 8.1 网络问题

```bash
# 检查网络是否存在
docker network ls | grep ods

# 手动创建网络
docker network create ods-network

# 检查容器是否在正确网络
docker inspect <container_name> | grep -A 10 Networks
```

### 8.2 端口冲突

```bash
# 检查端口占用
lsof -i :8010  # Portal
lsof -i :8088  # Superset
lsof -i :9002  # DataHub

# 停止占用进程
kill <PID>
```

### 8.3 环境变量未生效

```bash
# 检查环境变量
docker exec <container_name> env | grep -E "(DATABASE|REDIS|JWT)"

# 重新启动并强制读取新配置
docker compose up -d --force-recreate
```

---

## 九、总结

### 9.1 环境依赖关系核心要点

1. **网络隔离**: 每种环境使用独立的 Docker 网络，避免冲突
2. **配置分离**: 通过不同的 `.env` 文件管理环境特定配置
3. **启动顺序**: 严格遵循 基础设施 → 第三方平台 → 二开服务 的顺序
4. **资源管理**: 测试环境有明确的资源限制，生产环境需要更多资源
5. **服务发现**: 容器内使用服务名，容器外使用 localhost

### 9.2 推荐工作流

```
本地开发 (start-all.sh dev)
    │
    ▼
完整测试 (deploy/test/start.sh all)
    │
    ▼
生产部署 (scripts/production-deploy.sh)
```

---

## 附录：快速参考命令

```bash
# 开发环境
./start-all.sh all           # Docker 模式启动
./start-all.sh dev           # 本地模式启动
./start-all.sh stop          # 停止所有
./start-all.sh status        # 查看状态

# 完整测试环境
cd deploy/test
./start.sh all               # 启动所有
./start.sh infra             # 仅启动基础设施
./start.sh platforms         # 仅启动平台层
./start.sh services          # 仅启动服务层

# 精简测试环境
./deploy/test-env.sh         # 一键启动

# 生产环境
bash scripts/production-deploy.sh  # 部署

# 通用命令
make status                  # 查看状态
make services-logs          # 查看服务日志
docker compose ps           # Docker 容器状态
```
