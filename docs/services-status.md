# ONE-DATA-STUDIO-LITE 服务状态详细清单

> 最后更新: 2026-01-31

---

## 目录

- [内部服务](#内部服务)
  - [Portal 服务](#portal-服务)
  - [NL2SQL 服务](#nl2sql-服务)
  - [AI Cleaning 服务](#ai-cleaning-服务)
  - [Metadata Sync 服务](#metadata-sync-服务)
  - [Data API 服务](#data-api-服务)
  - [Sensitive Detect 服务](#sensitive-detect-服务)
  - [Audit Log 服务](#audit-log-服务)
- [共享模块](#共享模块)
- [外部组件](#外部组件)

---

## 内部服务

### Portal 服务

| 属性 | 值 |
|------|-----|
| 端口 | 8010 |
| 状态 | ✅ 完成 100% |
| 入口文件 | `services/portal/main.py` |
| 配置文件 | `services/portal/config.py` |

#### 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 用户认证 | ✅ 完成 | JWT 认证、Token 验证、用户信息 |
| API 代理 | ✅ 完成 | 11 个外部组件代理 |
| 配置中心 | ✅ 完成 | etcd 集成、热更新 |
| 安全检查 | ✅ 完成 | `/security/check` 端点 |
| 统一响应 | ✅ 完成 | ApiResponse 格式 |
| OpenAPI 文档 | ✅ 完成 | `/docs` 端点 |
| 健康检查 | ✅ 完成 | `/health` 端点 |
| 指标采集 | ✅ 完成 | Prometheus 指标 |
| 追踪中间件 | ✅ 完成 | OpenTelemetry |
| 日志聚合 | ✅ 完成 | Loki 集成 |

#### 路由清单

| 路由前缀 | 功能 | 状态 |
|---------|------|------|
| `/api/proxy/seatunnel/v1/*` | SeaTunnel v1 API | ✅ |
| `/api/proxy/shardingsphere/v1/*` | ShardingSphere v1 API | ✅ |
| `/api/proxy/hop/v1/*` | Apache Hop v1 API | ✅ |
| `/api/proxy/datahub/v1/*` | DataHub v1 API | ✅ |
| `/api/proxy/ds/v1/*` | DolphinScheduler v1 API | ✅ |
| `/api/proxy/superset/v1/*` | Superset v1 API | ✅ |
| `/api/proxy/cubestudio/v1/*` | Cube-Studio v1 API | ✅ |
| `/api/cleaning/v1/*` | AI Cleaning v1 API | ✅ |
| `/api/nl2sql/v1/*` | NL2SQL v1 API | ✅ |
| `/api/data-api/v1/*` | Data API v1 API | ✅ |
| `/api/metadata/v1/*` | Metadata Sync v1 API | ✅ |
| `/api/sensitive/v1/*` | Sensitive Detect v1 API | ✅ |
| `/api/audit/v1/*` | Audit Log v1 API | ✅ |
| `/auth/*` | 认证相关 | ✅ |
| `/security/check` | 安全检查 | ✅ |

#### 待办事项

- [ ] 前端页面完善（当前仅 API）
- [ ] WebSocket 支持
- [ ] 限流和熔断

---

### NL2SQL 服务

| 属性 | 值 |
|------|-----|
| 端口 | 8011 |
| 状态 | ✅ 完成 100% |
| 入口文件 | `services/nl2sql/main.py` |

#### 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 自然语言解析 | ✅ 完成 | LLM 调用 |
| SQL 生成 | ✅ 完成 | 结构化输出 |
| 数据库连接 | ✅ 完成 | 支持多种数据库 |
| 缓存机制 | ✅ 完成 | LLM 缓存 |
| 重试机制 | ✅ 完成 | 指数退避 |
| v1 API | ✅ 完成 | 统一响应格式 |

#### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/nl2sql/v1/query` | POST | 自然语言转 SQL |
| `/api/nl2sql/v1/validate` | POST | SQL 验证 |
| `/api/nl2sql/v1/cache/clear` | DELETE | 清除缓存 |

---

### AI Cleaning 服务

| 属性 | 值 |
|------|-----|
| 端口 | 8012 |
| 状态 | ✅ 完成 100% |
| 入口文件 | `services/ai_cleaning/main.py` |

#### 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 数据分析 | ✅ 完成 | 数据质量评估 |
| 规则推荐 | ✅ 完成 | LLM 推荐 |
| 规则模板 | ✅ 完成 | 预定义规则 |
| v1 API | ✅ 完成 | 统一响应格式 |

#### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/cleaning/v1/analyze` | POST | 分析数据 |
| `/api/cleaning/v1/recommend` | POST | 推荐清洗规则 |
| `/api/cleaning/v1/templates` | GET | 获取规则模板 |

---

### Metadata Sync 服务

| 属性 | 值 |
|------|-----|
| 端口 | 8013 |
| 状态 | ✅ 完成 100% |
| 入口文件 | `services/metadata_sync/main.py` |

#### 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 元数据采集 | ✅ 完成 | DataHub 集成 |
| 映射规则管理 | ✅ 完成 | CRUD + 持久化 |
| ETL 任务生成 | ✅ 完成 | SeaTunnel/Hop |
| Webhook 处理 | ✅ 完成 | 签名验证 |
| v1 API | ✅ 完成 | 统一响应格式 |

#### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/metadata/v1/mappings` | GET/POST | 映射规则列表/创建 |
| `/api/metadata/v1/mappings/{id}` | GET/PUT/DELETE | 映射规则详情 |
| `/api/metadata/v1/sync` | POST | 触发同步 |
| `/api/metadata/v1/webhook` | POST | Webhook 接收 |

---

### Data API 服务

| 属性 | 值 |
|------|-----|
| 端口 | 8014 |
| 状态 | ✅ 完成 100% |
| 入口文件 | `services/data_api/main.py` |

#### 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| API 注册 | ✅ 完成 | API 定义管理 |
| 调用统计 | ✅ 完成 | 访问日志 |
| 权限控制 | ✅ 完成 | API Key + JWT |
| 限流 | ✅ 完成 | 令牌桶算法 |
| v1 API | ✅ 完成 | 统一响应格式 |

#### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/data-api/v1/apis` | GET/POST | API 列表/注册 |
| `/api/data-api/v1/apis/{id}` | GET/PUT/DELETE | API 详情 |
| `/api/data-api/v1/call/{name}` | POST | 调用 API |
| `/api/data-api/v1/keys` | GET/POST | API Key 管理 |

---

### Sensitive Detect 服务

| 属性 | 值 |
|------|-----|
| 端口 | 8015 |
| 状态 | ✅ 完成 100% |
| 入口文件 | `services/sensitive_detect/main.py` |

#### 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 敏感数据识别 | ✅ 完成 | LLM + 规则 |
| 检测报告 | ✅ 完成 | 报告生成 + 持久化 |
| 脱敏规则同步 | ✅ 完成 | ShardingSphere |
| v1 API | ✅ 完成 | 统一响应格式 |

#### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/sensitive/v1/detect` | POST | 检测敏感数据 |
| `/api/sensitive/v1/reports` | GET/POST | 检测报告 |
| `/api/sensitive/v1/reports/{id}` | GET | 报告详情 |
| `/api/sensitive/v1/sync` | POST | 同步脱敏规则 |

---

### Audit Log 服务

| 属性 | 值 |
|------|-----|
| 端口 | 8016 |
| 状态 | ✅ 完成 100% |
| 入口文件 | `services/audit_log/main.py` |

#### 功能模块

| 模块 | 状态 | 说明 |
|------|------|------|
| 日志采集 | ✅ 完成 | 中间件拦截 |
| 日志存储 | ✅ 完成 | 持久化存储 |
| 日志查询 | ✅ 完成 | 多条件查询 |
| 日志导出 | ✅ 完成 | CSV 导出 |
| v1 API | ✅ 完成 | 统一响应格式 |

#### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/audit/v1/logs` | GET | 日志查询 |
| `/api/audit/v1/logs/{id}` | GET | 日志详情 |
| `/api/audit/v1/export` | POST | 日志导出 |
| `/api/audit/v1/stats` | GET | 统计信息 |

---

## 共享模块

### common 模块

| 模块 | 文件 | 状态 | 功能 |
|------|------|------|------|
| 配置中心 | `config_center.py` | ✅ 完成 | etcd 客户端 |
| API 响应 | `api_response.py` | ✅ 完成 | 统一响应格式 |
| 安全工具 | `security.py` | ✅ 完成 | 密码/密钥生成 |
| 日志模块 | `logging.py` | ✅ 完成 | 结构化日志 |
| 追踪模块 | `telemetry.py` | ✅ 完成 | OpenTelemetry |
| LLM 客户端 | `llm_client.py` | ✅ 完成 | 统一 LLM 调用 |
| Webhook 安全 | `webhook_security.py` | ✅ 完成 | 签名验证 |
| ShardingSphere 客户端 | `shardingsphere_client.py` | ✅ 完成 | DistSQL |
| ORM 模型 | `orm_models.py` | ✅ 完成 | 基础模型 |
| Repository | `repositories/base.py` | ✅ 完成 | 数据访问层 |
| 中间件 | `middleware.py` | ✅ 完成 | 审计日志 |
| 数据库 | `database.py` | ✅ 完成 | 连接池 |
| 认证 | `auth.py` | ✅ 完成 | JWT |
| HTTP 客户端 | `http.py` | ✅ 完成 | 请求封装 |

---

## 外部组件

| 组件 | 端口 | 状态 | 说明 |
|------|------|------|------|
| Cube-Studio | 30080 | ✅ 完成 | 基座平台，Ollama 集成 |
| DataHub | 8081 | ✅ 完成 | 元数据管理 |
| SeaTunnel | 5802 | ✅ 完成 | 数据同步 |
| DolphinScheduler | 12345 | ✅ 完成 | 任务调度 |
| Superset | 8088 | ✅ 完成 | BI 可视化 |
| ShardingSphere | 3309 | ✅ 完成 | 数据脱敏 |
| Apache Hop | 8083 | ✅ 完成 | ETL 引擎 |
| Ollama/LLM | 31434 | ✅ 完成 | AI 推理 |
| etcd | 2379 | ✅ 完成 | 配置中心 |
| Loki | 3100 | ✅ 完成 | 日志聚合 |
| Grafana | 3000 | ✅ 完成 | 监控面板 |

---

## 服务依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                         Portal (8010)                          │
│                      (统一入口 / API 代理)                      │
└─────────────────────────────────────────────────────────────────┘
           │                │                │
           ▼                ▼                ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  外部组件    │  │  内部服务    │  │   基础设施   │
    │  (11个)     │  │  (6个)      │  │  (etcd/Loki) │
    └─────────────┘  └─────────────┘  └─────────────┘
           │                │                │
           └────────────────┴────────────────┘
                            │
                    ┌───────────────┐
                    │  Common 模块   │
                    │  (共享库)      │
                    └───────────────┘
```

---

## 相关文档

- [项目状态总览](project-status.md)
- [集成状态](integration-status.md)
- [技术债务追踪](technical-debt.md)
