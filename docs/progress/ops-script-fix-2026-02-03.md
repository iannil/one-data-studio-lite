# 运维脚本问题修复

## 修复日期
2026-02-03

## 问题描述

1. **微服务容器健康检查失败**
   - 现象: 所有微服务容器显示 unhealthy
   - 原因: 镜像中没有 curl 命令，healthcheck 失败
   - 错误: `exec: "curl": executable file not found in $PATH`

2. **bash 3.2 兼容性问题**
   - 现象: 脚本在 macOS 上运行失败
   - 原因: macOS 默认 bash 3.2 不支持关联数组 (`declare -A`)
   - 解决: 移除 `set -u`，改用 case 函数替代关联数组

3. **Docker Compose 网络配置问题**
   - 现象: 容器无法连接到网络
   - 原因: 现有网络缺少 Docker Compose 期望的标签
   - 解决: 使用 `external: true` 声明外部网络

## 修复方案

### 1. 健康检查修复 (`services/docker-compose.yml`)

修改前:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
```

修改后:
```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8010/health\", timeout=5)'"]
```

### 2. 脚本兼容性修复

- `scripts/lib/common.sh`: 移除 `set -u`，添加 zsh 兼容
- `scripts/infra.sh`: 用 case 函数替代关联数组
- `scripts/services.sh`: 用 case 函数替代关联数组
- `scripts/health.sh`: 用字符串变量替代关联数组

### 3. 网络配置修复

- `scripts/infra.sh`: 网络配置改为 `external: true`

## 修复结果

### 微服务状态 (7/7 healthy)

| 服务 | 端口 | 状态 |
|------|------|------|
| Portal | 8010 | ✅ healthy |
| NL2SQL | 8011 | ✅ healthy |
| AI-Cleaning | 8012 | ✅ healthy |
| Metadata-Sync | 8013 | ✅ healthy |
| Data-API | 8014 | ✅ healthy |
| Sensitive-Detect | 8015 | ✅ healthy |
| Audit-Log | 8016 | ✅ healthy |

### 基础设施状态 (3/3 healthy)

| 服务 | 端口 | 状态 |
|------|------|------|
| MySQL | 3306 | ✅ healthy |
| Redis | 6379 | ✅ healthy |
| MinIO | 9000 | ✅ healthy |

### 平台服务状态 (5/6 healthy)

| 服务 | 端口 | 状态 |
|------|------|------|
| OpenMetadata | 8585 | ✅ healthy |
| Superset | 8088 | ✅ healthy |
| DolphinScheduler | 12345 | ✅ healthy |
| Hop | 8083 | ✅ healthy |
| ShardingSphere | 3309 | ✅ healthy |
| SeaTunnel | 5802 | ⏳ 下载中 (2GB+) |

## 后续修复

### 4. OpenMetadata 数据库初始化问题

- **现象**: OpenMetadata 容器启动后立即退出
- **原因**: 缺少数据库迁移初始化步骤
- **错误**: `Table 'openmetadata.DATABASE_CHANGE_LOG' doesn't exist`
- **解决**: 在 `deploy/openmetadata/docker-compose.yml` 中添加迁移容器

添加的迁移容器配置:
```yaml
openmetadata-migrate:
  image: docker.getcollate.io/openmetadata/server:1.4.4
  container_name: ods-openmetadata-migrate
  restart: "no"
  command: ["./bootstrap/openmetadata-ops.sh", "migrate"]
  depends_on:
    openmetadata-mysql:
      condition: service_healthy
    openmetadata-elasticsearch:
      condition: service_healthy
```

同时更新主服务依赖:
```yaml
openmetadata-server:
  depends_on:
    ...
    openmetadata-migrate:
      condition: service_completed_successfully
```

## 最新状态

2026-02-03 13:30 更新:
- ✅ 所有基础设施服务 healthy
- ✅ 所有微服务 healthy (7/7)
- ✅ OpenMetadata 修复后 healthy
- ✅ ShardingSphere healthy
- ⏳ SeaTunnel 镜像下载中 (2GB+ 镜像)
- ❌ 前端服务未启动 (开发模式，需要手动启动)
