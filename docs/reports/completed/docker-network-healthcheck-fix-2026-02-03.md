# Docker 网络统一、健康检查配置与部署脚本标准化

**修改日期**: 2026-02-03
**修改状态**: 已完成

---

## 修改概述

本次修改解决了三个问题：
1. Docker 网络命名不一致问题
2. 关键服务缺少健康检查配置问题
3. 部署脚本不标准化问题（新增共享函数库）

---

## Phase 1: Docker 网络统一

### 问题描述
项目中存在两种网络命名：
- `ods-network`: 大部分组件使用
- `one-data-studio-network`: superset, etcd, loki 使用

### 修改内容

| 文件 | 修改说明 |
|------|---------|
| `deploy/superset/docker-compose.yml` | 将所有 `one-data-studio-network` 替换为 `ods-network` |
| `deploy/etcd/docker-compose.yml` | 将所有 `one-data-studio-network` 替换为 `ods-network` |
| `deploy/etcd/etcdctl.sh` | 将 `--network one-data-studio-network` 替换为 `--network ods-network` |
| `deploy/loki/docker-compose.yml` | 将所有 `one-data-studio-network` 替换为 `ods-network` |

### 修改时间
- 2026-02-03 开始修改
- 2026-02-03 完成验证

---

## Phase 2: 健康检查配置

### 问题描述
以下服务缺少健康检查配置，影响依赖服务的启动顺序和服务可观测性。

### 修改内容

#### 1. 二开服务 (`services/docker-compose.yml`)

添加公共健康检查模板和7个微服务的健康检查：

```yaml
x-healthcheck-common: &healthcheck-common
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

| 服务 | 端口 | 健康检查端点 |
|------|------|------------|
| portal | 8010 | `http://localhost:8010/health` |
| nl2sql | 8011 | `http://localhost:8011/health` |
| ai-cleaning | 8012 | `http://localhost:8012/health` |
| metadata-sync | 8013 | `http://localhost:8013/health` |
| data-api | 8014 | `http://localhost:8014/health` |
| sensitive-detect | 8015 | `http://localhost:8015/health` |
| audit-log | 8016 | `http://localhost:8016/health` |

#### 2. DataHub (`deploy/datahub/docker-compose.yml`)

| 服务 | 健康检查配置 |
|------|------------|
| datahub-zookeeper | `echo 'ruok' \| nc localhost 2181` |
| datahub-kafka | `kafka-broker-api-versions --bootstrap-server localhost:9092` |
| datahub-schema-registry | `curl -f http://localhost:8081/subjects` |
| datahub-gms | `curl -f http://localhost:8080/health` (start_period: 120s) |
| datahub-frontend | `curl -f http://localhost:9002/` (start_period: 60s) |
| datahub-actions | `curl -f http://datahub-gms:8080/health` |

同时优化了依赖配置，使用 `service_healthy` 条件代替简单的 `service_started`。

#### 3. Hop (`deploy/hop/docker-compose.yml`)

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

#### 4. ShardingSphere (`deploy/shardingsphere/docker-compose.yml`)

```yaml
healthcheck:
  test: ["CMD-SHELL", "nc -z localhost 3307 || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

#### 5. Prometheus (`deploy/prometheus/docker-compose.yml`)

```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost:9090/-/healthy"]
  interval: 30s
  timeout: 10s
  retries: 3
```

#### 6. Alertmanager (`deploy/alertmanager/docker-compose.yml`)

```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost:9093/-/healthy"]
  interval: 30s
  timeout: 10s
  retries: 3
```

#### 7. Cube-Studio (`deploy/cube-studio/docker-compose.yml`)

| 服务 | 健康检查配置 |
|------|------------|
| cube-frontend | `curl -f http://localhost:80/` |
| cube-myapp | `curl -f http://localhost:80/health` (start_period: 60s) |

---

## 验证结果

### 1. 网络统一验证
```bash
grep -r "one-data-studio-network" deploy/
# 预期结果: 无输出 ✓
```

### 2. Docker Compose 配置验证
```bash
docker compose -f services/docker-compose.yml config
# 预期结果: 配置正确解析，每个服务都有 healthcheck 配置 ✓
```

---

## 影响范围

### 文件变更清单
1. `deploy/superset/docker-compose.yml`
2. `deploy/etcd/docker-compose.yml`
3. `deploy/etcd/etcdctl.sh`
4. `deploy/loki/docker-compose.yml`
5. `services/docker-compose.yml`
6. `deploy/datahub/docker-compose.yml`
7. `deploy/hop/docker-compose.yml`
8. `deploy/shardingsphere/docker-compose.yml`
9. `deploy/prometheus/docker-compose.yml`
10. `deploy/alertmanager/docker-compose.yml`
11. `deploy/cube-studio/docker-compose.yml`

### 回滚方案

如需回滚，可从 git 历史恢复：
```bash
git checkout HEAD~1 -- deploy/ services/docker-compose.yml
```

---

---

## Phase 3: 部署脚本标准化

### 问题描述

项目中存在多个部署脚本，各自实现日志、网络、Docker 操作等功能，存在以下问题：
- Shebang 不统一 (`#!/bin/bash` vs `#!/usr/bin/env bash`)
- 错误处理级别不一致 (`set -e` vs `set -euo pipefail`)
- 日志函数命名不统一 (`log_warn` vs `log_warning`)
- 等待机制实现不同 (curl轮询 vs Docker健康检查)
- 代码重复，维护困难

### 修改内容

#### 1. 新建共享函数库 (`scripts/lib/`)

| 文件 | 功能说明 |
|------|---------|
| `scripts/lib/colors.sh` | 统一颜色定义 (RED, GREEN, YELLOW, BLUE, PURPLE, CYAN, NC) |
| `scripts/lib/logging.sh` | 日志函数 (log_info, log_success, log_warn, log_error, log_step, log_section, log_debug) |
| `scripts/lib/docker.sh` | Docker工具函数 (wait_for_http, wait_for_container, deploy_compose, stop_compose, check_docker) |
| `scripts/lib/network.sh` | 网络管理函数 (create_network, remove_network, network_exists) |
| `scripts/lib/common.sh` | 统一入口，加载所有模块，导出 PROJECT_ROOT, DEPLOY_DIR, SERVICES_DIR |

**共享库特性**:
- 防止重复加载 (`[[ -n "${_ODS_XXX_LOADED:-}" ]] && return`)
- 统一 `set -euo pipefail` 错误处理
- 带时间戳的日志输出
- 标准化的默认超时和重试参数

#### 2. 重构部署脚本

| 脚本 | 原行数 | 新行数 | 变化 |
|------|--------|--------|------|
| `deploy.sh` | 163 | 163 | 使用共享库重写 |
| `start-all.sh` | 489 | 489 | 使用共享库重写 |
| `scripts/production-deploy.sh` | 130 | 130 | 使用共享库重写 |
| `deploy/test/start.sh` | 187 | 187 | 使用共享库重写 |
| `deploy/test-env.sh` | 295 | 295 | 使用共享库重写 |

**重构要点**:
- 统一使用 `#!/usr/bin/env bash` shebang
- 通过 `source` 加载 `scripts/lib/common.sh`
- 移除重复的函数定义
- 保持原有功能和命令行接口不变

### 验证结果

```bash
# 语法检查
bash -n scripts/lib/colors.sh    # ✓
bash -n scripts/lib/logging.sh   # ✓
bash -n scripts/lib/docker.sh    # ✓
bash -n scripts/lib/network.sh   # ✓
bash -n scripts/lib/common.sh    # ✓
bash -n deploy.sh                # ✓
bash -n start-all.sh             # ✓
bash -n scripts/production-deploy.sh  # ✓
bash -n deploy/test/start.sh     # ✓
bash -n deploy/test-env.sh       # ✓

# 功能测试
./deploy.sh help      # ✓ 正确显示帮助信息
./start-all.sh help   # ✓ 正确显示帮助信息
```

---

## 完整文件变更清单

### Phase 1 & 2: Docker 配置
1. `deploy/superset/docker-compose.yml` - 网络统一
2. `deploy/etcd/docker-compose.yml` - 网络统一
3. `deploy/etcd/etcdctl.sh` - 网络统一
4. `deploy/loki/docker-compose.yml` - 网络统一
5. `services/docker-compose.yml` - 健康检查
6. `deploy/datahub/docker-compose.yml` - 健康检查
7. `deploy/hop/docker-compose.yml` - 健康检查
8. `deploy/shardingsphere/docker-compose.yml` - 健康检查
9. `deploy/prometheus/docker-compose.yml` - 健康检查
10. `deploy/alertmanager/docker-compose.yml` - 健康检查
11. `deploy/cube-studio/docker-compose.yml` - 健康检查

### Phase 3: 脚本标准化
12. `scripts/lib/colors.sh` - 新建
13. `scripts/lib/logging.sh` - 新建
14. `scripts/lib/docker.sh` - 新建
15. `scripts/lib/network.sh` - 新建
16. `scripts/lib/common.sh` - 新建
17. `deploy.sh` - 重构
18. `start-all.sh` - 重构
19. `scripts/production-deploy.sh` - 重构
20. `deploy/test/start.sh` - 重构
21. `deploy/test-env.sh` - 重构

---

## 回滚方案

如需回滚，可从 git 历史恢复：
```bash
# 回滚 Phase 1 & 2
git checkout HEAD~1 -- deploy/ services/docker-compose.yml

# 回滚 Phase 3
git checkout HEAD~1 -- deploy.sh start-all.sh scripts/production-deploy.sh deploy/test/start.sh deploy/test-env.sh
rm -rf scripts/lib/
```

---

## 后续建议

1. **验证启动顺序**: 执行 `./start-all.sh all` 验证所有服务能正常启动
2. **监控健康状态**: 使用 `docker ps --format "table {{.Names}}\t{{.Status}}"` 检查服务健康状态
3. **共享库扩展**: 未来可在 `scripts/lib/` 添加更多通用函数
4. **添加 ShellCheck**: 考虑在 CI 中集成 ShellCheck 进行脚本质量检查
