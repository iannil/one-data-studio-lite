# ONE-DATA-STUDIO-LITE 外部组件对接情况梳理

## 任务说明

根据 `docs/architecture.md` 文档描述，梳理项目中所有需要通过接口通讯的外部组件/产品的对接方案、实际对接情况及存在的问题。

---

## 组件对接总览

| 组件 | 设计端口 | 对接方式 | 实现状态 | 问题级别 |
|------|---------|---------|---------|---------|
| DataHub | 8081 (GMS) | REST API 代理 | ✅ 已实现 | ⚠️ 中 |
| SeaTunnel | 5802 | Hazelcast REST | ✅ 已实现 | ✅ 低 |
| DolphinScheduler | 12345 | REST API 代理 | ✅ 已实现 | ⚠️ 中 |
| Superset | 8088 | REST API + Token缓存 | ✅ 已实现 | ⚠️ 中 |
| ShardingSphere | 3309 | DistSQL API | ✅ 已实现 | ✅ 低 |
| Ollama/LLM | 31434 | REST API 直连 | ✅ 已实现 | ✅ 低 |
| Cube-Studio | 30080 | REST API 代理 | ✅ 已实现 | ✅ 低 |
| Apache Hop | 8083 | REST API | ✅ 已实现 | ✅ 低 |
| etcd | 2379 | 配置中心 | ✅ 新增 | ✅ 低 |
| Loki | 3100 | 日志聚合 | ✅ 新增 | ✅ 低 |
| Grafana | 3000 | 监控面板 | ✅ 新增 | ✅ 低 |
| Promtail | 9090 | 日志采集 | ✅ 新增 | ✅ 低 |

---

## 1. DataHub（元数据管理）

### 设计方案

- **功能定位**: 元数据智能识别、标签管理、版本控制、数据血缘
- **交互方式**: REST API（GMS GraphQL/REST）
- **端口**: 8081 (GMS API), 9002 (前端UI)

### 实际对接情况

**前端 API** (`web/src/api/datahub.ts`):

```typescript
searchEntities()     → /api/proxy/datahub/entities?action=search
getEntityAspect()    → /api/proxy/datahub/aspects/v1
getLineage()         → /api/proxy/datahub/relationships
searchTags()         → /api/proxy/datahub/entities?action=search (type=tag)
createTag()          → /api/proxy/datahub/entities?action=ingest
```

**后端代理** (`services/portal/routers/datahub.py`):

- 纯代理模式，转发请求到 `DATAHUB_GMS_URL`
- 注入特殊头: `X-RestLi-Protocol-Version: 2.0.0`
- 支持 Bearer Token 认证

**部署配置** (`deploy/datahub/docker-compose.yml`):

- MySQL Ingestion Recipe 支持自动采集业务库元数据
- 支持多库模式采集 (`one_data_.*`, `business_.*`)

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| Token 未配置 | ⚠️ 中 | `DATAHUB_TOKEN` 环境变量未设置时代理无法正常工作 |
| 无错误重试 | ⚠️ 低 | 请求失败时没有重试机制 |
| ~~Webhook 未集成~~ | ✅ 已解决 | 已实现 Webhook 签名验证 (2026-01-30) |

---

## 2. SeaTunnel（数据同步）

### 设计方案

- **功能定位**: 高性能数据同步、批流一体、CDC实时同步
- **交互方式**: REST API
- **端口**: 5802

### 实际对接情况

**前端 API** (`web/src/api/seatunnel.ts`):

```typescript
// v1 版本（推荐）
getJobsV1()           → /api/proxy/seatunnel/v1/jobs
getJobDetailV1(id)    → /api/proxy/seatunnel/v1/jobs/{id}
submitJobV1(config)   → /api/proxy/seatunnel/v1/jobs (POST)
cancelJobV1(id)       → /api/proxy/seatunnel/v1/jobs/{id} (DELETE)
getJobStatusV1(id)    → /api/proxy/seatunnel/v1/jobs/{id}/status
getClusterStatusV1()  → /api/proxy/seatunnel/v1/cluster

// 旧版 API（向后兼容）
getJobs()             → /api/proxy/seatunnel/api/v1/job/list
getJobDetail(id)      → /api/proxy/seatunnel/api/v1/job/{id}
submitJob(config)     → /api/proxy/seatunnel/api/v1/job/submit (POST)
cancelJob(id)         → /api/proxy/seatunnel/api/v1/job/{id} (DELETE)
getJobStatus(id)      → /api/proxy/seatunnel/api/v1/job/{id}/status
```

**后端代理** (`services/portal/routers/seatunnel.py`):

- **注意**: 实际使用 Hazelcast REST Maps API（非标准 Zeta REST API）
- 实际端点:
  - `/hazelcast/rest/maps/running-jobs`
  - `/hazelcast/rest/maps/finished-jobs`
  - `/hazelcast/rest/maps/job-info/{job_id}`
  - `/hazelcast/rest/maps/submit-job`
  - `/hazelcast/rest/maps/cancel-job/{job_id}`
- 有业务逻辑：合并运行中和已完成任务列表
- **2026-01-30 更新**: 添加 v1 版本 API，使用统一 `ApiResponse` 格式

**部署配置** (`deploy/seatunnel/docker-compose.yml`):

- 与 DolphinScheduler 工作组 `seatunnel` 集成
- 检查点存储配置完整

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| ~~API 版本不一致~~ | ✅ 已解决 | 已添加 v1 版本 API，统一响应格式 (2026-01-30) |
| 无认证机制 | ⚠️ 低 | SeaTunnel API 无需认证，但 Portal 代理层已添加认证检查 |

---

## 3. DolphinScheduler（任务调度）

### 设计方案

- **功能定位**: 统一调度 ETL 任务
- **交互方式**: REST API
- **端口**: 12345

### 实际对接情况

**前端 API** (`web/src/api/dolphinscheduler.ts`):

```typescript
getProjects()                    → /api/proxy/ds/projects
getProcessDefinitions(code)      → /api/proxy/ds/projects/{code}/process-definition
getSchedules(code)               → /api/proxy/ds/projects/{code}/schedules
updateScheduleState(...)         → /api/proxy/ds/projects/{code}/schedules/{id}/online
getTaskInstances(code)           → /api/proxy/ds/projects/{code}/task-instances
getTaskLog(code, taskId)         → /api/proxy/ds/projects/{code}/task-instances/{id}/log
```

**后端代理** (`services/portal/routers/dolphinscheduler.py`):

- 纯代理模式，转发到 `http://localhost:12345/dolphinscheduler`
- 使用 `DOLPHINSCHEDULER_TOKEN` 作为 `token` 请求头

**部署配置** (`deploy/dolphinscheduler/docker-compose.yml`):

- 3个工作组: `default`, `seatunnel`, `hop`
- 固定 Token 认证
- PostgreSQL 持久化存储

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| Token 硬编码 | ⚠️ 中 | 部署配置中 Token 为硬编码值 `ds_token_2024` |
| Token 未配置 | ⚠️ 中 | `.env.example` 中未设置默认值 |
| 路径前缀 | ⚠️ 低 | 代理需处理 `/dolphinscheduler` 前缀 |

---

## 4. Superset（BI 可视化）

### 设计方案

- **功能定位**: BI 可视化、数据探索
- **交互方式**: REST API
- **端口**: 8088

### 实际对接情况

**前端 API** (`web/src/api/superset.ts`):

```typescript
getDashboards()     → /api/proxy/superset/api/v1/dashboard/
getDashboard(id)    → /api/proxy/superset/api/v1/dashboard/{id}
getCharts()         → /api/proxy/superset/api/v1/chart/
getChart(id)        → /api/proxy/superset/api/v1/chart/{id}
getDatasets()       → /api/proxy/superset/api/v1/dataset/
```

**后端代理** (`services/portal/routers/superset.py`):

- **有业务逻辑**: 自动获取和缓存 admin Token
- 认证流程:
  1. 调用 `/api/v1/security/login` 获取 Token
  2. 缓存 Token 1 小时
  3. 代理请求时注入 `Authorization: Bearer {token}`
- 全局变量存储: `_superset_token`, `_superset_token_expire`

**部署配置** (`deploy/superset/`):

- PostgreSQL + Redis 高可用
- Celery Worker 支持异步任务

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| ~~Token 全局单例~~ | ✅ 已解决 | 已实现线程安全的 Token 管理器 (2026-01-30) |
| 默认凭据 | 🔴 高 | admin/admin 硬编码，生产环境必须修改 |
| 无刷新机制 | ⚠️ 低 | Token 过期后才重新获取，无主动刷新 |

---

## 5. ShardingSphere（数据脱敏）

### 设计方案

- **功能定位**: 透明数据脱敏、SQL 层拦截
- **交互方式**: DistSQL API
- **端口**: 3309（代理端口）

### 实际对接情况

**前端 API** (`web/src/api/shardingsphere.ts`):

```typescript
getMaskRules()      → /api/proxy/shardingsphere/mask-rules
updateMaskRules()   → /api/proxy/shardingsphere/mask-rules (PUT)
```

**后端实现** (`services/portal/routers/shardingsphere.py`):

- **2026-01-30 更新**: 已实现 DistSQL 动态配置
- 通过 JDBC 连接执行 DistSQL 命令
- 支持:
  - `ALTER MASK RULE` - 添加/修改脱敏规则
  - `DROP MASK RULE` - 删除脱敏规则
  - `SHOW MASK RULES` - 查询脱敏规则

**部署配置** (`deploy/shardingsphere/docker-compose.yml`):

- 在查询层透明脱敏（6种敏感数据类型）
- 连接 Cube-Studio MySQL (3308)
- Standalone + JDBC 持久化模式

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| ~~非 API 对接~~ | ✅ 已解决 | 已实现 DistSQL 动态配置 (2026-01-30) |
| ~~配置不同步~~ | ✅ 已解决 | DistSQL 配置即时生效 (2026-01-30) |
| ~~与敏感检测未联动~~ | ✅ 已解决 | 敏感检测 → ShardingSphere 配置同步已实现 (2026-01-30) |

---

## 6. Ollama/LLM（AI 推理）

### 设计方案

- **功能定位**: NL2SQL、AI 清洗规则推荐、敏感数据分类
- **交互方式**: REST API
- **端口**: 31434（Cube-Studio 部署的 Ollama）

### 实际对接情况

**调用服务**:

1. NLtd NL2SQL 服务 (`services/nl2sql/main.py`)
2. AI 清洗服务 (`services/ai_cleaning/main.py`)
3. 敏感数据检测服务 (`services/sensitive_detect/main.py`)

**API 调用格式**（统一）:

```python
url = f"{settings.LLM_BASE_URL}/api/generate"
payload = {
    "model": "qwen2.5:7b",
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_predict": 2048
    }
}
```

**配置**:

- 基础 URL: `http://localhost:31434`
- 默认模型: `qwen2.5:7b`
- 温度参数: 0.1（低温，保证一致性）

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| ~~无缓存机制~~ | ✅ 已解决 | 已实现 LLM 缓存 (2026-01-30) |
| ~~无重试机制~~ | ✅ 已解决 | 已实现指数退避重试 (2026-01-30) |
| ~~JSON 解析不严格~~ | ✅ 已解决 | 已改进错误处理和日志记录 (2026-01-30) |

---

## 7. Cube-Studio（基座平台）

### 设计方案

- **功能定位**: 数据管理、在线开发、任务编排、模型推理、监控告警
- **交互方式**: REST API
- **端口**: 30080

### 实际对接情况

**前端 API** (`web/src/api/cubestudio.ts`):

```typescript
getPipelines()      → /api/proxy/cubestudio/pipeline_modelview/api/
getPipeline(id)     → /api/proxy/cubestudio/pipeline_modelview/api/{id}
runPipeline(id)     → /api/proxy/cubestudio/pipeline_modelview/api/{id}/run (POST)
```

**后端代理** (`services/portal/routers/proxy.py`):

- 使用通用代理函数转发请求
- 无特殊认证处理

**部署配置** (`deploy/cube-studio/`):

- Helm values.yaml 完整的 K8s 部署配置
- Ollama LLM 集成 (NodePort 31434)
- Prometheus + Grafana 监控

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| 功能覆盖有限 | ⚠️ 低 | 仅实现了 Pipeline 相关 API，其他功能未对接 |

---

## 8. Apache Hop（ETL 引擎）

### 设计方案

- **功能定位**: 复杂业务逻辑 ETL 转换
- **交互方式**: REST API
- **端口**: 8083

### 实际对接情况

**前端 API** (`web/src/api/hop.ts`):

```typescript
getPipelines()           → /api/proxy/hop/pipelines
getPipeline(id)          → /api/proxy/hop/pipelines/{id}
executePipeline(id)      → /api/proxy/hop/pipelines/{id}/execute (POST)
getExecutionStatus(id)   → /api/proxy/hop/executions/{id}
```

**后端代理** (`services/portal/routers/hop.py`):

- **2026-01-30 更新**: 已实现 Hop REST API 对接
- 支持的端点:
  - `/hop/pipelines` - 获取管道列表
  - `/hop/pipelines/{name}` - 获取管道详情
  - `/hop/pipelines/{name}/execute` - 执行管道
  - `/hop/executions/{id}` - 获取执行状态

**部署配置**:

- 通过 DolphinScheduler 工作组 `hop` 调度

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| ~~完全未实现~~ | ✅ 已解决 | 已实现 Hop REST API 对接 (2026-01-30) |

---

## 9. etcd（配置中心）

### 设计方案

- **功能定位**: 统一配置管理、配置热更新、敏感配置加密
- **交互方式**: REST API (v3)
- **端口**: 2379

### 实际对接情况

**部署配置** (`deploy/etcd/docker-compose.yml`):

- **2026-01-30 新增**: etcd 配置中心部署
- 特性:
  - 数据持久化（Docker volume）
  - 自动快照（每 10000 次写操作）
  - 自动压缩（保留 24 小时历史）
  - 健康检查
  - 8GB 后端配额

**客户端实现** (`services/common/config_center.py`):

- **2026-01-30 新增**: `EtcdConfigCenter` 类
- 功能:
  - 配置集中存储（KV）
  - 配置读取（带缓存）
  - Watch 机制（热更新）
  - 配置版本记录（etcd 内置）
  - 敏感配置加密（AES-256-GCM）
  - 环境变量兜底（降级策略）

**管理工具** (`deploy/etcd/etcdctl.sh`):

- **2026-01-30 新增**: etcdctl 快捷操作脚本
- 命令:
  - `get` - 获取配置值
  - `put` - 设置配置值
  - `del` - 删除配置值
  - `list` - 列出所有键（支持前缀过滤）
  - `watch` - 监控配置变更
  - `history` - 查看配置历史版本
  - `backup` - 备份 etcd 数据
  - `restore` - 恢复 etcd 数据
  - `init` - 初始化 ONE-DATA-STUDIO-LITE 配置

**配置结构**:

```
/one-data-studio/
├── /portal/
│   ├── /database/url
│   ├── /database/pool_size
│   └── /jwt/secret
├── /seatunnel/
│   └── /api/token
├── /superset/
│   ├── /auth/username
│   └── /auth/password
└── /global/
    ├── /log/level
    └── /llm/base_url
```

**Portal 集成** (`services/portal/config.py`):

- **2026-01-30 更新**: 添加配置中心支持
- 优先级: etcd > 环境变量 > 默认值
- 配置热更新回调支持
- 运行时配置读写函数

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| 无 | ✅ 低 | 实现完整 |

---

## 10. 内部微服务对接

### 服务列表

| 服务 | 端口 | 实现状态 |
|-----|------|---------|
| NL2SQL | 8011 | ✅ 完整实现 |
| AI Cleaning | 8012 | ✅ 完整实现 |
| Metadata Sync | 8013 | ✅ 完整实现 |
| Data API | 8014 | ✅ 完整实现 |
| Sensitive Detect | 8015 | ✅ 完整实现 |
| Audit Log | 8016 | ✅ 完整实现 |

### 共同问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| ~~内存存储~~ | ✅ 已解决 | 已实现数据库持久化 (2026-01-30) |
| ~~无持久化~~ | ✅ 已解决 | 已实现 Repository 层 (2026-01-30) |
| ~~Webhook 无签名~~ | ✅ 已解决 | 已实现 HMAC-SHA256 签名验证 (2026-01-30) |

---

## 问题汇总

### 🔴 高优先级问题

1. **~~ShardingSphere 非 API 对接~~** ✅ 已解决 (2026-01-30)
   - ~~当前实现只是读写本地配置文件~~
   - ~~修改后需要重启服务才能生效~~
   - ~~与敏感检测服务未联动~~
   - 已实现 DistSQL 动态配置

2. **~~Apache Hop 完全未实现~~** ✅ 已解决 (2026-01-30)
   - ~~仅有 URL 配置，无任何 API 调用代码~~
   - ~~架构设计中的功能未落地~~
   - 已实现 Hop REST API 对接

3. **~~内部服务无持久化~~** ✅ 已解决 (2026-01-30)
   - ~~元数据同步映射规则存内存~~
   - ~~敏感检测规则和报告存内存~~
   - ~~审计日志存内存（超 10000 条清理）~~
   - 已实现 ORM + Repository 层

4. **安全配置问题** ✅ 已部分解决 (2026-01-30)
   - 生产环境强制检查 JWT_SECRET
   - 硬编码用户凭据已移至环境变量
   - 添加启动时安全配置验证
   - ⚠️ Superset 默认凭据仍需手动修改

### ⚠️ 中优先级问题

1. **认证 Token 管理** ✅ 已部分解决 (2026-01-30)
   - ~~Superset Token 全局单例~~
   - 已实现线程安全的 Token 管理器
   - 各组件 Token 配置说明已完善

2. **~~API 版本不一致~~** ✅ 已解决 (2026-01-30)
   - ~~SeaTunnel 前端调用与后端实际 API 不一致~~
   - 已添加 v1 版本 API，统一响应格式

3. **架构设计未完全实现** ✅ 已部分解决 (2026-01-30)
   - ~~DataHub → SeaTunnel Webhook 未实现~~
   - 已实现 Webhook 签名验证
   - 敏感检测 → ShardingSphere 配置同步已实现

### ✅ 低优先级问题

1. **LLM 调用优化** ✅ 已解决 (2026-01-30)
   - ~~无缓存、无重试机制~~
   - 已实现统一 LLM 客户端，支持缓存和重试

2. **错误处理** ✅ 已部分解决 (2026-01-30)
   - ~~部分代理无重试机制~~
   - LLM 调用已添加重试机制
   - SeaTunnel 代理已添加详细错误处理

---

## 建议改进方案

### 短期（必要修复）

1. **~~ShardingSphere 真正 API 对接~~** ✅ 已完成 (2026-01-30)
   - ~~实现 DistSQL 动态配置更新~~
   - ~~或使用 ShardingSphere 管理 API~~
   - 已实现 DistSQL 动态配置

2. **~~数据持久化~~** ✅ 已完成 (2026-01-30)
   - ~~为内部服务添加数据库持久化~~
   - ~~使用 SQLAlchemy 模型~~
   - 已实现 ORM + Repository 层

3. **安全加固** ⚠️ 部分完成
   - ✅ 生成随机 JWT_SECRET
   - ✅ 配置各组件认证 Token
   - ⚠️ Superset 默认凭据需手动修改

### 中期（功能完善）

1. **~~Apache Hop API 对接~~** ✅ 已完成 (2026-01-30)
   - ~~实现 Pipeline 管理 API~~
   - ~~或完全通过 DolphinScheduler 调度~~
   - 已实现 Hop REST API 对接

2. **~~Webhook 集成~~** ✅ 已完成 (2026-01-30)
   - ~~实现 DataHub 元数据变更 Webhook~~
   - ~~添加签名验证~~
   - 已实现 Webhook 签名验证

3. **配置中心** ✅ 已完成 (2026-01-30)
   - ~~使用配置中心统一管理各组件配置~~
   - 已实现 etcd 配置中心

### 长期（架构优化）

1. **统一认证**
   - 各组件统一使用 OAuth2/OIDC

2. **~~配置中心~~** ✅ 已完成 (2026-01-30)
   - ~~使用配置中心统一管理各组件配置~~
   - 已实现 etcd 配置中心

---

## 11. Loki + Grafana（日志聚合与监控）

### 设计方案

- **功能定位**: 日志聚合、查询分析、可视化监控、告警通知
- **交互方式**: Loki API、Grafana UI
- **端口**: 3100 (Loki), 3000 (Grafana), 9090 (Promtail)

### 实际对接情况

**部署配置** (`deploy/loki/docker-compose.yml`):

- **2026-01-30 新增**: Loki 日志聚合部署
- 服务:
  - **Loki**: 日志存储和查询引擎
  - **Promtail**: 日志采集代理
  - **Grafana**: 监控面板和可视化
- 特性:
  - 数据持久化（Docker volume）
  - 自动仪表板配置
  - 健康检查
  - 外部网络连接（one-data-studio-network）

**Loki 配置** (`deploy/loki/config/loki-config.yaml`):

- **2026-01-30 新增**: Loki 主配置
- 功能:
  - 无认证模式（内部网络）
  - 日志保留策略:
    - ERROR 日志：永久保留
    - Portal 日志：永久保留
    - AI 服务日志：单独索引
    - DEBUG 日志：删除（生产环境）
  - 存储引擎: TSDB
  - 索引周期: 24小时
  - 自动压缩: 24小时周期

**Promtail 配置** (`deploy/loki/config/promtail/config.yaml`):

- **2026-01-30 新增**: Promtail 日志采集配置
- 采集源:
  - Docker 容器日志（自动发现）
  - Portal 服务日志 (`/var/log/portal/*.log`)
  - NL2SQL 服务日志 (`/var/log/nl2sql/*.log`)
  - AI Cleaning 服务日志 (`/var/log/ai_cleaning/*.log`)
  - 系统日志 (`/var/log/syslog`, `/var/log/auth.log`)
- 标签提取:
  - `service`: 服务名（portal, nl2sql, ai_cleaning 等）
  - `subsystem`: 子系统（superset, datahub, dolphinscheduler 等）
  - `internal_service`: 内部服务（nl2sql, ai_cleaning, metadata_sync 等）
  - `level`: 日志级别
  - `instance`: 实例标识

**Grafana 配置** (`deploy/loki/config/grafana/provisioning/`):

- **2026-01-30 新增**: Grafana 自动配置
- 数据源:
  - Loki: `http://loki:3100`
  - Prometheus: `http://prometheus:9090`（预留）
- 仪表板:
  - **Service Health**: 服务健康状态监控
  - **API Performance**: API 性能监控
  - **Log Analysis**: 日志分析面板

**统一日志模块** (`services/common/logging.py`):

- **2026-01-30 新增**: 统一日志配置
- 功能:
  - JSON 格式化器（生产环境）
  - 纯文本格式化器（开发环境，支持颜色）
  - 结构化日志上下文
  - 日志上下文管理器 (`log_context`)
  - 计时上下文管理器 (`log_duration`)
  - 日志辅助类 (`LogHelper`)

**OpenTelemetry 追踪** (`services/common/telemetry.py`):

- **2026-01-30 新增**: 分布式追踪支持
- 功能:
  - OpenTelemetry SDK 集成
  - Jaeger 追踪后端（预留）
  - 追踪中间件 (`TracingMiddleware`)
  - 装饰器支持 (`@traced`, `@timed`)
  - 追踪上下文 (`TraceContext`)
  - 指标采集 (Metrics)

**告警规则** (`deploy/loki/config/alert-rules.yml`):

- **2026-01-30 新增**: Loki 告警规则
- 规则分类:
  - 服务健康告警（无日志输出 = 服务宕机）
  - 错误率告警（>5% 警告，>15% 严重）
  - 异常检测告警（异常突增、超时、连接失败）
  - 业务指标告警（LLM 失败、连接池耗尽、API 延迟）
  - 资源使用告警（内存、磁盘）
  - 安全告警（认证失败、SQL 注入）

**Makefile 命令**:

```bash
make monitoring-up      # 启动完整监控系统
make monitoring-down    # 停止监控系统
make monitoring-logs    # 查看监控系统日志
make monitoring-status  # 查看监控系统状态
make loki-up            # 仅启动 Loki
make grafana-up         # 仅启动 Grafana
make grafana-logs       # 查看 Grafana 日志
```

### 存在问题

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| 无 | ✅ 低 | 实现完整 |

---

## 更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-01-30 | 完成 API 一致性修复，添加统一 ApiResponse 格式 |
| 2026-01-30 | 新增 etcd 配置中心实现 |
| 2026-01-30 | ShardingSphere 实现 DistSQL 动态配置 |
| 2026-01-30 | Apache Hop 实现 REST API 对接 |
| 2026-01-30 | 内部服务实现数据库持久化 |
| 2026-01-30 | LLM 调用添加缓存和重试机制 |
| 2026-01-30 | 实现 Webhook 签名验证 |
| 2026-01-30 | 实现线程安全的 Token 管理器 |
| 2026-01-30 | ShardingSphere、Hop、SeaTunnel 添加 v1 版本 API |
| 2026-01-30 | 创建配置中心使用指南 (docs/standards/config-center.md) |
| 2026-01-30 | 创建 API 设计规范文档 (docs/standards/api-design.md) |
| 2026-01-30 | 前端 API 客户端标准化完成，所有模块添加 v1 API |
| 2026-01-30 | 后端路由添加 v1 API：DataHub、DolphinScheduler、Superset |
| 2026-01-30 | 后端内部服务路由添加 v1 API：Cleaning、NL2SQL、Data-API、Metadata-Sync、Sensitive、Audit |
| 2026-01-30 | 新增 Cube-Studio 专用路由 |
| 2026-01-30 | 安全配置验证增强：密码强度检查、弱密钥检测、Token 验证 |
| 2026-01-30 | 新增安全工具模块：密码生成、Token 生成、敏感信息掩码 |
| 2026-01-30 | 新增生产环境密钥生成脚本 |
| 2026-01-30 | 添加 /security/check 安全配置检查端点 |
| 2026-01-30 | Cube-Studio 深度集成：模型推理、数据管理、Notebook、监控告警 API |
| 2026-01-30 | 统一认证框架设计：OAuth2/OIDC 架构设计文档 |
| 2026-01-30 | 新增 Token 验证端点：/auth/validate、/auth/userinfo、/auth/revoke |
| 2026-01-30 | 新增 Loki 日志聚合部署配置 |
| 2026-01-30 | 新增 Promtail 日志采集配置 |
| 2026-01-30 | 新增 Grafana 监控面板配置 |
| 2026-01-30 | 新增 Grafana 仪表板：Service Health、API Performance、Log Analysis |
| 2026-01-30 | 新增 Loki 告警规则配置 |
| 2026-01-30 | 新增统一日志模块 (services/common/logging.py) |
| 2026-01-30 | 新增 OpenTelemetry 分布式追踪模块 (services/common/telemetry.py) |
| 2026-01-30 | Makefile 新增监控相关命令 |

