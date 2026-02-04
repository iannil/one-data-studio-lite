# LLM 项目索引 (LLM-INDEX)

**目的**: 专门为 AI/LLM 优化的项目索引，帮助大模型快速理解和操作本项目。

**更新日期**: 2026-02-04

---

## 快速导航

### 给 LLM 的提示

当你需要操作此项目时，请按以下优先级阅读：

1. **快速理解** → 阅读 `PROJECT-SUMMARY.md`
2. **运维操作** → 阅读 `RUNBOOK.md` 和 `SCRIPTS.md`
3. **开发任务** → 阅读 `development.md` 和 `standards/` 目录
4. **API 接口** → 阅读 `api/services.md`
5. **测试相关** → 阅读 `standards/e2e-test-guide.md`

### 文档映射表

| 需求 | 阅读文档 | 优先级 |
|------|----------|--------|
| 项目整体理解 | `PROJECT-SUMMARY.md` | ⭐⭐⭐⭐⭐ |
| 快速启动项目 | `QUICK-START.md` | ⭐⭐⭐⭐⭐ |
| 运维操作 | `RUNBOOK.md` | ⭐⭐⭐⭐ |
| 脚本命令 | `SCRIPTS.md` | ⭐⭐⭐⭐ |
| 系统架构 | `architecture.md` | ⭐⭐⭐⭐ |
| 开发规范 | `standards/` | ⭐⭐⭐⭐ |
| 测试规范 | `standards/e2e-test-guide.md` | ⭐⭐⭐⭐ |
| API 文档 | `api/services.md` | ⭐⭐⭐ |
| 技术栈 | `tech-stack.md` | ⭐⭐⭐ |

---

## 服务架构

### 服务端口清单

```
┌────────────────────────────────────────────────────────────┐
│  服务名称        │ 端口  │ 健康检查    │ 状态  │ 用途     │
├────────────────────────────────────────────────────────────┤
│  portal          │ 8010  │ /health     │ ✅    │ 统一门户 │
│  nl2sql          │ 8011  │ /health     │ ✅    │ NL2SQL   │
│  ai_cleaning     │ 8012  │ /health     │ ✅    │ AI清洗   │
│  metadata_sync   │ 8013  │ /health     │ ✅    │ 元数据   │
│  data_api        │ 8014  │ /health     │ ✅    │ 数据API  │
│  sensitive_detect│ 8015  │ /health     │ ✅    │ 敏感数据 │
│  audit_log       │ 8016  │ /health     │ ✅    │ 审计日志 │
├────────────────────────────────────────────────────────────┤
│  web (前端)      │ 5173  │ -           │ ✅    │ React应用 │
├────────────────────────────────────────────────────────────┤
│  MySQL           │ 3306  │ -           │ ✅    │ 数据库   │
│  Redis           │ 6379  │ -           │ ✅    │ 缓存     │
│  MinIO           │ 9000  │ -           │ ✅    │ 对象存储 │
└────────────────────────────────────────────────────────────┘
```

### 服务依赖图

```
用户请求
    ↓
Portal (8010) - JWT验证
    ↓
┌───────────┬───────────┬───────────┬───────────┐
↓           ↓           ↓           ↓           ↓
nl2sql    ai_cleaning  metadata_sync  data_api  sensitive_detect
(8011)    (8012)      (8013)      (8014)      (8015)
    ↓           ↓           ↓           ↓           ↓
└───────────┴───────────┴───────────┴───────────┘
                    ↓
          common/ (共享库)
                    ↓
          MySQL, Redis, MinIO
                    ↓
  外部组件 (OpenMetadata, Superset, Hop, SeaTunnel, DS)
```

### 关键代码位置

| 功能 | 文件路径 | 说明 |
|------|----------|------|
| 服务入口 | `services/portal/main.py` | 统一门户入口 |
| JWT认证 | `services/common/auth.py` | Token验证逻辑 |
| 数据库 | `services/common/database.py` | 数据库连接 |
| API响应 | `services/common/api_response.py` | 统一响应格式 |
| 前端入口 | `web/src/main.tsx` | React入口 |
| 运维脚本 | `scripts/lib/common.sh` | 公共函数库 |

---

## 常用命令速查

### 启动停止

```bash
# 统一入口
./ods.sh start all              # 启动所有
./ods.sh stop all               # 停止所有
./ods.sh status all             # 查看状态

# 分层启动
./ods.sh start infra            # 基础设施
./ods.sh start platforms        # 平台服务
./ods.sh start services         # 微服务
./ods.sh start web              # 前端

# Make 命令
make start / make stop          # 启动/停止所有
make health                     # 健康检查
```

### 测试命令

```bash
# 全量测试
make test

# 分阶段测试
./scripts/test-phased.sh 0      # 阶段0: 基础设施
./scripts/test-phased.sh 1      # 阶段1: 数据规划
./scripts/test-phased.sh 2      # 阶段2: 数据感知
./scripts/test-phased.sh 3      # 阶段3: 数据加工
./scripts/test-phased.sh 4      # 阶段4: 数据分析
./scripts/test-phased.sh 5      # 阶段5: 数据资产
./scripts/test-phased.sh 6      # 阶段6: 数据安全

# 故障排查
./scripts/test-phased.sh --auto-port         # 自动端口
./scripts/test-phased.sh --skip-memory-check # 跳过内存检查
./scripts/test-phased.sh --diagnose          # 诊断模式
```

### 前端命令

```bash
cd web
npm run dev                    # 开发服务器
npm run build                  # 生产构建
npm run e2e                    # E2E测试
npm run e2e:ui                 # E2E UI模式
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

## 测试规范

### 测试分层

```
E2E测试 (Playwright)
    ↓
集成测试 (pytest + fixtures)
    ↓
单元测试 (pytest)
```

### 测试覆盖

- **代码覆盖率**: 87%
- **P0用例**: 213/213 (100%)
- **前端页面**: 85个

### 测试文件位置

| 类型 | 路径 |
|------|------|
| E2E测试 | `tests/e2e/` |
| 角色测试 | `tests/test_super_admin/`, `tests/test_admin/`, 等 |
| 通用测试 | `tests/test_common/` |
| 跨角色测试 | `tests/test_cross_role/` |

---

## 前端结构

### 页面组织

```
web/src/pages/
├── Planning/        (5页面) - 数据规划与元数据
├── Assets/          (4页面) - 数据资产
├── Collection/      (4页面) - 数据采集
├── Analysis/        (6页面) - 数据分析
├── Development/     (7页面) - 数据开发
├── Security/        (3页面) - 数据安全
└── Operations/      (5页面) - 运维管理
                    ───────
                    总计: 34个主页面, 85个组件
```

### 关键前端文件

| 文件 | 说明 |
|------|------|
| `web/src/api/` | API调用封装 |
| `web/src/store/` | 状态管理 |
| `web/src/pages/` | 页面组件 |
| `web/src/router/` | 路由配置 |
| `web/src/utils/` | 工具函数 |

---

## 开发规范

### 代码风格

- **Python**: 遵循 PEP 8
- **TypeScript**: 遵循 ESLint 配置
- **提交信息**: Conventional Commits 格式

### 文档规范

- 中文文档，英文代码
- 进度文档: `docs/progress/`
- 完成报告: `docs/reports/completed/`
- 标准文档: `docs/standards/`
- 模板: `docs/templates/`

### 命名规范

```python
# Python
class UserService:          # 大驼峰
def get_user():            # 小写+下划线
USER_ID = "xxx"            # 常量大写
```

```typescript
// TypeScript
class UserService { }      // 大驼峰
function getUser() { }     // 小驼峰
const userId = "xxx"       // 小驼峰
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
- ✅ 端口冲突问题解决

---

## 外部组件集成

| 组件 | 用途 | 部署位置 | 访问地址 |
|------|------|----------|----------|
| OpenMetadata | 元数据管理 | `deploy/openmetadata/` | :8585 |
| Apache Superset | BI可视化 | `deploy/superset/` | :8088 |
| Apache Hop | ETL引擎 | `deploy/hop/` | :8080 |
| Apache SeaTunnel | 数据同步 | `deploy/seatunnel/` | :58080 |
| DolphinScheduler | 任务调度 | `deploy/dolphinscheduler/` | :12345 |

---

## 项目统计

### 代码量

- **Python服务**: 7个微服务 + 1个共享库
- **前端**: 85个TSX文件
- **测试**: 132个测试文件
- **测试覆盖率**: 87%

### 文档量

- **Markdown文档**: 90+ 个
- **标准文档**: 8 个
- **测试用例文档**: 10 个
- **模板文档**: 5 个

---

## 相关文档链接

| 文档 | 路径 |
|------|------|
| 项目概览 | `PROJECT-SUMMARY.md` |
| 快速开始 | `QUICK-START.md` |
| 系统架构 | `architecture.md` |
| 部署指南 | `deployment.md` |
| 开发指南 | `development.md` |
| 运维手册 | `RUNBOOK.md` |
| 脚本参考 | `SCRIPTS.md` |
| 参考手册 | `REFERENCE.md` |
| 文档状态 | `STATUS.md` |
| 项目进度 | `progress.md` |
| 技术债务 | `technical-debt.md` |
| 贡献指南 | `CONTRIB.md` |
| 变更日志 | `changelog.md` |

---

**注意**: 本文档专为 LLM 理解项目而设计，内容保持简洁和高可读性。如需详细信息，请参考对应的完整文档。
