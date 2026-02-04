# 分阶段测试脚本修复记录

**修复时间**: 2026-02-04

---

## 网络隔离配置（2026-02-04 13:30）

### 问题
基础设施服务使用标准端口（3306, 6379, 9000, 9001）与其他项目（如 ruoyi）冲突。

### 解决方案
使用非标准端口配置，通过环境变量可覆盖：

| 服务 | 原端口 | 新端口 | 环境变量 |
|------|--------|--------|----------|
| MySQL | 3306 | 13306 | `ODS_MYSQL_PORT`, `MYSQL_PORT` |
| Redis | 6379 | 16379 | `ODS_REDIS_PORT`, `REDIS_PORT` |
| MinIO API | 9000 | 19000 | `ODS_MINIO_PORT` |
| MinIO Console | 9001 | 19001 | `ODS_MINIO_CONSOLE_PORT` |

### 修改文件
- `scripts/infra.sh` - 更新端口映射和配置
- `scripts/test-phased.sh` - 更新端口检查逻辑
- `services/common/base_config.py` - 更新默认数据库/Redis连接配置
- `services/docker-compose.yml` - 添加端口环境变量支持
- `deploy/test/docker-compose.infra.yml` - Redis 端口环境变量
- `deploy/test-env/docker-compose.yml` - MySQL/Redis/MinIO 端口环境变量
- `deploy/test-env/.env` - 添加端口配置说明
- `.env.example` - 更新端口配置说明

### 使用方法
```bash
# 使用默认非标准端口
./scripts/infra.sh start

# 使用自定义端口
ODS_MYSQL_PORT=23306 ODS_REDIS_PORT=26379 ./scripts/infra.sh start

# 使用标准端口（如果不冲突）
ODS_MYSQL_PORT=3306 ODS_REDIS_PORT=6379 ./scripts/infra.sh start

# 测试环境使用 .env 文件配置
cd deploy/test-env
echo "MYSQL_PORT=13306" >> .env
echo "REDIS_PORT=16379" >> .env
docker compose up -d
```

### 配置说明
- **容器间通信**: Docker 网络内部仍使用标准端口（ods-mysql:3306）
- **主机访问**: 通过非标准端口从主机访问（localhost:13306）
- **本地开发**: 微服务本地运行时使用 `MYSQL_PORT` 环境变量
- **环境变量优先级**: 环境变量 > .env 文件 > 默认值

### 验证结果
```bash
# 所有配置文件语法检查通过
bash -n scripts/infra.sh                    # OK
bash -n scripts/test-phased.sh              # OK
docker compose -f deploy/test/docker-compose.infra.yml config     # OK
docker compose -f deploy/test-env/docker-compose.yml config       # OK
docker compose -f services/docker-compose.yml config              # OK
```

---

## 修复概述

本次修复针对 `scripts/test-phased.sh` 脚本中的三个主要问题：

1. **Python 测试结果显示错误** - 跳过时显示"通过"而非"- 跳过"
2. **缺少服务健康检查** - 仅依赖固定等待时间，不验证服务真正就绪
3. **缺少详细输出选项** - 无法查看测试执行详情

---

## Phase 1: 修复 record_result 函数

### 问题
当 Python 测试跳过时，结果显示为"✓ 通过"而非"- 跳过"。

### 修复
```bash
# 修改前
if [[ -n "$py_result" ]]; then
    echo "- Python 测试: $([[ $py_result -eq 0 ]] && echo '✓ 通过' || echo '✗ 失败' || echo '- 跳过')"
fi

# 修改后
if [[ -z "$py_result" ]]; then
    echo "- Python 测试: - 跳过"
else
    echo "- Python 测试: $([[ $py_result -eq 0 ]] && echo '✓ 通过' || echo '✗ 失败')"
fi
```

### 相关文件
- `scripts/test-phased.sh:324-343` (record_result 函数)
- `scripts/test-phased.sh:417-438` (run_phase_tests 函数 - py_result 初始化为空字符串)

---

## Phase 2: 增强服务启动检查

### 新增函数

#### 1. check_service_ready
检查 HTTP 服务是否就绪：
```bash
check_service_ready() {
    local url=$1
    local timeout=${2:-60}
    local elapsed=0

    while [[ $elapsed -lt $timeout ]]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    return 1
}
```

#### 2. check_container_running
检查 Docker 容器是否运行：
```bash
check_container_running() {
    local container_name=$1
    if docker ps --format '{{.Names}}' | grep -q "$container_name"; then
        return 0
    fi
    return 1
}
```

#### 3. check_port_listening
检查端口是否监听：
```bash
check_port_listening() {
    local port=$1
    if lsof -i ":$port" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}
```

#### 4. wait_phase_services_ready
等待阶段所需服务就绪：
- 阶段 0: 检查 MySQL/Redis/MinIO 容器
- 阶段 1: 检查 Portal /health 端点
- 阶段 2: 检查 OpenMetadata API
- 阶段 3: 检查 ETL 平台（至少一个服务）
- 阶段 4-6: 检查对应微服务

#### 5. show_service_health_summary
显示服务健康状态摘要（verbose 模式）：
```
=== 阶段 0 服务健康状态 ===
基础设施:
  ✓ ods-mysql
  ✓ ods-redis
  ✗ ods-minio (未运行)
...
```

### 相关文件
- `scripts/test-phased.sh:72-179` (新增健康检查函数)
- `scripts/test-phased.sh:280-304` (修改 start_phase_services)
- `scripts/test-phased.sh:324-340` (新增 show_service_health_summary)

---

## Phase 3: 添加详细输出选项

### 新增选项
```bash
--verbose, -v    # 显示详细测试输出
```

### 详细输出内容包括
1. 服务健康检查过程
2. 测试用例详细输出（pytest -v）
3. 服务健康状态摘要
4. Bash 测试完整输出

### 相关文件
- `scripts/test-phased.sh:12` (VERBOSE_OUTPUT 配置)
- `scripts/test-phased.sh:455-540` (main 函数参数解析)
- `scripts/test-phased.sh:459-461` (帮助文本)

---

## 验证方法

### 1. 语法检查
```bash
bash -n scripts/test-phased.sh
# 输出: Syntax OK
```

### 2. 帮助输出
```bash
./scripts/test-phased.sh --help
```

### 3. 单阶段测试（带详细输出）
```bash
# 测试阶段 0（基础设施）
./scripts/test-phased.sh 0 --verbose

# 测试阶段 1（系统基础）
./scripts/test-phased.sh 1 -v --show-errors
```

### 4. 验证进度文件格式
```bash
./scripts/test-phased.sh 0
cat docs/progress/phased-testing-*.md
# 应该看到:
# - Python 测试: - 跳过
```

---

## 测试脚本状态

| 功能 | 状态 | 说明 |
|------|------|------|
| record_result 修复 | ✅ 完成 | Python 测试跳过时正确显示 |
| 服务健康检查 | ✅ 完成 | 5 个新函数 |
| verbose 选项 | ✅ 完成 | 支持详细输出 |
| 语法检查 | ✅ 通过 | bash -n 验证 |
| 帮助输出 | ✅ 正常 | --help 选项工作 |

---

## 下一步

脚本修复已完成。如需实际运行测试，请确保：

1. Docker 服务运行
2. 基础设施容器可正常启动
3. 微服务配置正确

使用以下命令开始测试：
```bash
# 仅测试基础设施
./scripts/test-phased.sh 0 --verbose

# 完整测试流程
./scripts/test-phased.sh --auto-continue
```
