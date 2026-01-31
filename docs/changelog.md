# 变更日志

所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

### 新增
- 生产就绪验收测试脚本 (scripts/acceptance-test.sh)
  - 68 项自动化测试
  - 文件存在性、代码质量、功能正确性验证
  - 部署配置、CI/CD、安全检查
  - 通过率 98%

### 修复
- pytest.ini 配置：添加 `pythonpath = .` 解决模块导入问题
- acceptance-test.sh：修正 token_blacklist 导入检查逻辑

### 测试
- 单元测试通过：11 passed, 5 skipped
- 验收测试通过：67 passed, 1 warning, 0 failed

---

## [1.1.0] - 2026-01-31

### 生产就绪实施 (12 个功能模块)

#### 安全与认证
- Token 黑名单实现 (services/common/token_blacklist.py)
  - Redis 存储已撤销 Token
  - 支持单个和批量撤销
  - 自动过期清理
- 生产环境配置模板 (services/.env.production.template)
- 配置生成脚本 (scripts/setup-production.sh)

#### HTTPS/TLS
- Nginx 反向代理配置 (deploy/nginx/)
- SSL 证书设置脚本 (deploy/nginx/ssl_setup.sh)
- 支持 Let's Encrypt 自动证书

#### 监控与告警
- Prometheus 部署配置 (deploy/prometheus/)
- Alertmanager 配置 (deploy/alertmanager/)
- 9 条告警规则

#### 运维自动化
- 日志清理脚本 (scripts/log-cleanup.sh)
- 数据库备份/恢复脚本 (scripts/backup-database.sh, restore-database.sh)
- 全量备份脚本 (scripts/backup-all.sh)
- 定时任务设置脚本

#### CI/CD
- GitHub Actions CI 工作流 (.github/workflows/ci.yml)
- GitHub Actions CD 工作流 (.github/workflows/deploy.yml)
- 代码检查、类型检查、安全扫描

#### 质量保障
- 配置基类 (services/common/base_config.py)
- 认证模块单元测试 (services/common/tests/test_auth.py)
- 性能压测脚本 (tests/performance/)
- 生产部署检查清单 (docs/production-checklist.md)

---

## [1.0.0] - 2026-01-30

### 新增

#### 基础架构
- 文档导航索引 (docs/README.md)
- 项目状态总览 (docs/project-status.md)
- 服务状态详细清单 (docs/services-status.md)
- 技术债务追踪文档 (docs/technical-debt.md)
- etcd 配置中心 (deploy/etcd/)
  - etcd 服务部署配置
  - etcdctl 快捷操作脚本
  - 配置中心客户端 (services/common/config_center.py)
  - 配置热更新支持
  - 敏感配置加密 (AES-256-GCM)

#### 监控和可观测性
- Loki 日志聚合 (deploy/loki/)
  - Loki 日志存储和查询引擎
  - Promtail 日志采集代理
  - Grafana 监控面板
  - 告警规则配置
- OpenTelemetry 分布式追踪 (services/common/telemetry.py)
  - 追踪中间件
  - 追踪装饰器 (@traced, @timed)
  - 指标采集

#### 安全
- 安全工具模块 (services/common/security.py)
  - 密码生成器
  - 密钥生成器
  - 密码强度检查
  - 敏感信息掩码
- 安全配置验证
  - 安全检查端点 (/security/check)
  - 密钥生成脚本 (scripts/generate_secrets.py)
  - 生产环境安全验证

#### API 标准化
- 统一 API 响应模型 (services/common/api_response.py)
  - ApiResponse 通用响应格式
  - ErrorCode 错误码定义
- v1 版本 API (所有服务)
  - SeaTunnel v1 API
  - ShardingSphere v1 API
  - Apache Hop v1 API
  - DataHub v1 API
  - DolphinScheduler v1 API
  - Superset v1 API
  - 内部服务 v1 API

#### 数据持久化
- ORM 基础模型 (services/common/orm_models.py)
- Repository 基类 (services/common/repositories/base.py)
- 数据库持久化层
  - 元数据同步映射规则
  - 敏感检测规则和报告
  - 审计日志

#### LLM 客户端
- 统一 LLM 客户端 (services/common/llm_client.py)
  - 缓存机制
  - 指数退避重试
  - 错误处理和日志记录

#### Webhook 安全
- Webhook 签名验证 (services/common/webhook_security.py)
  - HMAC-SHA256 签名

#### 客户端
- ShardingSphere 客户端 (services/common/shardingsphere_client.py)
  - DistSQL 动态配置

#### Cube-Studio 集成
- Cube-Studio 专用路由 (services/portal/routers/cubestudio.py)
  - 模型推理 API
  - 对话补全 API
  - 快速对话 API
  - 服务状态 API
  - 数据管理 API
  - Notebook API
  - 监控告警 API

#### 统一认证
- Token 验证端点 (/auth/validate)
- 用户信息端点 (/auth/userinfo)
- Token 撤销端点 (/auth/revoke)
- 前端认证 API (web/src/api/auth.ts)

#### 规范文档
- 配置中心使用指南 (docs/standards/config-center.md)
- API 设计规范 (docs/standards/api-design.md)
- 安全配置指南 (docs/standards/security.md)
- 统一认证框架设计 (docs/standards/unified-auth.md)

### 变更

#### 后端
- Portal 配置中心集成 (services/portal/config.py)
- Superset Token 管理器 (线程安全)
- 所有服务添加 v1 API
- 配置文件支持热更新

#### 前端
- 所有 API 客户端标准化
- 添加 v1 版本 API 函数
- Token 管理优化

### 修复

#### 安全
- Superset Token 线程安全问题
- 硬编码用户凭据移至环境变量
- 弱密钥检测和警告

#### 功能
- ShardingSphere 配置不同步问题 (实现 DistSQL 动态配置)
- Apache Hop API 完全未实现 (实现 REST API 对接)
- LLM 调用无缓存、无重试 (统一 LLM 客户端)
- Webhook 无签名验证 (HMAC-SHA256)

### Makefile 新增命令

```bash
# 配置中心
make etcd-up          # 启动 etcd
make etcd-down        # 停止 etcd
make etcd-logs        # 查看 etcd 日志
make etcd-ctl         # etcdctl 交互
make etcd-backup      # 备份 etcd
make etcd-init        # 初始化配置

# 安全
make generate-secrets         # 生成密钥
make generate-secrets-env     # 生成并导出
make generate-secrets-file    # 生成并写入文件
make security-check           # 检查安全配置

# 监控
make monitoring-up      # 启动监控系统
make monitoring-down    # 停止监控系统
make monitoring-logs    # 查看日志
make monitoring-status  # 查看状态
make loki-up            # 启动 Loki
make grafana-up         # 启动 Grafana
```

---

## [0.1.0] - 2025-01-29

### 新增
- 项目初始化
- Cube-Studio 基座集成
- 7个二开微服务（Python/FastAPI）
  - portal: 统一门户
  - nl2sql: 自然语言查询
  - ai_cleaning: AI清洗推荐
  - metadata_sync: 元数据同步
  - data_api: 数据资产API
  - sensitive_detect: 敏感检测
  - audit_log: 审计日志
- 部署配置
  - K3s 安装脚本
  - Superset Docker Compose
  - DataHub Docker Compose
  - Apache Hop Docker Compose
  - SeaTunnel Docker Compose
  - DolphinScheduler Docker Compose
  - ShardingSphere 配置
- 文档
  - 架构设计文档
  - 技术选型文档
  - 部署指南
