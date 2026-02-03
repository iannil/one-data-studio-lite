# 贡献者指南 (CONTRIBUTING)

**更新日期**: 2026-02-03
**版本**: 1.1

本文档为 ONE-DATA-STUDIO-LITE 项目的开发者提供开发工作流程、可用脚本、环境配置和测试程序的完整参考。

---

## 目录

1. [开发工作流程](#开发工作流程)
2. [环境配置](#环境配置)
3. [可用脚本](#可用脚本)
4. [测试程序](#测试程序)
5. [代码规范](#代码规范)
6. [提交规范](#提交规范)

---

## 开发工作流程

### 标准开发流程

```mermaid
graph TD
    A[创建功能分支] --> B[本地开发]
    B --> C[编写测试]
    C --> D[本地测试通过]
    D --> E[提交代码]
    E --> F[创建 Pull Request]
    F --> G[代码审查]
    G --> H[合并到主分支]
```

### 分支策略

| 分支类型 | 命名规范 | 用途 | 生命周期 |
|---------|---------|------|---------|
| `master` | - | 主分支，生产代码 | 长期 |
| `develop` | - | 开发分支（可选） | 长期 |
| `feature/*` | `feature/功能名称` | 新功能开发 | 临时 |
| `bugfix/*` | `bugfix/问题描述` | Bug 修复 | 临时 |
| `hotfix/*` | `hotfix/紧急问题` | 生产环境紧急修复 | 临时 |
| `docs/*` | `docs/文档内容` | 文档更新 | 临时 |

### 开发步骤

1. **创建功能分支**
   ```bash
   git checkout -b feature/add-new-endpoint
   ```

2. **本地开发与测试**
   ```bash
   # 启动依赖服务
   make network

   # 启动需要的子系统
   make datahub-up
   make superset-up

   # 本地开发运行
   make dev-portal  # 或其他服务
   ```

3. **编写并运行测试**
   ```bash
   # 单元测试
   make test-unit

   # E2E 测试
   make test-e2e
   ```

4. **代码检查**
   ```bash
   # 前端代码检查
   cd web && npm run lint

   # 格式化代码
   cd web && npm run lint:fix
   ```

5. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add new endpoint for data export"
   git push origin feature/add-new-endpoint
   ```

---

## 环境配置

### 系统要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.11 | 3.11+ |
| Node.js | 18.x | 20.x LTS |
| Docker | 24.0+ | 最新稳定版 |
| Make | 任意 | - |

### 初始化开发环境

```bash
# 1. 克隆项目
git clone <repo-url>
cd one-data-studio-lite

# 2. 创建 Python 虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 3. 安装 Python 依赖
make dev-install
# 或
pip install -r services/requirements.txt

# 4. 安装前端依赖
make web-install
# 或
cd web && npm install

# 5. 配置环境变量
cp .env.example .env
cp services/.env.example services/.env
# 编辑 .env 文件，设置必要的配置

# 6. 创建 Docker 网络
make network
```

### 环境变量说明

完整的环境变量配置请参考项目根目录下的 `.env.example` 文件。

#### 通用配置 (必须设置)

| 变量名 | 说明 | 示例值 |
|-------|------|--------|
| `DATABASE_URL` | 数据库连接字符串 | `mysql+aiomysql://root:password@localhost:3306/one_data_studio` |
| `MYSQL_PASSWORD` | MySQL 密码 | `your_secure_password` |
| `MYSQL_HOST` | MySQL 主机 | `localhost` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_DATABASE` | MySQL 数据库名 | `one_data_warehouse` |
| `MYSQL_USERNAME` | MySQL 用户名 | `root` |
| `JWT_SECRET` | JWT 签名密钥 (至少32字符) | 随机安全字符串 |

#### 子系统地址

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `CUBE_STUDIO_URL` | Cube-Studio 地址 | `http://localhost:30080` |
| `SUPERSET_URL` | Superset 地址 | `http://localhost:8088` |
| `SUPERSET_SECRET_KEY` | Superset 密钥 | 需修改生产密钥 |
| `SUPERSET_DATABASE_URI` | Superset 数据库连接 | `mysql+pymysql://root:pass@localhost:3306/superset` |
| `SUPERSET_ADMIN_PASSWORD` | Superset 管理员密码 | `changeme` |
| `DATAHUB_GMS_URL` | DataHub GMS API | `http://localhost:8081` |
| `DATAHUB_TOKEN` | DataHub Token | 需修改生产 Token |
| `DOLPHINSCHEDULER_API_URL` | DolphinScheduler API | `http://localhost:12345/dolphinscheduler` |
| `DOLPHINSCHEDULER_TOKEN` | DolphinScheduler Token | 需修改生产 Token |
| `SEATUNNEL_API_URL` | SeaTunnel API | `http://localhost:5801` |

#### 邮件服务配置 (SMTP)

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

#### LLM 配置

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `LLM_BASE_URL` | LLM 服务地址 | `http://localhost:31434` |
| `LLM_MODEL` | LLM 模型名称 | `qwen2.5:7b` |
| `LLM_TEMPERATURE` | LLM 温度参数 | `0.1` |
| `LLM_MAX_TOKENS` | LLM 最大 Token 数 | `2048` |

#### 审计日志

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `AUDIT_LOG_URL` | 审计日志服务 | `http://localhost:8016/api/audit/log` |
| `AUDIT_LOG_RETENTION_DAYS` | 日志保留天数 | `90` |

#### 各服务独立配置

各服务可以通过特定环境变量覆盖默认配置：

| 服务 | 端口变量 | 数据库变量 |
|------|---------|----------|
| Portal | `PORTAL_APP_PORT=8010` | `PORTAL_DATABASE_URL` |
| NL2SQL | `NL2SQL_APP_PORT=8011` | `NL2SQL_DATABASE_URL` |
| AI Cleaning | `AI_CLEAN_APP_PORT=8012` | `AI_CLEAN_DATABASE_URL` |
| Metadata Sync | `META_SYNC_APP_PORT=8013` | `META_SYNC_DATABASE_URL` |
| Data API | `DATA_API_APP_PORT=8014` | `DATA_API_DATABASE_URL` |
| Sensitive Detect | `SENSITIVE_APP_PORT=8015` | `SENSITIVE_DATABASE_URL` |
| Audit Log | `AUDIT_APP_PORT=8016` | `AUDIT_DATABASE_URL` |

---

## 可用脚本

### 统一运维入口 (ods.sh)

`ods.sh` 是项目的统一运维入口脚本，支持所有服务的管理操作。

#### 启动服务

| 命令 | 说明 |
|------|------|
| `./ods.sh start all` | 启动所有服务 |
| `./ods.sh start infra` | 启动基础设施 (MySQL, Redis, MinIO, etcd) |
| `./ods.sh start platforms` | 启动第三方平台 (OpenMetadata, Superset等) |
| `./ods.sh start services` | 启动后端微服务 |
| `./ods.sh start web` | 启动前端开发服务器 |

#### 停止服务

| 命令 | 说明 |
|------|------|
| `./ods.sh stop all` | 停止所有服务 |
| `./ods.sh stop infra` | 停止基础设施 |
| `./ods.sh stop platforms` | 停止第三方平台 |
| `./ods.sh stop services` | 停止后端微服务 |
| `./ods.sh stop web` | 停止前端 |

#### 状态与健康检查

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

#### 测试

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
| `make superset-up` | 启动 Superset |
| `make superset-down` | 停止 Superset |
| `make datahub-up` | 启动 DataHub |
| `make datahub-down` | 停止 DataHub |
| `make dolphinscheduler-up` | 启动 DolphinScheduler |
| `make dolphinscheduler-down` | 停止 DolphinScheduler |
| `make seatunnel-up` | 启动 SeaTunnel |
| `make hop-up` | 启动 Apache Hop |
| `make cube-studio-up` | 启动 Cube-Studio |
| `make cube-studio-down` | 停止 Cube-Studio |
| `make cube-studio-logs` | 查看 Cube-Studio 日志 |

#### 配置中心

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
| `make loki-up` | 启动 Loki 日志聚合 |
| `make loki-down` | 停止 Loki 日志聚合 |
| `make loki-logs` | 查看 Loki 日志 |
| `make grafana-up` | 启动 Grafana 监控面板 |
| `make grafana-down` | 停止 Grafana |
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

### Makefile 测试命令

| 命令 | 说明 |
|------|------|
| `make test` | 运行所有测试 |
| `make test-e2e` | 运行 E2E 测试 |
| `make test-unit` | 运行单元测试 |
| `make test-lifecycle` | 运行生命周期测试 |
| `make test-lifecycle-01` | 账户创建阶段测试 |
| `make test-lifecycle-02` | 权限配置阶段测试 |
| `make test-lifecycle-03` | 数据访问阶段测试 |
| `make test-lifecycle-04` | 功能使用阶段测试 |
| `make test-lifecycle-05` | 监控审计阶段测试 |
| `make test-lifecycle-06` | 维护阶段测试 |
| `make test-lifecycle-07` | 账户禁用阶段测试 |
| `make test-lifecycle-08` | 账户删除阶段测试 |
| `make test-lifecycle-09` | 紧急处理阶段测试 |
| `make test-subsystem` | 运行六大子系统测试 |
| `make test-planning` | 数据规划子系统测试 |
| `make test-collection` | 数据汇聚子系统测试 |
| `make test-development` | 数据开发子系统测试 |
| `make test-analysis` | 数据分析子系统测试 |
| `make test-assets` | 数据资产子系统测试 |
| `make test-security` | 数据安全子系统测试 |
| `make test-roles` | 运行角色权限测试 |
| `make test-api` | 运行 API 测试 |
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

---

## 测试程序

### 测试层级

```
测试金字塔
       /\
      /  \      E2E 测试 (少量)
     /----\
    /      \    集成测试 (中等)
   /--------\
  /          \  单元测试 (大量)
 /------------\
```

### 单元测试

#### Python 后端

```bash
# 运行所有单元测试
pytest tests/

# 运行特定模块测试
pytest tests/test_portal.py

# 带覆盖率报告
pytest --cov=services/portal tests/

# 查看详细输出
pytest -v -s
```

#### React 前端

```bash
cd web

# 运行测试
npm run test

# 生成覆盖率
npm run test:coverage

# UI 模式
npm run test:ui
```

### E2E 测试

#### 运行 E2E 测试

```bash
cd web/e2e

# 运行所有测试
npx playwright test

# 指定测试文件
npx playwright test tests/features/auth.spec.ts

# 按标签运行
npx playwright test --grep "@p0"
npx playwright test --grep "@smoke"

# 调试模式
npx playwright test --debug

# UI 模式
npx playwright test --ui
```

#### E2E 测试标签

| 标签 | 说明 | 示例 |
|------|------|------|
| `@smoke` | 冒烟测试，验证基本功能 | 登录、导航 |
| `@p0` | P0 优先级，核心功能 | 用户管理、数据访问 |
| `@p1` | P1 优先级，重要功能 | 报表生成、配置管理 |
| `@planning` | 数据规划子系统 | 元数据浏览、数据源管理 |
| `@collection` | 数据汇聚子系统 | 同步任务、ETL 流程 |
| `@development` | 数据开发子系统 | 清洗规则、数据融合 |
| `@analysis` | 数据分析子系统 | NL2SQL、BI 报表 |
| `@assets` | 数据资产子系统 | 数据 API、资产目录 |
| `@security` | 数据安全子系统 | 敏感数据、权限管理 |
| `@lifecycle` | 用户生命周期测试 | 从创建到删除的完整流程 |
| `@sup` | Superset 相关测试 | BI 报表、仪表盘 |
| `@adm` | 管理功能测试 | 用户管理、租户管理 |
| `@sci` | 数据科学相关测试 | NL2SQL、Pipeline |
| `@ana` | 分析相关测试 | 图表、BI 分析 |
| `@vw` | 查看者权限测试 | 只读访问验证 |

#### 测试用例结构

```typescript
import { test, expect } from '@playwright/test';

test.describe('用户认证', () => {
  test.beforeEach(async ({ page }) => {
    // 每个测试前的准备工作
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'admin');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // 测试实现
  });
});
```

### 测试覆盖率要求

| 类型 | 最低覆盖率 | 推荐覆盖率 |
|------|-----------|-----------|
| 单元测试 | 60% | 80% |
| 集成测试 | 40% | 60% |
| E2E 测试 | 覆盖关键路径 | 覆盖主要用户场景 |

---

## 代码规范

### Python 代码规范

```bash
# 格式化代码
black services/

# 排序导入
isort services/

# 类型检查
mypy services/
```

### TypeScript 代码规范

```bash
# 格式化并修复
npm run lint:fix

# 仅检查
npm run lint
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量 | snake_case | `user_name`, `total_count` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY`, `DEFAULT_TIMEOUT` |
| 函数 | snake_case | `get_user()`, `calculate_total()` |
| 类 | PascalCase | `UserService`, `DataProcessor` |
| 模块 | snake_case | `user_service.py`, `data_processor.py` |
| 组件 | PascalCase | `UserProfile.tsx`, `DataTable.tsx` |
| 接口/类型 | PascalCase | `UserData`, `ApiResponse` |

---

## 提交规范

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式调整（不影响功能） |
| `refactor` | 重构（不是新功能也不是修复） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具链相关 |

### 示例

```bash
# 新功能
git commit -m "feat(portal): add user profile update endpoint"

# Bug 修复
git commit -m "fix(auth): resolve token expiration edge case"

# 文档
git commit -m "docs: update API documentation for v2"

# 重构
git commit -m "refactor(services): extract common database utilities"
```

---

## 相关文档

- [部署指南](./deployment.md) - 生产环境部署
- [开发指南](./development.md) - 详细开发规范
- [API 设计规范](./standards/api-design.md) - API 设计标准
- [安全配置指南](./standards/security.md) - 安全配置参考
- [E2E 测试选择指南](./standards/e2e-selector-guide.md) - E2E 测试选择
