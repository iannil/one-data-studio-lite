# ONE-DATA-STUDIO-LITE 模块化运维指南

本文档描述 ONE-DATA-STUDIO-LITE 的模块化划分和运维方法。

## 目录

- [模块概览](#模块概览)
- [模块详细说明](#模块详细说明)
- [快速开始](#快速开始)
- [运维脚本](#运维脚本)
- [测试验证](#测试验证)
- [常见场景](#常见场景)

---

## 模块概览

| 模块 | 名称 | 内存 | 端口 | 依赖 |
|------|------|------|------|------|
| **base** | 基础平台 | ~4 GB | 8010, 8016, 3306, 6379 | 无 |
| **metadata** | 元数据管理 | ~6 GB | 8585, 8586, 9201 | base |
| **integration** | 数据集成 | ~8 GB | 5802, 12345, 2181 | base |
| **processing** | 数据加工 | ~6 GB | 8083, 8012 | base |
| **bi** | BI 分析 | ~8 GB | 8088, 8011 | base |
| **security** | 数据安全 | ~5 GB | 8015 | base |

---

## 模块详细说明

### 模块 1: 基础平台 (base)

**业务价值**: 用户认证、权限控制、审计日志（所有模块的基础）

**核心组件**:
- Portal (8010) - 统一门户、认证、用户/角色管理
- Audit Log (8016) - 审计日志服务
- MySQL (3306) - 用户、权限、日志数据
- Redis (6379) - 会话、缓存

**完整功能流程**:
```
用户登录 → 权限验证 → 操作执行 → 审计记录 → 日志查询
```

**访问地址**:
- Portal: http://localhost:8010
- Audit Log: http://localhost:8016

---

### 模块 2: 元数据管理 (metadata)

**业务价值**: 数据资产目录、血缘追踪、元数据同步

**核心组件**:
- OpenMetadata (8585/8586) - 元数据平台
- Metadata Sync (8013) - 元数据同步服务
- MySQL (3308) - 元数据存储
- Elasticsearch (9201) - 元数据搜索

**完整功能流程**:
```
连接数据源 → 采集元数据 → 构建血缘 → 资产目录 → 变更同步 → ETL联动
```

**访问地址**:
- OpenMetadata: http://localhost:8585 (admin/admin)
- Metadata Sync: http://localhost:8013

---

### 模块 3: 数据集成 (integration)

**业务价值**: 数据采集、CDC 同步、任务调度

**核心组件**:
- SeaTunnel (5802) - 数据同步引擎
- DolphinScheduler (12345) - 调度平台
- Zookeeper (2181) - 协调服务
- PostgreSQL (5432) - DS 数据库

**完整功能流程**:
```
配置数据源 → 设计同步任务 → 调度执行 → 监控状态 → 失败重试 → 完成通知
```

**访问地址**:
- SeaTunnel: http://localhost:5802
- DolphinScheduler: http://localhost:12345 (admin/dolphinscheduler123)

---

### 模块 4: 数据加工 (processing)

**业务价值**: ETL 流程设计、数据清洗、质量检测

**核心组件**:
- Apache Hop (8083) - ETL 引擎
- AI Cleaning (8012) - 清洗规则推荐

**完整功能流程**:
```
数据源接入 → 设计ETL流程 → AI推荐清洗规则 → 执行转换 → 质量检测 → 输出目标
```

**访问地址**:
- Hop: http://localhost:8083
- AI Cleaning: http://localhost:8012

---

### 模块 5: BI 分析 (bi)

**业务价值**: 可视化报表、自助分析、自然语言查询

**核心组件**:
- Apache Superset (8088) - BI 平台
- NL2SQL (8011) - 自然语言转 SQL
- PostgreSQL (5432) - Superset 数据库
- Redis (6379) - 缓存

**完整功能流程**:
```
连接数据源 → 创建数据集 → 设计图表 → 构建仪表盘 → 自然语言查询 → 分享报表
```

**访问地址**:
- Superset: http://localhost:8088 (admin/admin123)
- NL2SQL: http://localhost:8011

---

### 模块 6: 数据安全 (security)

**业务价值**: 敏感数据扫描、自动脱敏、访问审计

**核心组件**:
- Sensitive Detect (8015) - 敏感数据检测
- ShardingSphere (可选) - 数据脱敏
- LLM/Ollama (31434) - 智能分类

**完整功能流程**:
```
配置扫描规则 → 扫描数据表 → LLM智能分类 → 生成脱敏规则 → 应用脱敏 → 访问审计
```

**访问地址**:
- Sensitive Detect: http://localhost:8015

---

## 快速开始

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/your-org/one-data-studio-lite.git
cd one-data-studio-lite

# 安装 Python 依赖
pip install -r services/requirements.txt

# 安装前端依赖
cd web && npm install && cd ..
```

### 启动第一个模块

```bash
# 启动基础平台（最小配置）
./scripts/modules.sh start base

# 查看状态
./scripts/modules.sh status

# 快速验证
./scripts/test-modules.sh verify base
```

---

## 运维脚本

### modules.sh - 模块启动脚本

```bash
# 启动模块
./scripts/modules.sh start <module>

# 停止模块
./scripts/modules.sh stop <module>

# 重启模块
./scripts/modules.sh restart <module>

# 查看状态
./scripts/modules.sh status [module]

# 健康检查
./scripts/modules.sh health [module]

# 列出所有模块
./scripts/modules.sh list
```

### 本地模式（开发调试）

```bash
# 使用本地模式启动微服务（支持热重载）
./scripts/modules.sh start base --local

# 本地运行单个服务
make dev-portal
make dev-nl2sql
make dev-cleaning
```

---

## 测试验证

### test-modules.sh - 测试脚本

```bash
# 运行模块测试
./scripts/test-modules.sh test <module>

# 快速验证
./scripts/test-modules.sh verify <module>

# 完整测试（单元+集成）
./scripts/test-modules.sh test <module> --full

# 等待模块就绪后测试
./scripts/test-modules.sh test <module> --wait

# 测试所有模块
./scripts/test-modules.sh test all

# 列出测试配置
./scripts/test-modules.sh list
```

### 测试文件映射

| 模块 | 单元测试 | 集成测试 |
|------|----------|----------|
| base | test_01_auth_init.py<br>test_02_user_management.py<br>test_03_role_management.py<br>test_06_audit_logging.py | test_e2e_01_user_lifecycle.py |
| metadata | test_08_metadata_sync.py | test_metadata_management.py |
| integration | test_09_seatunnel_pipelines.py<br>test_11_dolphinscheduler.py | test_e2e_03_data_pipeline_flow.py |
| processing | test_10_hop_etl.py<br>test_17_ai_cleaning.py | test_cleaning_rules.py<br>test_data_quality.py |
| bi | test_15_superset.py<br>test_16_nl2sql.py | test_nl2sql.py<br>test_data_explore.py |
| security | test_13_sensitive_detect.py | test_sensitive_scan.py<br>test_detection_rules.py |

---

## 常见场景

### 场景 1: 前端开发（最小配置）

```bash
# 启动基础平台
./scripts/modules.sh start base --local

# 启动前端
make web-dev

# 内存需求: ~6 GB
```

### 场景 2: 后端 API 开发

```bash
# 启动基础平台
./scripts/modules.sh start base --local

# 本地运行需要开发的服务
make dev-portal
make dev-nl2sql

# 内存需求: ~4 GB
```

### 场景 3: 元数据工程师

```bash
# 启动元数据管理模块
./scripts/modules.sh start metadata

# 运行测试
./scripts/test-modules.sh test metadata

# 内存需求: ~10 GB
```

### 场景 4: 数据工程师

```bash
# 启动数据集成和加工模块
./scripts/modules.sh start integration
./scripts/modules.sh start processing

# 内存需求: ~14 GB
```

### 场景 5: BI 开发

```bash
# 启动 BI 分析模块
./scripts/modules.sh start bi

# 内存需求: ~12 GB
```

### 场景 6: 安全开发

```bash
# 启动数据安全模块
./scripts/modules.sh start security

# 内存需求: ~10 GB
```

### 场景 7: 全栈开发

```bash
# 启动所有模块
./scripts/modules.sh start all

# 内存需求: ~32 GB
```

---

## 模块依赖图

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

---

## 故障排查

### 模块启动失败

1. 检查端口占用
   ```bash
   lsof -i :8010  # 检查 Portal 端口
   ```

2. 查看日志
   ```bash
   # 本地模式
   tail -f logs/portal.log

   # 容器模式
   docker logs ods-portal
   ```

3. 检查健康状态
   ```bash
   ./scripts/modules.sh health <module>
   ```

### 测试失败

1. 确认模块已启动
   ```bash
   ./scripts/modules.sh status
   ```

2. 运行单个测试文件
   ```bash
   pytest tests/test_lifecycle/test_01_auth_init.py -v
   ```

3. 查看详细错误
   ```bash
   pytest tests/test_lifecycle/test_01_auth_init.py -vv --tb=long
   ```

---

## 更多信息

- 项目 README: [README.md](../../README.md)
- 开发指南: [CLAUDE.md](../../CLAUDE.md)
- 测试文档: [docs/testing/](../testing/)
