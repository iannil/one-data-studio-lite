# ONE-DATA-STUDIO-LITE 服务依赖关系分析报告

**生成日期**: 2026-02-03
**分析范围**: 启动脚本、Docker Compose 配置、运行时配置

---

## 一、架构总览

项目采用三层架构：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Layer 3: 服务层 (Services)                       │
│    Portal | NL2SQL | AI-Cleaning | Metadata-Sync | Data-API |           │
│    Sensitive-Detect | Audit-Log | Web Frontend                          │
├─────────────────────────────────────────────────────────────────────────┤
│                          Layer 2: 平台层 (Platforms)                      │
│  Cube-Studio | Superset | DataHub | DolphinScheduler | Hop | SeaTunnel  │
│                        ShardingSphere                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                          Layer 1: 基础设施层 (Infrastructure)              │
│   MySQL | PostgreSQL | Redis | etcd | Zookeeper | Kafka | Elasticsearch │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Docker Compose 静态依赖矩阵

### 2.1 基础设施层 (无外部依赖)

| 服务 | 文件 | 端口 | 健康检查 |
|------|------|------|---------|
| mysql | `deploy/mysql/docker-compose.yml` | 3306 | mysqladmin ping |
| cube-mysql | `deploy/cube-studio/docker-compose.yml` | 3308 | mysqladmin ping |
| datahub-mysql | `deploy/datahub/docker-compose.yml` | 3307 | mysqladmin ping |
| postgresql | `deploy/dolphinscheduler/docker-compose.yml` | - | pg_isready |
| redis | 多个文件 | 6379 | redis-cli ping |
| etcd | `deploy/etcd/docker-compose.yml` | 2379 | etcdctl endpoint health |
| zookeeper | `deploy/datahub/docker-compose.yml` | 2181 | echo ruok |
| elasticsearch | `deploy/datahub/docker-compose.yml` | 9200 | curl /_cluster/health |

### 2.2 消息队列依赖链

```
zookeeper (service_healthy)
    │
    └──▶ kafka (service_healthy)
              │
              └──▶ schema-registry (service_started)
```

| 服务 | depends_on | 条件 |
|------|-----------|------|
| kafka | zookeeper | service_healthy |
| schema-registry | kafka | service_healthy |

### 2.3 DataHub 启动依赖链 (最复杂)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Setup 服务 (初始化)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  datahub-mysql-setup                                                    │
│  └── depends_on: datahub-mysql (service_healthy)                        │
│                                                                         │
│  datahub-elasticsearch-setup                                            │
│  └── depends_on: datahub-elasticsearch (service_healthy)                │
│                                                                         │
│  datahub-kafka-setup                                                    │
│  └── depends_on: datahub-kafka (service_healthy)                        │
│  └── depends_on: datahub-schema-registry (service_started)              │
└─────────────────────────────────────────────────────────────────────────┘
                    │ 全部 service_completed_successfully
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  datahub-gms                                                            │
│  └── depends_on: datahub-mysql-setup (completed)                        │
│  └── depends_on: datahub-elasticsearch-setup (completed)                │
│  └── depends_on: datahub-kafka-setup (completed)                        │
└─────────────────────────────────────────────────────────────────────────┘
                    │ service_healthy
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  datahub-frontend, datahub-actions                                      │
│  └── depends_on: datahub-gms (service_healthy)                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Superset 启动依赖链

```
postgres (service_healthy) + redis (service_healthy)
                    │
                    ▼
         ┌─────────────────────────┐
         │     superset-init       │
         │  (db upgrade, 创建admin) │
         └───────────┬─────────────┘
                     │ service_completed_successfully
                     ▼
         ┌─────────────────────────┐
         │  superset               │
         │  superset-worker        │
         └─────────────────────────┘
```

### 2.5 DolphinScheduler 启动依赖链

```
dolphinscheduler-postgres (service_healthy) + dolphinscheduler-zookeeper (service_started)
                    │
                    ▼
         ┌─────────────────────────────┐
         │ dolphinscheduler-schema-init │
         └───────────┬─────────────────┘
                     │ service_completed_successfully
                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  dolphinscheduler-api, dolphinscheduler-master,                          │
│  dolphinscheduler-worker, dolphinscheduler-alert                         │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.6 Cube-Studio 启动依赖链

```
cube-mysql (service_healthy) + cube-redis (service_healthy)
                    │
                    ▼
              ┌─────────────────────┐
              │    cube-myapp       │
              │   (后端服务)        │
              └──────────┬──────────┘
                         │ service_started
                         ▼
              ┌─────────────────────┐
              │   cube-frontend     │
              │    (Nginx前端)      │
              └─────────────────────┘
```

### 2.7 独立服务 (无 depends_on)

| 服务 | 文件 | 说明 |
|------|------|------|
| seatunnel | `deploy/seatunnel/docker-compose.yml` | 独立运行 |
| hop-server | `deploy/hop/docker-compose.yml` | 独立运行 |
| shardingsphere-proxy | `deploy/shardingsphere/docker-compose.yml` | 需要后端 MySQL |
| prometheus | `deploy/prometheus/docker-compose.yml` | 独立运行 |
| alertmanager | `deploy/alertmanager/docker-compose.yml` | 独立运行 |

### 2.8 二开服务 (无显式 depends_on)

所有 7 个微服务通过环境变量配置运行时依赖，无 Docker Compose 级别的 depends_on：

| 服务 | 端口 | 容器名 |
|------|------|--------|
| portal | 8010 | ods-portal |
| nl2sql | 8011 | ods-nl2sql |
| ai-cleaning | 8012 | ods-ai-cleaning |
| metadata-sync | 8013 | ods-metadata-sync |
| data-api | 8014 | ods-data-api |
| sensitive-detect | 8015 | ods-sensitive-detect |
| audit-log | 8016 | ods-audit-log |

---

## 三、运行时依赖矩阵

### 3.1 共享基础设施依赖

所有二开服务通过 `services/common/base_config.py` 共享以下依赖：

| 依赖 | 环境变量 | 默认值 | 用途 |
|------|---------|--------|------|
| MySQL | `DATABASE_URL` | - | 业务数据存储 |
| Redis | `REDIS_URL` | redis://localhost:6379/0 | 缓存、会话、Token黑名单 |
| etcd | `ETCD_ENDPOINTS` | http://localhost:2379 | 配置中心 |
| LLM API | `LLM_BASE_URL` | http://localhost:31434 | AI 能力 (Ollama) |

### 3.2 外部平台依赖

| 依赖 | 环境变量 | 默认端口 | 使用服务 |
|------|---------|---------|---------|
| DataHub GMS | `DATAHUB_GMS_URL` | 8081 | metadata-sync, portal |
| DataHub Frontend | `DATAHUB_URL` | 9002 | portal (代理) |
| Superset | `SUPERSET_URL` | 8088 | portal (代理) |
| DolphinScheduler | `DOLPHINSCHEDULER_API_URL` | 12345 | portal, metadata-sync |
| Hop | `HOP_URL` | 8083 | portal (代理) |
| SeaTunnel | `SEATUNNEL_API_URL` | 5802 | portal, data-api |
| Cube-Studio | `CUBE_STUDIO_URL` | 30080 | portal (代理) |
| ShardingSphere | - | 3309 | data-api (数据脱敏) |

### 3.3 Portal 内部服务代理

Portal 作为统一入口网关，代理所有内部微服务：

```
                              ┌────────────────────────────────────┐
                              │            Portal (:8010)          │
                              │                                    │
                              │  PORTAL_NL2SQL_URL                 │
                              │  PORTAL_AI_CLEANING_URL            │
                              │  PORTAL_METADATA_SYNC_URL          │
                              │  PORTAL_DATA_API_URL               │
                              │  PORTAL_SENSITIVE_DETECT_URL       │
                              │  PORTAL_AUDIT_LOG_URL              │
                              └───────────────┬────────────────────┘
                                              │
        ┌──────────────┬──────────────┬───────┴───────┬──────────────┬──────────────┐
        ▼              ▼              ▼               ▼              ▼              ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│  NL2SQL   │  │AI Cleaning│  │Meta Sync  │  │ Data API  │  │Sensitive  │  │Audit Log  │
│  :8011    │  │  :8012    │  │  :8013    │  │  :8014    │  │  :8015    │  │  :8016    │
└───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘
```

### 3.4 服务间 API 调用关系

| 调用方 | 被调用方 | 用途 |
|--------|---------|------|
| portal | nl2sql | 自然语言查询代理 |
| portal | ai-cleaning | AI 清洗规则推荐 |
| portal | metadata-sync | 元数据同步触发 |
| portal | data-api | 数据资产查询 |
| portal | sensitive-detect | 敏感数据检测 |
| portal | audit-log | 审计日志记录 |
| nl2sql | LLM API | SQL 生成 |
| ai-cleaning | LLM API | 规则推荐 |
| metadata-sync | DataHub GMS | 元数据写入 |
| data-api | ShardingSphere | 脱敏数据访问 |
| sensitive-detect | MySQL | 数据源扫描 |

---

## 四、启动脚本顺序分析

### 4.1 deploy.sh (一键部署)

```bash
deploy_all() {
    1. create_network                     # 创建 ods-network
    2. k3s (可选)                         # 基础设施
    3. Cube-Studio (可选)                 # 基座平台
    4. Superset → wait_for_service :8088  # BI
    5. DataHub → wait_for_service :9002   # 元数据
    6. Hop                                # ETL
    7. SeaTunnel                          # 数据同步
    8. DolphinScheduler → wait :12345     # 调度
    9. ShardingSphere                     # 数据脱敏
    10. 二开服务                          # 微服务
}
```

### 4.2 start-all.sh (多模式启动)

| 模式 | 启动内容 | 等待逻辑 |
|------|---------|---------|
| `all` | platforms + services + web | 完整等待 |
| `platforms` | 第三方平台 | Superset/DataHub/DS |
| `services` | 二开服务 (Docker) | Portal |
| `web` | 前端 npm dev | - |
| `dev` | 二开服务 (uvicorn) | - |

**启动顺序** (all 模式):
```
1. start_platforms:
   ├─ k3s (可选)
   ├─ Cube-Studio (可选)
   ├─ Superset → wait :8088/health (180s)
   ├─ DataHub → wait :9002 (240s)
   ├─ Hop
   ├─ SeaTunnel
   ├─ DolphinScheduler → wait :12345 (180s)
   └─ ShardingSphere

2. start_services:
   └─ docker compose up -d --build → wait :8010/health (60s)

3. start_web:
   └─ npm run dev → :3000
```

### 4.3 deploy/test/start.sh (分阶段测试环境)

```
Phase 1: stage1_infra (基础设施)
├── MySQL → wait 60s
├── Redis → wait 30s
├── Zookeeper → wait 30s
├── Elasticsearch → wait 120s
├── PostgreSQL → wait 30s
└── etcd → wait 30s

Phase 2: stage2_platforms (第三方平台)
├── DataHub GMS → wait 180s
├── DolphinScheduler API → wait 120s
├── Superset → wait 120s
└── Cube-Studio → wait 120s

Phase 3: stage3_services (二开服务)
└── Portal → wait 60s
```

---

## 五、完整依赖图

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    Layer 3: 服务层                                        │
│                                                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │ Portal  │  │ NL2SQL  │  │AI Clean │  │MetaSync │  │Data API │  │Sensitive│          │
│  │ :8010   │  │ :8011   │  │ :8012   │  │ :8013   │  │ :8014   │  │ :8015   │          │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘          │
│       │            │            │            │            │            │                │
│       ├────────────┴────────────┴────────────┴────────────┴────────────┘                │
│       │                                                                                 │
│  ┌────▼────┐                                                                            │
│  │AuditLog │  ← 所有服务通过中间件自动上报                                                 │
│  │ :8016   │                                                                            │
│  └─────────┘                                                                            │
└───────┬─────────────────────────────────────────────────────────────────────────────────┘
        │ 运行时依赖（HTTP API 调用）
        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    Layer 2: 平台层                                        │
│                                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │ Cube-Studio │  │  Superset   │  │   DataHub   │  │DolphinSched │                     │
│  │   :30080    │  │   :8088     │  │ :9002/:8081 │  │   :12345    │                     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                     │
│         │                │                │                │                            │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────────────────┴──────┐                   │
│  │ cube-mysql  │  │superset-db  │  │        基础设施依赖             │                   │
│  │ cube-redis  │  │superset-redis│ │ mysql, es, kafka, zk, postgres │                   │
│  └─────────────┘  └─────────────┘  └────────────────────────────────┘                   │
│                                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                                      │
│  │  SeaTunnel  │  │     Hop     │  │ShardingSphere│                                     │
│  │   :5802     │  │   :8083     │  │    :3309    │                                      │
│  │  (独立运行)  │  │  (独立运行)  │  │ → ods-mysql │                                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                                      │
└───────┬─────────────────────────────────────────────────────────────────────────────────┘
        │ Docker depends_on
        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    Layer 1: 基础设施层                                    │
│                                                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │  MySQL  │  │ Postgre │  │  Redis  │  │  etcd   │  │Zookeeper│  │  Kafka  │          │
│  │ :3306   │  │ :5432   │  │ :6379   │  │ :2379   │  │ :2181   │  │ :9092   │          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └────┬────┘  └────┬────┘          │
│                                                           │            │               │
│  ┌─────────────┐  ┌─────────────┐                        │            │               │
│  │Elasticsearch│  │Schema Regis │◄───────────────────────┴────────────┘               │
│  │   :9200     │  │   :8081     │                                                      │
│  └─────────────┘  └─────────────┘                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 六、Docker 网络

| 网络名称 | 用途 | 使用环境 |
|---------|------|---------|
| `ods-network` | 生产/开发主网络 | deploy.sh, start-all.sh, services/ |
| `ods-test-network` | 测试环境网络 | deploy/test/ |

---

## 七、端口汇总

### 7.1 基础设施端口

| 服务 | 端口 | 说明 |
|------|------|------|
| MySQL (应用) | 3306 | 二开服务数据库 |
| MySQL (DataHub) | 3307 | DataHub 专用 |
| MySQL (Cube) | 3308 | Cube-Studio 专用 |
| PostgreSQL | 5432 | Superset/DolphinScheduler |
| Redis | 6379 | 缓存/会话 |
| etcd | 2379 | 配置中心 |
| Zookeeper | 2181 | 协调服务 |
| Elasticsearch | 9200 | DataHub 搜索 |

### 7.2 平台端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Cube-Studio | 30080 | AI 平台 |
| Superset | 8088 | BI 分析 |
| DataHub Frontend | 9002 | 元数据 UI |
| DataHub GMS | 8081 | 元数据 API |
| DolphinScheduler | 12345 | 调度器 |
| Hop | 8083 | ETL |
| SeaTunnel | 5802 | 数据同步 |
| ShardingSphere | 3309 | 脱敏代理 |

### 7.3 二开服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Portal | 8010 | 统一入口 |
| NL2SQL | 8011 | 自然语言查询 |
| AI Cleaning | 8012 | AI 清洗 |
| Metadata Sync | 8013 | 元数据同步 |
| Data API | 8014 | 数据资产 API |
| Sensitive Detect | 8015 | 敏感检测 |
| Audit Log | 8016 | 审计日志 |

### 7.4 监控端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Prometheus | 9090 | 指标采集 |
| Grafana | 3000 | 监控面板 |
| Loki | 3100 | 日志聚合 |
| Alertmanager | 9093 | 告警管理 |

---

## 八、健康检查等待时间

| 服务 | start_period | 原因 |
|------|-------------|------|
| MySQL | 30s | 初始化数据库文件 |
| Elasticsearch | 60s | 索引初始化 |
| Kafka | 60s | broker 注册 |
| DataHub GMS | 120s | 依赖多个 setup 完成 |
| DataHub Frontend | 60s | 等待 GMS |
| Superset | 40s | 初始化数据库 |
| Portal | 30s | FastAPI 启动 |

---

## 九、推荐启动顺序

### 9.1 完整环境 (生产部署)

```
Phase 1: 基础设施 (并行)
├── MySQL, PostgreSQL, Redis, etcd
├── Zookeeper → Kafka → Schema Registry
└── Elasticsearch

Phase 2: 第三方平台 (各自启动)
├── Cube-Studio (← MySQL + Redis)
├── Superset (← PostgreSQL + Redis)
├── DataHub (← MySQL + ES + Kafka)
├── DolphinScheduler (← PostgreSQL + ZK)
├── SeaTunnel (独立)
├── Hop (独立)
└── ShardingSphere (← MySQL)

Phase 3: 二开服务 (并行)
├── Portal, NL2SQL, AI-Cleaning, Metadata-Sync
├── Data-API, Sensitive-Detect, Audit-Log
└── (全部依赖: MySQL + Redis + etcd)

Phase 4: 前端和监控 (可选)
├── Web Frontend
├── Loki + Promtail + Grafana
└── Prometheus + Alertmanager
```

### 9.2 最小开发环境

```
必须启动:
├── MySQL (:3306)
├── Redis (:6379)
├── etcd (:2379)
└── Portal (:8010)

按需启动:
├── 其他二开服务
├── DataHub (元数据功能)
└── Superset (BI 功能)
```

---

## 十、常见问题排查

### 10.1 启动失败排查

```bash
# 检查服务状态
docker ps --format "table {{.Names}}\t{{.Status}}" | grep ods-

# 检查特定服务日志
docker compose logs -f <service-name>

# 检查健康状态
docker inspect --format='{{.State.Health.Status}}' <container-name>

# 检查网络
docker network inspect ods-network
```

### 10.2 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 网络不存在 | 未创建 | `docker network create ods-network` |
| 端口冲突 | 已占用 | `lsof -i :<port>` |
| DataHub 启动慢 | 依赖多 | 耐心等待 180s+ |
| 内存不足 | 服务太多 | 减少同时启动的服务 |
| 数据库连接失败 | 未就绪 | 确保 MySQL 健康后再启动服务 |
