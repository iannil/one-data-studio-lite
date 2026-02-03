# 运维手册 (RUNBOOK)

**更新日期**: 2026-02-03
**版本**: 1.2
**来源**: Makefile, ods.sh, .env.example

本文档为 ONE-DATA-STUDIO-LITE 项目的运维人员提供部署程序、监控告警、常见问题处理和回滚程序的完整参考。

---

## 目录

1. [部署程序](#部署程序)
2. [监控与告警](#监控与告警)
3. [常见问题与修复](#常见问题与修复)
4. [回滚程序](#回滚程序)
5. [备份与恢复](#备份与恢复)
6. [性能调优](#性能调优)
7. [安全加固](#安全加固)

---

## 服务访问地址

完整的服务访问地址可通过以下命令获取：

```bash
./ods.sh info
```

### 默认访问地址

| 服务 | 地址 | 凭据 |
|------|------|------|
| **基座平台** | | |
| Cube-Studio | http://localhost:30080 | - |
| **核心组件** | | |
| Apache Superset | http://localhost:8088 | admin/admin123 |
| OpenMetadata | http://localhost:8585 | admin/admin |
| DolphinScheduler | http://localhost:12345 | admin/dolphinscheduler123 |
| Apache Hop | http://localhost:8083 | - |
| SeaTunnel API | http://localhost:5802 | - |
| **二开服务** | | |
| 统一门户 Portal | http://localhost:8010 | admin/admin123 |
| NL2SQL API | http://localhost:8011/docs | - |
| AI清洗 API | http://localhost:8012/docs | - |
| 元数据同步 API | http://localhost:8013/docs | - |
| 数据API网关 | http://localhost:8014/docs | - |
| 敏感检测 API | http://localhost:8015/docs | - |
| 审计日志 API | http://localhost:8016/docs | - |
| **前端** | | |
| 开发服务器 | http://localhost:3000 | - |
| **基础设施** | | |
| MySQL | localhost:3306 | root/配置密码 |
| Redis | localhost:6379 | - |
| MinIO | http://localhost:9000 | minioadmin/minioadmin123 |
| etcd | localhost:2379 | - |

---

## 部署程序

### 前置检查清单

在执行部署前，请确认以下检查项：

#### 系统资源检查

| 检查项 | 命令 | 最低要求 | 推荐配置 |
|--------|------|---------|---------|
| CPU 核心 | `nproc` | 4 核 | 8 核+ |
| 可用内存 | `free -h` | 16 GB | 32 GB+ |
| 可用磁盘 | `df -h` | 100 GB | 200 GB+ SSD |
| Docker 版本 | `docker --version` | 24.0+ | 最新稳定版 |
| Docker Compose | `docker compose version` | 2.0+ | 最新稳定版 |

#### 网络检查

```bash
# 检查端口占用
netstat -tuln | grep -E ':(8010|8011|8012|8013|8014|8015|8016|8088|9002)'

# 检查 Docker 网络
docker network ls | grep ods-network

# 检查防火墙
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-all  # CentOS
```

#### 安全配置检查

```bash
# 运行安全检查
make security-check

# 或通过 API
curl http://localhost:8010/security/check
```

### 标准部署流程

#### 1. 全量部署

```bash
# 一键部署所有组件
./ods.sh start all
# 或使用 make
make start

# 等待部署完成，查看状态
./ods.sh status all
make status

# 查看访问地址
./ods.sh info
make info
```

#### 2. 分阶段部署

**阶段 1: 基础设施**

```bash
# 启动基础设施 (MySQL, Redis, MinIO)
./ods.sh start infra
# 或使用 make
make start-infra

# 等待就绪后检查健康状态
./ods.sh health infra
make health-infra
```

**阶段 2: 第三方平台**

```bash
# 启动所有平台服务
./ods.sh start platforms
# 或使用 make
make start-platforms

# 或按需启动单个平台
make superset-up          # Apache Superset (BI)
make openmetadata-up      # OpenMetadata (元数据)
make dolphinscheduler-up  # DolphinScheduler (调度)
make hop-up               # Apache Hop (ETL)
make seatunnel-up         # SeaTunnel (同步)
make cube-studio-up       # Cube-Studio (可选)
```

**阶段 3: 二开服务**

```bash
# 启动所有二开服务
./ods.sh start services
# 或使用 make
make start-services

# 查看日志
make services-logs
```

**阶段 4: 前端（开发环境）**

```bash
# 启动前端开发服务器
./ods.sh start web
# 或使用 make
make start-web
```

#### 3. 初始化数据

```bash
# 初始化种子数据
./ods.sh init-data seed
# 或使用 make
make init-data

# 验证数据完整性
./ods.sh init-data verify
make init-data-verify

# 查看数据状态
./ods.sh init-data status
make init-data-status
```

#### 4. 生产环境部署

```bash
# 1. 生成生产密钥
make generate-secrets-file
chmod 600 .env.production

# 2. 配置生产环境变量
cp .env.example .env.production
# 编辑 .env.production，设置生产配置

# 3. 初始化数据库
make db-migrate
make db-seed-prod

# 4. 部署服务
docker compose --env-file .env.production -f services/docker-compose.yml up -d

# 5. 验证部署
make security-check
curl http://localhost:8010/health
```

### 验证部署

#### 健康检查

```bash
# 检查所有服务状态
./ods.sh status all
make status

# 分层健康检查
./ods.sh health all        # 所有服务
./ods.sh health infra      # 基础设施
./ods.sh health platforms  # 平台服务
./ods.sh health services   # 微服务

# 或使用 make
make health
make health-infra
make health-platforms
make health-services

# 检查各服务健康端点
curl http://localhost:8010/health  # Portal
curl http://localhost:8011/health  # NL2SQL
curl http://localhost:8012/health  # AI Cleaning
curl http://localhost:8013/health  # Metadata Sync
curl http://localhost:8014/health  # Data API
curl http://localhost:8015/health  # Sensitive Detect
curl http://localhost:8016/health  # Audit Log
```

#### 功能验证

```bash
# 运行生命周期测试（推荐）
./ods.sh test lifecycle
make test-lifecycle

# 分阶段测试
make test-foundation       # 系统基础测试
make test-planning         # 数据规划测试
make test-collection       # 数据汇聚测试
make test-processing       # 数据加工测试
make test-analysis         # 数据分析测试
make test-security         # 数据安全测试

# 运行所有测试
./ods.sh test all
make test

# 检查数据库连接
make db-verify
```

---

## 监控与告警

### 监控系统架构

```
应用服务 -> Promtail -> Loki <- Grafana
                |
                v
            日志聚合
```

### 启动监控

```bash
# 启动完整监控系统
make monitoring-up

# 访问 Grafana
open http://localhost:3000
# 默认用户名: admin
# 默认密码: admin123 (首次登录需修改)
```

### 监控指标

#### 系统指标

| 指标 | 告警阈值 | 说明 |
|------|---------|------|
| CPU 使用率 | > 80% | 持续 5 分钟 |
| 内存使用率 | > 85% | 持续 5 分钟 |
| 磁盘使用率 | > 80% | - |
| 磁盘 I/O 等待 | > 20% | 持续 3 分钟 |

#### 应用指标

| 指标 | 告警阈值 | 说明 |
|------|---------|------|
| 服务可用性 | < 99% | 健康检查失败 |
| API 响应时间 | > 3s | P95 响应时间 |
| 错误率 | > 5% | 5xx 错误占比 |
| 队列堆积 | > 1000 | 异步任务队列 |

#### 数据库指标

| 指标 | 告警阈值 | 说明 |
|------|---------|------|
| 连接数 | > 80% 最大连接 | - |
| 慢查询 | > 10s | - |
| 复制延迟 | > 30s | 主从延迟 |

### 日志查询

```bash
# 查看特定服务日志
docker logs -f ods-portal-1

# 查看最近 100 行
docker logs --tail 100 ods-portal-1

# 查看特定时间范围
docker logs --since 2024-02-01T00:00:00 ods-portal-1

# 通过 Loki 查询
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="portal"} |= "error"'
```

### 告警配置

在 Grafana 中配置告警规则：

1. 导航到 Alerting → New alert rule
2. 设置查询条件
3. 配置通知渠道（Email、Webhook）
4. 设置评估间隔（建议 1 分钟）

---

## 常见问题与修复

### 服务启动失败

#### 问题 1: 端口已被占用

**症状**: 服务启动时报错 "port is already allocated"

**诊断**:
```bash
# 查找占用端口的进程
lsof -i :8010  # macOS
ss -tlnp | grep 8010  # Linux
```

**修复**:
```bash
# 停止占用端口的进程
kill -9 <PID>

# 或修改服务端口
export PORTAL_APP_PORT=8010
```

#### 问题 2: 数据库连接失败

**症状**: 日志显示 "Could not connect to database"

**诊断**:
```bash
# 检查数据库是否运行
docker ps | grep mysql

# 检查连接字符串
echo $DATABASE_URL
```

**修复**:
```bash
# 启动数据库
docker start ods-mysql-1

# 或更新数据库连接
export DATABASE_URL="mysql+aiomysql://user:pass@host:3306/db"
```

#### 问题 3: 内存不足

**症状**: 服务被 OOM Killer 杀死

**诊断**:
```bash
# 查看 OOM 日志
dmesg | grep -i "out of memory"

# 查看内存使用
free -h
```

**修复**:
```bash
# 增加 swap 空间
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 或减少 Docker 内存限制
# 编辑 docker-compose.yml，添加:
services:
  portal:
    deploy:
      resources:
        limits:
          memory: 512M
```

#### 问题 4: LLM 服务不可用

**症状**: NL2SQL 服务报错 "LLM service unavailable"

**诊断**:
```bash
# 检查 Ollama 是否运行
curl http://localhost:31434/api/tags

# 检查模型是否下载
curl http://localhost:31434/api/tags | grep qwen
```

**修复**:
```bash
# 启动 Ollama
docker start ollama

# 下载模型
curl http://localhost:31434/api/pull -d '{"name":"qwen2.5:7b"}'

# 或更新 LLM 地址
export LLM_BASE_URL=http://new-host:31434
```

### 性能问题

#### 问题 1: API 响应缓慢

**诊断**:
```bash
# 检查服务日志
docker logs ods-portal-1 | grep "slow query"

# 检查数据库性能
docker exec ods-mysql-1 mysqladmin processlist
```

**修复**:
```bash
# 重启服务
docker restart ods-portal-1

# 优化数据库索引
# 登录数据库并运行 EXPLAIN 分析
```

#### 问题 2: 数据库连接池耗尽

**症状**: 日志显示 "pool exhausted"

**修复**:
```bash
# 增加连接池大小
# 在 config.py 中设置:
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=10
```

### 认证问题

#### 问题 1: Token 过期频繁

**症状**: 用户频繁被要求重新登录

**修复**:
```bash
# 增加有效期
export JWT_EXPIRE_HOURS=168  # 7 天

# 或减少刷新阈值
export JWT_REFRESH_THRESHOLD_MINUTES=120
```

#### 问题 2: 安全检查失败

**症状**: security-check 返回警告

**修复**:
```bash
# 查看详细警告
curl http://localhost:8010/security/check

# 根据警告修复配置
# 例如:
export JWT_SECRET=$(openssl rand -hex 32)
export INTERNAL_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
```

---

## 回滚程序

### 服务级回滚

#### 回滚单个服务

```bash
# 查看当前镜像版本
docker images | grep ods-portal

# 停止当前服务
docker compose -f services/docker-compose.yml stop portal

# 切换到旧版本镜像
# 编辑 docker-compose.yml，修改 image tag
# 或:
docker tag ods-portal:new ods-portal:previous

# 重启服务
docker compose -f services/docker-compose.yml up -d portal
```

#### 回滚所有二开服务

```bash
# 停止所有服务
make services-down

# 切换到旧版本标签
# 编辑 .env 或 docker-compose.yml
export VERSION=v1.0.0

# 重新启动
make services-up
```

### 数据库回滚

#### 备份当前状态

```bash
# 备份数据库
make backup-db

# 记录当前迁移版本
docker exec ods-mysql-1 mysql -uroot -p database -e "SELECT * FROM alembic_version;"
```

#### 执行回滚

```bash
# 回滚到指定版本
docker exec ods-mysql-1 mysql -uroot -p database -e "UPDATE alembic_version SET version_num='<target_version>';"

# 或使用迁移工具回滚
alembic downgrade -1
```

### 紧急回滚

#### 快速停止所有服务

```bash
# 立即停止所有服务
./ods.sh stop all
make stop

# 分层停止
./ods.sh stop services     # 停止微服务
./ods.sh stop platforms    # 停止平台服务
./ods.sh stop infra        # 停止基础设施
```

#### 恢复备份

```bash
# 恢复数据库
make restore-db

# 恢复配置
make restore-etcd
```

---

## 备份与恢复

### 备份策略

| 备份类型 | 频率 | 保留期 | 存储位置 |
|---------|------|--------|---------|
| 数据库完整备份 | 每天 | 30 天 | /backup/database |
| etcd 配置备份 | 每天 | 30 天 | /backup/etcd |
| 增量备份 | 每小时 | 7 天 | /backup/incremental |
| 应用日志 | 每天 | 7 天 | /backup/logs |

### 自动备份

```bash
# 设置定时备份（每天凌晨 1 点）
make schedule-backup

# 查看定时任务
crontab -l
```

### 手动备份

```bash
# 全量备份
make backup-all

# 仅备份数据库
make backup-db

# 仅备份 etcd
make backup-etcd
```

### 恢复程序

#### 恢复数据库

```bash
# 1. 停止相关服务
make services-down

# 2. 恢复数据库
make restore-db

# 3. 验证数据
make db-verify

# 4. 重启服务
make services-up
```

#### 恢复 etcd

```bash
# 1. 停止 etcd
make etcd-down

# 2. 恢复数据
make restore-etcd

# 3. 启动 etcd
make etcd-up
```

---

## 性能调优

### 数据库优化

```sql
-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- 启用慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- 分析表
ANALYZE TABLE table_name;

-- 优化表
OPTIMIZE TABLE table_name;
```

### Docker 资源限制

```yaml
# docker-compose.yml
services:
  portal:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 应用缓存

```python
# 启用配置缓存
export CONFIG_CACHE_TTL=300  # 5 分钟

# 启用数据库连接池
export DATABASE_POOL_SIZE=20
export DATABASE_MAX_OVERFLOW=10
```

---

## 安全加固

### 生产环境安全检查清单

- [ ] 所有默认密码已修改
- [ ] JWT_SECRET 使用强随机字符串
- [ ] INTERNAL_TOKEN 已配置
- [ ] HTTPS 已启用
- [ ] 防火墙规则已配置
- [ ] 审计日志已启用
- [ ] 定期备份已配置
- [ ] 监控告警已配置

### 生成安全密钥

```bash
# 生成所有生产密钥
make generate-secrets-file

# 或单独生成
export JWT_SECRET=$(openssl rand -hex 32)
export INTERNAL_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export META_SYNC_WEBHOOK_SECRET=$(openssl rand -hex 32)
```

### 配置 HTTPS

```bash
# 使用 Nginx 反向代理
# 配置 SSL 证书

# 示例配置
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 相关文档

- [部署指南](./deployment.md) - 基础部署说明
- [安全配置指南](./standards/security.md) - 详细安全配置
- [贡献者指南](./CONTRIB.md) - 开发相关内容
- [配置参考](./REFERENCE.md) - 完整配置参考
- [文档状态](./STATUS.md) - 文档更新状态
- [生产检查清单](./production-checklist.md) - 上线前检查
- [模块化运维指南](./modules/MODULES.md) - 模块详细说明
