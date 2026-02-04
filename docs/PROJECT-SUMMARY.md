# ONE-DATA-STUDIO-LITE 项目概览

> **给AI/LLM的提示**: 本文档是为大模型优化的项目索引。
> 阅读本文档后，你应该能够：
> 1. 快速定位关键代码位置
> 2. 理解服务间依赖关系
> 3. 执行常用运维命令
> 4. 定位和修复常见问题

**更新日期**: 2026-02-04
**项目完成度**: 95-100%

---

## 快速索引 (LLM专用)

### 关键文件位置

| 类型 | 路径 | 说明 |
|------|------|------|
| 服务入口 | `services/portal/main.py` | 统一门户 (40KB) |
| 共享库 | `services/common/` | 公共模块 |
| 认证模块 | `services/common/auth.py` | JWT认证 |
| 数据库 | `services/common/database.py` | 数据库连接 |
| API响应 | `services/common/api_response.py` | 统一响应格式 |
| 前端 | `web/src/` | React前端 |
| 运维脚本 | `scripts/` | 运维脚本集合 |
| 部署配置 | `deploy/` | Docker/K8s配置 |
| 测试 | `tests/` | 集成测试 |

### 服务端口清单

| 服务 | 端口 | 健康检查 | 状态 |
|------|------|----------|------|
| portal | 8010 | `/health` | ✅ |
| nl2sql | 8011 | `/health` | ✅ |
| ai_cleaning | 8012 | `/health` | ✅ |
| metadata_sync | 8013 | `/health` | ✅ |
| data_api | 8014 | `/health` | ✅ |
| sensitive_detect | 8015 | `/health` | ✅ |
| audit_log | 8016 | `/health` | ✅ |
| web (frontend) | 5173 | - | ✅ |
| MySQL | 3306 | - | ✅ |
| Redis | 6379 | - | ✅ |
| MinIO | 9000 | - | ✅ |

### 服务依赖关系

```
用户请求
    ↓
Portal (8010) - JWT验证
    ↓
┌───────────┬───────────┬───────────┐
↓           ↓           ↓           ↓
nl2sql    ai_cleaning  metadata_sync  data_api
(8011)    (8012)      (8013)      (8014)
    ↓           ↓           ↓           ↓
└───────────┴───────────┴───────────┘
                    ↓
          common/ (共享库)
                    ↓
          MySQL, Redis, MinIO
                    ↓
          外部组件 (OpenMetadata, Superset, etc.)
```

### 外部组件集成

| 组件 | 用途 | 类型 | 部署位置 |
|------|------|------|---------|
| OpenMetadata | 元数据管理 | 外部 | `deploy/openmetadata/` |
| Apache Superset | BI可视化 | 外部 | `deploy/superset/` |
| Apache Hop | ETL引擎 | 外部 | `deploy/hop/` |
| Apache SeaTunnel | 数据同步 | 外部 | `deploy/seatunnel/` |
| DolphinScheduler | 任务调度 | 外部 | `deploy/dolphinscheduler/` |

---

## 测试命令

### 全量测试
```bash
make test
# 或
./scripts/test-lifecycle.sh
```

### 分阶段测试
```bash
# 阶段0: 基础设施
./scripts/test-phased.sh 0

# 阶段1: 数据规划
./scripts/test-phased.sh 1

# 阶段2: 数据感知
./scripts/test-phased.sh 2

# 阶段3: 数据加工
./scripts/test-phased.sh 3

# 阶段4: 数据分析
./scripts/test-phased.sh 4

# 阶段5: 数据资产
./scripts/test-phased.sh 5

# 阶段6: 数据安全
./scripts/test-phased.sh 6
```

### 单个服务测试
```bash
# Portal服务
pytest tests/test_portal/

# 通用模块测试
pytest services/common/tests/
```

### 测试故障排查
```bash
# 自动分配端口
./scripts/test-phased.sh --auto-port

# 跳过内存检查
./scripts/test-phased.sh --skip-memory-check

# 诊断模式
./scripts/test-phased.sh --diagnose
```

---

## 常用运维命令

### 统一入口 (ods.sh)
```bash
./ods.sh start all              # 启动所有服务
./ods.sh stop all               # 停止所有服务
./ods.sh status all             # 查看所有服务状态
./ods.sh health all             # 健康检查
./ods.sh info                   # 显示访问地址
```

### 分层启动
```bash
./ods.sh start infra            # 启动基础设施 (MySQL, Redis, MinIO)
./ods.sh start platforms        # 启动平台服务 (OpenMetadata, Superset等)
./ods.sh start services         # 启动微服务
./ods.sh start web              # 启动前端
```

### 初始化
```bash
./ods.sh init-data seed         # 初始化种子数据
./ods.sh init-data verify       # 验证数据完整性
```

### Make命令
```bash
make start                      # 启动所有服务
make stop                       # 停止所有服务
make status                     # 查看服务状态
make health                     # 健康检查
make test                       # 运行所有测试
```

---

## 故障排查

### 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8010

# 或使用测试脚本的自动端口功能
./scripts/test-phased.sh --auto-port
```

### Docker网络问题
```bash
# 检查Docker网络
docker network ls
docker network inspect ods-network

# 重建网络
./scripts/infra.sh down
./scripts/infra.sh up
```

### 内存不足
```bash
# 跳过内存检查运行测试
./scripts/test-phased.sh --skip-memory-check

# 查看Docker资源使用
docker stats
```

### 服务无法启动
```bash
# 查看服务日志
docker-compose -f services/docker-compose.yml logs [service_name]

# 检查健康状态
curl http://localhost:8010/health
```

### 数据库连接问题
```bash
# 检查MySQL状态
docker-compose -f services/docker-compose.yml ps mysql

# 进入MySQL容器
docker-compose -f services/docker-compose.yml exec mysql bash
```

---

## 技术债务

### 高优先级
- **Token黑名单**: 未实现 → `services/common/auth.py:167`
- **配置文件重复**: 各服务 `config.py` 存在重复配置

### 中优先级
- 错误处理模式不统一
- 日志级别不规范
- Prometheus未部署
- 告警通知未配置

### 已解决 (2026-02-03 ~ 2026-02-04)
- ✅ Docker网络健康检查
- ✅ 运维脚本重构
- ✅ 测试脚本内存计算Bug修复

---

## 项目统计

### 代码量
- **Python服务**: 7个微服务 + 1个共享库
- **前端**: 85个TSX文件
- **测试**: 132个测试文件
- **测试覆盖率**: 87%

### E2E测试
- **P0用例**: 213/213 (100%)
- **前端页面**: 85个主要功能页面

---

## 开发规范

### 代码风格
- Python: 遵循PEP 8
- TypeScript: 遵循ESLint配置
- 提交信息: Conventional Commits格式

### 文档规范
- 中文文档，英文代码
- 进度文档: `docs/progress/`
- 完成报告: `docs/reports/completed/`
- 模板: `docs/templates/`

### 测试规范
- TDD: 先写测试，后实现
- 覆盖率要求: 80%+
- 单元测试 + 集成测试 + E2E测试

---

## 访问地址

| 服务 | 本地地址 |
|------|---------|
| Portal API | http://localhost:8010 |
| Web前端 | http://localhost:5173 |
| OpenMetadata | http://localhost:8585 |
| Superset | http://localhost:8088 |
| Hop | http://localhost:8080 |
| DolphinScheduler | http://localhost:12345 |
| Grafana | http://localhost:3000 |

---

## 相关文档

| 文档 | 路径 |
|------|------|
| 快速开始 | `docs/QUICK-START.md` |
| 系统架构 | `docs/architecture.md` |
| 部署指南 | `docs/deployment.md` |
| 开发指南 | `docs/development.md` |
| 运维手册 | `docs/RUNBOOK.md` |
| 参考手册 | `docs/REFERENCE.md` |
| 项目状态 | `docs/STATUS.md` |
| 技术债务 | `docs/technical-debt.md` |
| 贡献指南 | `docs/CONTRIB.md` |
| 文档模板 | `docs/templates/` |
