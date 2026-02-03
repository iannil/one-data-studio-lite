# ONE-DATA-STUDIO-LITE 启动环境与服务代码梳理

> **梳理日期**: 2026-02-03
> **任务**: 梳理当前项目所有涉及启动环境或服务的代码逻辑或脚本
> **状态**: 已完成

---

## 概述

项目启动机制分为 **5 个层级**：

```
┌─────────────────────────────────────────────────────────────┐
│  1. 顶层启动脚本 (deploy.sh, start-all.sh)                  │
├─────────────────────────────────────────────────────────────┤
│  2. Makefile 目标 (make deploy, make services-up, ...)      │
├─────────────────────────────────────────────────────────────┤
│  3. Docker Compose 配置 (15 个 docker-compose.yml 文件)     │
├─────────────────────────────────────────────────────────────┤
│  4. Python 服务启动 (uvicorn + FastAPI lifespan)            │
├─────────────────────────────────────────────────────────────┤
│  5. 辅助脚本 (测试环境、生产部署、备份恢复)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. 顶层启动脚本

### 1.1 deploy.sh (一键部署脚本)

**路径**: `/deploy.sh`

**功能**: 按顺序部署所有组件到单机开发环境

**命令**:
```bash
./deploy.sh deploy   # 全量部署
./deploy.sh stop     # 停止所有服务
./deploy.sh status   # 查看状态
./deploy.sh info     # 显示访问地址
```

**启动顺序**:
1. 创建 Docker 网络 (`ods-network`)
2. k3s (可选，`SKIP_K3S=1` 跳过)
3. Cube-Studio (可选，`SKIP_CUBE_STUDIO=1` 跳过)
4. Apache Superset → 等待健康检查 (120s)
5. DataHub → 等待健康检查 (180s)
6. Apache Hop
7. Apache SeaTunnel
8. DolphinScheduler → 等待健康检查 (120s)
9. ShardingSphere
10. 二开服务 (`services/docker-compose.yml`)

**关键函数**:
- `create_network()` - 创建 Docker 网络
- `deploy_component()` - 部署单个组件
- `wait_for_service()` - 等待服务健康检查
- `stop_all()` - 停止所有服务
- `print_access_info()` - 打印访问地址

**代码位置**: `/deploy.sh:23-179`

---

### 1.2 start-all.sh (全量启动脚本)

**路径**: `/start-all.sh`

**功能**: 更灵活的启动选项，支持本地开发模式

**命令**:
```bash
./start-all.sh all        # 启动所有 (平台+后端+前端)
./start-all.sh platforms  # 仅启动第三方平台
./start-all.sh services   # 仅启动后端微服务 (Docker)
./start-all.sh web        # 仅启动前端开发服务器
./start-all.sh dev        # 本地开发模式 (不用 Docker)
./start-all.sh stop       # 停止所有
./start-all.sh status     # 查看状态
./start-all.sh info       # 显示访问地址
```

**选项**:
- `--skip-k3s` - 跳过 k3s
- `--skip-cube-studio` - 跳过 Cube-Studio
- `--no-wait` - 不等待服务就绪
- `--no-web` - 不启动前端
- `--web-build` - 构建前端生产版本

**本地开发模式** (`dev`):
- 使用 `uvicorn --reload` 启动 7 个服务
- PID 文件保存在 `logs/*.pid`
- 日志保存在 `logs/*.log`

**关键函数**:
- `check_dependencies()` - 检查 Docker/Node.js 环境
- `create_network()` - 创建 Docker 网络
- `wait_for_service()` - 等待服务就绪
- `start_platforms()` - 启动第三方平台
- `start_services()` - 启动后端微服务
- `start_web()` - 启动前端
- `start_dev_mode()` - 本地开发模式
- `stop_all()` - 停止所有服务
- `show_status()` - 查看状态
- `print_access_info()` - 打印访问地址

**代码位置**: `/start-all.sh:1-527`

---

## 2. Makefile 目标

**路径**: `/Makefile`

### 2.1 部署命令

| 命令 | 功能 | 实际执行 |
|------|------|---------|
| `make deploy` | 一键部署 | `bash deploy.sh deploy` |
| `make stop` | 停止所有 | `bash deploy.sh stop` |
| `make status` | 查看状态 | `bash deploy.sh status` |
| `make info` | 显示地址 | `bash deploy.sh info` |

### 2.2 全量启动

| 命令 | 功能 |
|------|------|
| `make start-all` | 启动所有服务 |
| `make start-platforms` | 仅启动第三方平台 |
| `make start-services` | 仅启动后端微服务 |
| `make start-web` | 仅启动前端 |
| `make start-dev` | 本地开发模式 |
| `make stop-all` | 停止所有服务 |

### 2.3 单组件启动

| 命令 | 组件 | 端口 |
|------|------|------|
| `make superset-up` | Apache Superset | 8088 |
| `make datahub-up` | DataHub | 9002 |
| `make dolphinscheduler-up` | DolphinScheduler | 12345 |
| `make seatunnel-up` | SeaTunnel | 5801 |
| `make hop-up` | Apache Hop | 8083 |
| `make shardingsphere-up` | ShardingSphere | 3309 |
| `make cube-studio-up` | Cube-Studio | 30080 |
| `make etcd-up` | etcd 配置中心 | 2379 |
| `make services-up` | 7 个微服务 | 8010-8016 |
| `make loki-up` | Loki 日志 | 3100 |
| `make monitoring-up` | 监控系统 | 3000, 3100 |

### 2.4 本地开发

| 命令 | 服务 | 端口 |
|------|------|------|
| `make dev-install` | 安装依赖 | - |
| `make dev-portal` | Portal | 8010 |
| `make dev-nl2sql` | NL2SQL | 8011 |
| `make dev-cleaning` | AI Cleaning | 8012 |
| `make dev-metadata` | Metadata Sync | 8013 |
| `make dev-dataapi` | Data API | 8014 |
| `make dev-sensitive` | Sensitive Detect | 8015 |
| `make dev-audit` | Audit Log | 8016 |

### 2.5 测试环境

| 命令 | 功能 |
|------|------|
| `make test-env-up` | 启动测试环境 |
| `make test-env-down` | 停止测试环境 |
| `make test-env-status` | 查看状态 |
| `make test-env-logs` | 查看日志 |
| `make test-env-clean` | 清理数据 |

**代码位置**: `/Makefile:1-424`

---

## 3. Docker Compose 配置文件

共 **15 个** Docker Compose 文件：

### 3.1 核心服务 - services/docker-compose.yml

**路径**: `/services/docker-compose.yml`

**定义的服务** (7 个微服务):

| 服务 | 容器名 | 端口 | 启动命令 |
|------|--------|------|---------|
| portal | ods-portal | 8010 | `uvicorn services.portal.main:app` |
| nl2sql | ods-nl2sql | 8011 | `uvicorn services.nl2sql.main:app` |
| ai-cleaning | ods-ai-cleaning | 8012 | `uvicorn services.ai_cleaning.main:app` |
| metadata-sync | ods-metadata-sync | 8013 | `uvicorn services.metadata_sync.main:app` |
| data-api | ods-data-api | 8014 | `uvicorn services.data_api.main:app` |
| sensitive-detect | ods-sensitive-detect | 8015 | `uvicorn services.sensitive_detect.main:app` |
| audit-log | ods-audit-log | 8016 | `uvicorn services.audit_log.main:app` |

**公共配置** (YAML anchor):
```yaml
x-service-common:
  build:
    context: ..
    dockerfile: services/Dockerfile
  restart: unless-stopped
  networks:
    - ods-network
  environment:
    DATABASE_URL: mysql+aiomysql://...
    JWT_SECRET: ...
    LLM_BASE_URL: ...
```

**网络**: `ods-network` (external)

**代码位置**: `/services/docker-compose.yml:1-95`

---

### 3.2 测试环境 - deploy/test-env/docker-compose.yml

**路径**: `/deploy/test-env/docker-compose.yml`

**特点**:
- 精简资源配置 (内存 < 3GB)
- 包含完整的开发组件

**定义的服务**:

| 类别 | 服务 | 内存限制 |
|------|------|---------|
| 基础设施 | mysql, redis, minio | 256M, 64M, 128M |
| DataHub | mysql, es, zk, kafka, schema-registry, gms, frontend | 128M-512M |
| Superset | db (postgres), redis, superset | 64M-512M |
| Cube-Studio | cube-studio-lite (nginx) | 64M |
| 微服务 | portal, nl2sql, ai-cleaning, metadata-sync, data-api, sensitive-detect, audit-log | 128M 每个 |

**代码位置**: `/deploy/test-env/docker-compose.yml:1-599`

---

### 3.3 外部组件 Docker Compose 文件

| 路径 | 组件 | 主要端口 |
|------|------|---------|
| `deploy/superset/docker-compose.yml` | Apache Superset | 8088 |
| `deploy/datahub/docker-compose.yml` | DataHub | 9002, 8081 |
| `deploy/dolphinscheduler/docker-compose.yml` | DolphinScheduler | 12345 |
| `deploy/seatunnel/docker-compose.yml` | SeaTunnel | 5801, 5802 |
| `deploy/hop/docker-compose.yml` | Apache Hop | 8083 |
| `deploy/shardingsphere/docker-compose.yml` | ShardingSphere | 3309 |
| `deploy/cube-studio/docker-compose.yml` | Cube-Studio | 30080 |
| `deploy/etcd/docker-compose.yml` | etcd 配置中心 | 2379 |
| `deploy/mysql/docker-compose.yml` | MySQL | 3306 |
| `deploy/loki/docker-compose.yml` | Loki + Promtail + Grafana | 3100, 3000 |
| `deploy/prometheus/docker-compose.yml` | Prometheus | 9090 |
| `deploy/alertmanager/docker-compose.yml` | Alertmanager | 9093 |
| `deploy/nginx/docker-compose.yml` | Nginx 反向代理 | 80, 443 |

---

## 4. Python 服务启动逻辑

### 4.1 入口点结构

每个服务的 `main.py` 结构（以 Portal 为例）：

```python
# services/{service}/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    check_security_configuration()
    await init_config_center()
    yield
    # 关闭时执行
    await cleanup()

app = FastAPI(lifespan=lifespan)

# 注册中间件
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, ...)
app.add_middleware(RequestLoggingMiddleware)

# 注册异常处理器
register_exception_handlers(app)

# 设置 Metrics
setup_metrics(app)

# 注册路由
app.include_router(...)
```

### 4.2 服务入口文件

| 服务 | 入口文件 | 端口 |
|------|---------|------|
| Portal | `services/portal/main.py` | 8010 |
| NL2SQL | `services/nl2sql/main.py` | 8011 |
| AI Cleaning | `services/ai_cleaning/main.py` | 8012 |
| Metadata Sync | `services/metadata_sync/main.py` | 8013 |
| Data API | `services/data_api/main.py` | 8014 |
| Sensitive Detect | `services/sensitive_detect/main.py` | 8015 |
| Audit Log | `services/audit_log/main.py` | 8016 |

### 4.3 启动时初始化逻辑

1. **安全配置检查** (`check_security_configuration`)
   - 验证 JWT_SECRET 配置
   - 验证 DATABASE_URL 配置
   - 生产环境强制检查，不合格则抛出异常

2. **配置中心初始化** (`init_config_center`)
   - 连接 etcd
   - 加载动态配置

3. **中间件注册**
   - CORS 中间件
   - 安全响应头中间件
   - 速率限制中间件
   - 请求日志中间件

4. **路由注册**
   - 各业务模块路由
   - 健康检查端点 (`/health`, `/health/all`)
   - 安全检查端点 (`/security/check`)

**代码位置**: `/services/portal/main.py:64-243`

---

## 5. 辅助脚本

### 5.1 生产部署脚本

**路径**: `/scripts/production-deploy.sh`

**执行流程**:
1. 检查 `.env.production` 文件
2. 安全配置验证 (JWT_SECRET 不能是默认值)
3. 备份当前配置到 `backup/production-{timestamp}/`
4. 创建 Docker 网络
5. 启动基础设施: etcd → MySQL → Redis
6. 等待 10 秒
7. 启动外部组件: DataHub → Superset → DolphinScheduler
8. 等待 30 秒
9. 启动内部服务 (带 `--env-file .env.production`)
10. 启动监控: Loki → Prometheus → Alertmanager
11. 启动 Nginx

**前置条件**:
```bash
# 先运行初始化
bash scripts/setup-production.sh
```

**代码位置**: `/scripts/production-deploy.sh:1-141`

---

### 5.2 测试环境脚本

**启动**: `/deploy/test-env.sh`

**关键函数**:
```bash
check_docker()            # 检查 Docker 环境
check_env()               # 检查配置文件
create_network()          # 创建网络 (test-env-network)
create_directories()      # 创建目录
create_cube_studio_lite() # 创建精简页面
pull_images()             # 拉取镜像
start_services()          # 启动服务
wait_for_services()       # 等待就绪
show_access_info()        # 显示访问信息
```

**停止**: `/deploy/test-env-stop.sh`

**代码位置**: `/deploy/test-env.sh:1-335`

---

### 5.3 其他辅助脚本

| 脚本 | 功能 |
|------|------|
| `scripts/setup-production.sh` | 初始化生产环境配置 |
| `scripts/backup-all.sh` | 全量备份 |
| `scripts/backup-database.sh` | 数据库备份 |
| `scripts/backup-etcd.sh` | etcd 备份 |
| `scripts/restore-database.sh` | 恢复数据库 |
| `scripts/restore-etcd.sh` | 恢复 etcd |
| `scripts/schedule-backup.sh` | 设置定时备份 |
| `scripts/log-cleanup.sh` | 日志清理 |
| `scripts/acceptance-test.sh` | 验收测试 |
| `deploy/etcd/etcdctl.sh` | etcd 命令行工具 |
| `deploy/nginx/ssl_setup.sh` | SSL 证书配置 |
| `deploy/k3s/install.sh` | k3s 安装 |
| `deploy/cube-studio/install.sh` | Cube-Studio 安装 |

---

## 6. 启动依赖关系图

```
                    ┌─────────────┐
                    │   k3s       │ (可选)
                    └─────────────┘
                           │
                    ┌─────────────┐
                    │ Cube-Studio │ (可选)
                    └─────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐          ┌──────────┐          ┌───────────┐
│ MySQL   │          │   etcd   │          │   Redis   │
└─────────┘          └──────────┘          └───────────┘
    │                      │                      │
    └──────────────────────┼──────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐          ┌──────────┐          ┌───────────┐
│ DataHub │          │ Superset │          │DolphinSch │
└─────────┘          └──────────┘          └───────────┘
    │                      │
    ├──────────────────────┤
    │                      │
    ▼                      ▼
┌─────────┐          ┌──────────┐
│SeaTunnel│          │   Hop    │
└─────────┘          └──────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│               7 个微服务 (8010-8016)                │
│  Portal, NL2SQL, AI Cleaning, Metadata Sync,       │
│  Data API, Sensitive Detect, Audit Log             │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│               监控系统                               │
│  Loki + Promtail + Grafana + Prometheus + Alertmgr │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────┐
│    Nginx    │ (反向代理)
└─────────────┘
```

---

## 7. 快速参考

### 开发环境启动

```bash
# 方式 1: 最小启动 (仅微服务，精简资源)
make test-env-up

# 方式 2: 本地开发 (热重载)
make dev-portal    # 在终端 1
make dev-nl2sql    # 在终端 2
# ...

# 方式 3: Docker 启动微服务
make services-up

# 方式 4: 全量启动
make start-all
```

### 生产环境启动

```bash
# 1. 初始化配置
bash scripts/setup-production.sh

# 2. 部署
bash scripts/production-deploy.sh

# 3. 验证
curl http://localhost:8010/health/all
curl http://localhost:8010/security/check
```

### 常用端口速查

| 端口 | 服务 |
|------|------|
| 3000 | Grafana |
| 3100 | Loki |
| 3306 | MySQL |
| 3309 | ShardingSphere |
| 5801-5802 | SeaTunnel |
| 6379 | Redis |
| 8010 | Portal |
| 8011 | NL2SQL |
| 8012 | AI Cleaning |
| 8013 | Metadata Sync |
| 8014 | Data API |
| 8015 | Sensitive Detect |
| 8016 | Audit Log |
| 8081 | DataHub GMS |
| 8083 | Apache Hop |
| 8088 | Superset |
| 9002 | DataHub Frontend |
| 9090 | Prometheus |
| 9093 | Alertmanager |
| 12345 | DolphinScheduler |
| 30080 | Cube-Studio |

---

## 8. 文件清单

### 启动脚本

| 文件路径 | 功能描述 |
|----------|----------|
| `/deploy.sh` | 一键部署脚本 |
| `/start-all.sh` | 全量启动脚本 |
| `/Makefile` | Make 命令集合 |
| `/deploy/test-env.sh` | 测试环境启动 |
| `/deploy/test-env-stop.sh` | 测试环境停止 |
| `/scripts/production-deploy.sh` | 生产部署脚本 |
| `/scripts/setup-production.sh` | 生产环境初始化 |

### Docker Compose 配置

| 文件路径 | 组件 |
|----------|------|
| `/services/docker-compose.yml` | 7 个微服务 |
| `/deploy/test-env/docker-compose.yml` | 测试环境全栈 |
| `/deploy/superset/docker-compose.yml` | Superset |
| `/deploy/datahub/docker-compose.yml` | DataHub |
| `/deploy/dolphinscheduler/docker-compose.yml` | DolphinScheduler |
| `/deploy/seatunnel/docker-compose.yml` | SeaTunnel |
| `/deploy/hop/docker-compose.yml` | Apache Hop |
| `/deploy/shardingsphere/docker-compose.yml` | ShardingSphere |
| `/deploy/cube-studio/docker-compose.yml` | Cube-Studio |
| `/deploy/etcd/docker-compose.yml` | etcd |
| `/deploy/mysql/docker-compose.yml` | MySQL |
| `/deploy/loki/docker-compose.yml` | Loki + Grafana |
| `/deploy/prometheus/docker-compose.yml` | Prometheus |
| `/deploy/alertmanager/docker-compose.yml` | Alertmanager |
| `/deploy/nginx/docker-compose.yml` | Nginx |

### Python 服务入口

| 文件路径 | 服务 |
|----------|------|
| `/services/portal/main.py` | Portal |
| `/services/nl2sql/main.py` | NL2SQL |
| `/services/ai_cleaning/main.py` | AI Cleaning |
| `/services/metadata_sync/main.py` | Metadata Sync |
| `/services/data_api/main.py` | Data API |
| `/services/sensitive_detect/main.py` | Sensitive Detect |
| `/services/audit_log/main.py` | Audit Log |

---

## 结论

项目启动机制设计合理，提供了多层级的启动选项：

1. **简单场景**: 使用 `make deploy` 一键部署
2. **开发场景**: 使用 `make dev-*` 本地热重载
3. **测试场景**: 使用 `make test-env-up` 精简环境
4. **生产场景**: 使用 `scripts/production-deploy.sh` 安全部署

所有启动脚本都支持健康检查等待、错误处理和状态查看。
