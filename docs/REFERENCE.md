# 配置参考手册 (REFERENCE)

**更新日期**: 2026-02-04
**版本**: 1.1
**来源**: .env.example, Makefile, package.json

本文档提供 ONE-DATA-STUDIO-LITE 项目的完整配置参考，包括所有环境变量、脚本命令和模块依赖关系。

---

## 目录

1. [环境变量参考](#环境变量参考)
2. [脚本参考表](#脚本参考表)
3. [模块依赖关系](#模块依赖关系)
4. [服务端口映射](#服务端口映射)
5. [默认凭据](#默认凭据)

---

## 环境变量参考

### 安全配置 (生产环境必须修改)

| 变量名 | 说明 | 默认值 | 生成方式 |
|-------|------|--------|----------|
| `JWT_SECRET` | JWT 签名密钥 | `your-strong-random-secret-key-here` | `openssl rand -hex 32` |
| `JWT_EXPIRE_HOURS` | Token 有效期(小时) | `24` | - |
| `JWT_REFRESH_THRESHOLD_MINUTES` | Token 刷新阈值(分钟) | `30` | - |
| `ENVIRONMENT` | 环境标识 | `development` | `production` |
| `INTERNAL_TOKEN` | 服务间认证 Token | - | `openssl rand -hex 32` |

### 配置中心 (etcd)

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `ETCD_ENDPOINTS` | etcd 服务地址 | `http://localhost:2379` |
| `ENABLE_CONFIG_CENTER` | 启用配置中心 | `true` |
| `CONFIG_CACHE_TTL` | 配置缓存过期时间(秒) | `60` |
| `CONFIG_ENCRYPTION_KEY` | 配置加密密钥(Fernet) | - |

### 外部平台认证

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `PORTAL_DATAHUB_TOKEN` | DataHub Personal Access Token | - |
| `META_SYNC_DATAHUB_WEBHOOK_SECRET` | DataHub Webhook 签名密钥 | - |
| `PORTAL_DOLPHINSCHEDULER_TOKEN` | DolphinScheduler Token | - |
| `PORTAL_SUPERSET_ADMIN_USER` | Superset 管理员用户 | `admin` |
| `PORTAL_SUPERSET_ADMIN_PASSWORD` | Superset 管理员密码 | `your-superset-password` |

### LLM 配置

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `LLM_BASE_URL` | LLM 服务地址 (Ollama API) | `http://localhost:31434` |
| `LLM_MODEL` | LLM 模型名称 | `qwen2.5:7b` |

### 服务地址配置

#### 基座平台

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `PORTAL_CUBE_STUDIO_URL` | Cube-Studio 地址 | `http://localhost:30080` |

#### 子系统地址

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `PORTAL_SUPERSET_URL` | Superset 地址 | `http://localhost:8088` |
| `PORTAL_DATAHUB_URL` | DataHub Web UI | `http://localhost:9002` |
| `PORTAL_DATAHUB_GMS_URL` | DataHub GMS API | `http://localhost:8081` |
| `PORTAL_DOLPHINSCHEDULER_URL` | DolphinScheduler 地址 | `http://localhost:12345` |
| `PORTAL_HOP_URL` | Apache Hop 地址 | `http://localhost:8083` |
| `PORTAL_SEATUNNEL_URL` | SeaTunnel 地址 | `http://localhost:5802` |
| `SEA_TUNNEL_API_KEY` | SeaTunnel API Key | - |

#### 二开服务地址

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `PORTAL_NL2SQL_URL` | NL2SQL 服务 | `http://localhost:8011` |
| `PORTAL_AI_CLEANING_URL` | AI 清洗服务 | `http://localhost:8012` |
| `PORTAL_METADATA_SYNC_URL` | 元数据同步服务 | `http://localhost:8013` |
| `PORTAL_DATA_API_URL` | 数据 API 网关 | `http://localhost:8014` |
| `PORTAL_SENSITIVE_DETECT_URL` | 敏感检测服务 | `http://localhost:8015` |
| `PORTAL_AUDIT_LOG_URL` | 审计日志服务 | `http://localhost:8016` |

### 服务端口

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `PORTAL_APP_PORT` | Portal 服务端口 | `8010` |
| `PORTAL_DEBUG` | Debug 模式 | `false` |

### Superset 部署配置

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `SUPERSET_ADMIN_EMAIL` | Superset 管理员邮箱 | `admin@onedata.local` |
| `SUPERSET_DB_PASSWORD` | Superset 数据库密码 | `superset_change_in_production` |
| `SUPERSET_SECRET_KEY` | Superset 密钥 | `one-data-studio-superset-secret-key-change-in-production` |
| `SUPERSET_LOG_LEVEL` | Superset 日志级别 | `INFO` |
| `SUPERSET_PORT` | Superset 端口 | `8088` |

### 其他配置

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `PORTAL_SHARDINGSPHERE_CONFIG_PATH` | ShardingSphere 配置路径 | `deploy/shardingsphere/config/config-mask.yaml` |
| `DATABASE_URL` | 数据库连接字符串 | - |

### 邮件服务配置 (SMTP)

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `SMTP_ENABLED` | 启用邮件服务 | `false` |
| `SMTP_HOST` | SMTP 服务器 | `smtp.example.com` |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USERNAME` | SMTP 用户名 | - |
| `SMTP_PASSWORD` | SMTP 密码 | - |
| `SMTP_FROM_EMAIL` | 发件人邮箱 | `noreply@one-data-studio.local` |
| `SMTP_FROM_NAME` | 发件人名称 | `ONE-DATA-STUDIO-LITE` |
| `SMTP_USE_TLS` | 使用 TLS | `true` |
| `SMTP_TIMEOUT` | 连接超时(秒) | `30` |

---

## 脚本参考表

### 统一运维脚本 (ods.sh)

#### 启动命令

| 命令 | 说明 |
|------|------|
| `./ods.sh start all` | 启动所有服务 |
| `./ods.sh start infra` | 启动基础设施 (MySQL, Redis, MinIO) |
| `./ods.sh start platforms` | 启动第三方平台 |
| `./ods.sh start services` | 启动后端微服务 |
| `./ods.sh start web` | 启动前端开发服务器 |

#### 停止命令

| 命令 | 说明 |
|------|------|
| `./ods.sh stop all` | 停止所有服务 |
| `./ods.sh stop infra` | 停止基础设施 |
| `./ods.sh stop platforms` | 停止第三方平台 |
| `./ods.sh stop services` | 停止后端微服务 |
| `./ods.sh stop web` | 停止前端 |

#### 状态检查

| 命令 | 说明 |
|------|------|
| `./ods.sh status all` | 查看所有服务状态 |
| `./ods.sh health all` | 健康检查 |
| `./ods.sh health infra` | 基础设施健康检查 |
| `./ods.sh health platforms` | 平台服务健康检查 |
| `./ods.sh health services` | 微服务健康检查 |
| `./ods.sh info` | 显示访问地址 |

#### 数据操作

| 命令 | 说明 |
|------|------|
| `./ods.sh init-data seed` | 初始化种子数据 |
| `./ods.sh init-data verify` | 验证数据完整性 |
| `./ods.sh init-data status` | 显示数据状态 |

#### 测试命令

| 命令 | 说明 |
|------|------|
| `./ods.sh test all` | 运行所有测试 |
| `./ods.sh test lifecycle` | 按生命周期顺序测试 |
| `./ods.sh test foundation` | 测试系统基础功能 |
| `./ods.sh test planning` | 测试数据规划功能 |
| `./ods.sh test collection` | 测试数据汇聚功能 |
| `./ods.sh test processing` | 测试数据加工功能 |
| `./ods.sh test analysis` | 测试数据分析功能 |
| `./ods.sh test security` | 测试数据安全功能 |

### Makefile 命令

#### 基础命令

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make start` | 启动所有服务 |
| `make stop` | 停止所有服务 |
| `make status` | 查看服务状态 |
| `make info` | 显示访问地址 |
| `make health` | 健康检查 |
| `make network` | 创建 Docker 网络 |

#### 二开服务

| 命令 | 说明 |
|------|------|
| `make services-up` | 启动二开服务 |
| `make services-down` | 停止二开服务 |
| `make services-logs` | 查看二开服务日志 |

#### 单组件部署

| 命令 | 说明 |
|------|------|
| `make superset-up/down` | 启动/停止 Superset |
| `make openmetadata-up/down` | 启动/停止 OpenMetadata |
| `make dolphinscheduler-up/down` | 启动/停止 DolphinScheduler |
| `make seatunnel-up` | 启动 SeaTunnel |
| `make hop-up` | 启动 Apache Hop |
| `make shardingsphere-up` | 启动 ShardingSphere |
| `make cube-studio-up/down` | 启动/停止 Cube-Studio |
| `make cube-studio-logs` | 查看 Cube-Studio 日志 |

#### 配置中心 (etcd)

| 命令 | 说明 |
|------|------|
| `make etcd-up` | 启动 etcd 配置中心 |
| `make etcd-down` | 停止 etcd 配置中心 |
| `make etcd-logs` | 查看 etcd 日志 |
| `make etcd-ctl` | 进入 etcdctl 交互模式 |
| `make etcd-backup` | 备份 etcd 数据 |
| `make etcd-init` | 初始化 etcd 配置 |

#### 安全工具

| 命令 | 说明 |
|------|------|
| `make generate-secrets` | 生成生产环境密钥 |
| `make generate-secrets-env` | 生成并导出密钥到环境变量 |
| `make generate-secrets-file` | 生成密钥并写入 .env.production |
| `make security-check` | 检查当前安全配置 |

#### 数据库迁移

| 命令 | 说明 |
|------|------|
| `make db-migrate` | 运行数据库迁移（不迁移原始密码） |
| `make db-migrate-dev` | 运行数据库迁移（迁移开发用户密码） |
| `make db-reset` | 重置数据库（警告：会删除所有数据） |
| `make db-seed` | 初始化种子数据（开发环境） |
| `make db-seed-prod` | 初始化种子数据（生产环境） |
| `make db-verify` | 验证数据完整性 |

#### 备份恢复

| 命令 | 说明 |
|------|------|
| `make backup-db` | 备份数据库 |
| `make backup-etcd` | 备份 etcd 配置中心 |
| `make backup-all` | 全量备份（数据库+etcd+配置） |
| `make restore-db` | 恢复数据库 |
| `make restore-etcd` | 恢复 etcd |
| `make schedule-backup` | 设置定时备份（每天凌晨1点） |
| `make unschedule-backup` | 取消定时备份 |

#### 监控和日志

| 命令 | 说明 |
|------|------|
| `make loki-up/down` | 启动/停止 Loki 日志聚合 |
| `make loki-logs` | 查看 Loki 日志 |
| `make promtail-logs` | 查看 Promtail 日志 |
| `make grafana-up/down` | 启动/停止 Grafana 监控面板 |
| `make grafana-logs` | 查看 Grafana 日志 |
| `make monitoring-up` | 启动完整监控系统 (Loki + Promtail + Grafana) |
| `make monitoring-down` | 停止监控系统 |
| `make monitoring-logs` | 查看监控系统日志 |
| `make monitoring-status` | 查看监控系统状态 |

#### 本地开发

| 命令 | 说明 |
|------|------|
| `make dev-install` | 安装 Python 开发依赖 |
| `make dev-portal` | 本地启动门户服务 (端口 8010) |
| `make dev-nl2sql` | 本地启动 NL2SQL 服务 (端口 8011) |
| `make dev-cleaning` | 本地启动 AI 清洗服务 (端口 8012) |
| `make dev-metadata` | 本地启动元数据同步服务 (端口 8013) |
| `make dev-dataapi` | 本地启动数据 API 服务 (端口 8014) |
| `make dev-sensitive` | 本地启动敏感检测服务 (端口 8015) |
| `make dev-audit` | 本地启动审计日志服务 (端口 8016) |

#### 前端开发

| 命令 | 说明 |
|------|------|
| `make web-install` | 安装前端依赖 |
| `make web-dev` | 启动前端开发服务器 |
| `make web-build` | 构建前端生产版本 |
| `make web-build-deploy` | 构建前端并部署到 Portal 静态目录 |
| `make web-preview` | 预览前端生产构建 |

#### 测试命令

| 命令 | 说明 |
|------|------|
| `make test` | 运行所有测试 |
| `make test-e2e` | 运行 E2E 测试 |
| `make test-unit` | 运行单元测试 |
| `make test-lifecycle` | 运行生命周期测试 |
| `make test-foundation` | 运行系统基础测试 |
| `make test-planning` | 运行数据规划测试 |
| `make test-collection` | 运行数据汇聚测试 |
| `make test-processing` | 运行数据加工测试 |
| `make test-analysis` | 运行数据分析测试 |
| `make test-security` | 运行数据安全测试 |
| `make test-report` | 生成测试 HTML 报告 |
| `make test-report-json` | 生成测试 JSON 报告 |
| `make test-clean` | 清理测试结果 |
| `make test-ui` | 打开测试 UI 模式 |
| `make test-debug` | 调试测试 |
| `make test-codegen` | 生成测试代码 |
| `make test-smoke` | 运行冒烟测试 |
| `make test-p0` | 运行 P0 级别测试 |
| `make test-p1` | 运行 P1 级别测试 |
| `make test-coverage` | 生成测试覆盖率报告 |

#### 模块化运维

| 命令 | 说明 |
|------|------|
| `make module-start MODULE=<name>` | 启动模块 |
| `make module-stop MODULE=<name>` | 停止模块 |
| `make module-restart MODULE=<name>` | 重启模块 |
| `make module-status` | 查看模块状态 |
| `make module-health MODULE=<name>` | 模块健康检查 |
| `make module-list` | 列出所有模块 |
| `make module-test MODULE=<name>` | 测试模块 |
| `make module-verify MODULE=<name>` | 快速验证模块 |
| `make mod-base` | 启动基础平台模块 |
| `make mod-metadata` | 启动元数据管理模块 |
| `make mod-integration` | 启动数据集成模块 |
| `make mod-processing` | 启动数据加工模块 |
| `make mod-bi` | 启动 BI 分析模块 |
| `make mod-security` | 启动数据安全模块 |
| `make mod-all` | 启动所有模块 |
| `make mod-stop-all` | 停止所有模块 |

#### 清理

| 命令 | 说明 |
|------|------|
| `make clean` | 停止并清理所有容器和卷 |

### npm Scripts (前端)

#### 开发命令

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动 Vite 开发服务器 |
| `npm run build` | 构建生产版本 (tsc + vite build) |
| `npm run build:full` | 完整构建 (tsc -b + vite build) |
| `npm run preview` | 预览生产构建 |

#### 代码检查

| 命令 | 说明 |
|------|------|
| `npm run lint` | 运行 ESLint 检查 |
| `npm run lint:fix` | 自动修复 ESLint 问题 |

#### 单元测试

| 命令 | 说明 |
|------|------|
| `npm run test` | 运行 Vitest 测试 (watch 模式) |
| `npm run test:ui` | 打开 Vitest UI 界面 |
| `npm run test:run` | 运行一次测试 |
| `npm run test:coverage` | 生成测试覆盖率报告 |
| `npm run test:watch` | 监听模式运行测试 |

#### E2E 测试

| 命令 | 说明 |
|------|------|
| `npm run e2e` | 运行所有 E2E 测试 |
| `npm run e2e:ui` | 打开 Playwright UI 模式 |
| `npm run e2e:debug` | 调试模式运行测试 |
| `npm run e2e:headed` | 有头模式运行测试 |
| `npm run e2e:report` | 显示测试报告 |
| `npm run e2e:p0` | 运行 P0 优先级测试 |
| `npm run e2e:p1` | 运行 P1 优先级测试 |
| `npm run e2e:sup` | 运行 Superset 相关测试 |
| `npm run e2e:adm` | 运行管理相关测试 |
| `npm run e2e:sci` | 运行数据科学相关测试 |
| `npm run e2e:ana` | 运行分析相关测试 |
| `npm run e2e:vw` | 运行查看者相关测试 |
| `npm run e2e:smoke` | 运行冒烟测试 |
| `npm run e2e:auth` | 运行认证测试 |

---

## 模块依赖关系

### 模块依赖图

```
┌─────────────────────────────────────────────────────────────┐
│                    基础设施层 (共享)                          │
│  MySQL | Redis | PostgreSQL | Elasticsearch | Zookeeper     │
└─────────────────────────────────────────────────────────────┘
                              ↑
                              │
┌─────────────────────────────────────────────────────────────┐
│               模块1: 基础平台 (Portal + Audit)               │
│              认证 | 权限 | 用户 | 审计                        │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ↓                    ↓                    ↓
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ 模块2: 元数据 │      │ 模块3: 数据集成│      │ 模块6: 数据安全│
│              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
         │                    │
         └──────┬─────────────┘
                ↓
        ┌──────────────┐
        │ 模块4: 数据加工│
        └──────────────┘
                │
                ↓
        ┌──────────────┐
        │ 模块5: BI分析 │
        └──────────────┘
```

### 模块依赖表

| 模块 | 名称 | 依赖模块 | 内存需求 |
|------|------|----------|----------|
| base | 基础平台 | 无 | ~4 GB |
| metadata | 元数据管理 | base | ~6 GB |
| integration | 数据集成 | base | ~8 GB |
| processing | 数据加工 | base | ~6 GB |
| bi | BI 分析 | base | ~8 GB |
| security | 数据安全 | base | ~5 GB |

### 服务启动顺序

1. **基础设施** (无依赖)
   - MySQL
   - Redis
   - MinIO
   - etcd

2. **基础平台** (依赖基础设施)
   - Portal (8010)
   - Audit Log (8016)

3. **第三方平台** (可并行启动)
   - OpenMetadata (8585)
   - Superset (8088)
   - DolphinScheduler (12345)
   - SeaTunnel (5802)
   - Apache Hop (8083)

4. **二开服务** (依赖基础平台)
   - NL2SQL (8011)
   - AI Cleaning (8012)
   - Metadata Sync (8013)
   - Data API (8014)
   - Sensitive Detect (8015)

---

## 服务端口映射

### 基座平台

| 服务 | 端口 | 说明 |
|------|------|------|
| Cube-Studio | 30080 | Web UI |

### 核心组件

| 服务 | 端口 | 说明 |
|------|------|------|
| Apache Superset | 8088 | Web UI |
| OpenMetadata | 8585 | Web UI |
| OpenMetadata | 8586 | Backend |
| DolphinScheduler | 12345 | Web UI |
| Apache Hop | 8083 | Web UI |
| SeaTunnel | 5802 | API |

### 二开服务

| 服务 | 端口 | 说明 |
|------|------|------|
| Portal | 8010 | 统一门户 |
| NL2SQL | 8011 | 自然语言查询 |
| AI Cleaning | 8012 | AI 清洗服务 |
| Metadata Sync | 8013 | 元数据同步 |
| Data API | 8014 | 数据 API 网关 |
| Sensitive Detect | 8015 | 敏感数据检测 |
| Audit Log | 8016 | 审计日志 |

### 基础设施

| 服务 | 端口 | 说明 |
|------|------|------|
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存 |
| MinIO | 9000 | 对象存储 |
| MinIO Console | 9001 | 管理控制台 |
| etcd | 2379 | 客户端通信 |
| etcd | 2380 | 对等通信 |
| PostgreSQL | 5432 | 数据库 |
| Elasticsearch | 9200 | 搜索引擎 |
| Zookeeper | 2181 | 协调服务 |
| Ollama | 31434 | LLM 服务 |
| Grafana | 3000 | 监控面板 |
| Loki | 3100 | 日志聚合 |

### 前端

| 服务 | 端口 | 说明 |
|------|------|------|
| Vite Dev Server | 3000 | 开发服务器 |
| Vite Preview | 4173 | 预览服务器 |

---

## 默认凭据

### 各服务默认凭据

| 服务 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| **Portal** | admin | admin123 | 统一门户 |
| **Superset** | admin | admin123 | BI 平台 |
| **OpenMetadata** | admin | admin | 元数据平台 |
| **DolphinScheduler** | admin | dolphinscheduler123 | 调度平台 |
| **MinIO** | minioadmin | minioadmin123 | 对象存储 |
| **Grafana** | admin | admin123 | 监控面板 |
| **MySQL** | root | 配置密码 | 数据库 |

> **注意**: 生产环境部署前必须修改所有默认密码！

---

## 相关文档

- [贡献者指南](./CONTRIB.md) - 开发工作流程
- [运维手册](./RUNBOOK.md) - 部署和运维
- [脚本参考](./SCRIPTS.md) - 完整脚本命令参考
- [模块化运维指南](./modules/MODULES.md) - 模块详细说明
- [模块快速参考](./modules/QUICKREF.md) - 模块运维快速参考
