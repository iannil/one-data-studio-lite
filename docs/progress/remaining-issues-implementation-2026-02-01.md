# 剩余问题实施进度

> 创建时间: 2026-02-01
> 状态: 进行中
> **最新更新**: 2026-02-01 P1.11 密码重置、服务账户调用历史功能完成

## 概述

本文档跟踪 ONE-DATA-STUDIO-LITE 项目剩余问题的修复进度。

---

## 🎉 P1 核心问题完成情况 (2026-02-01)

### ✅ 已完成的 P1 问题

| 问题 | 说明 | 状态 |
|------|------|------|
| P1.6 组件测试覆盖缺失 | 98% (43/44)，所有业务组件已测试 | ✅ 完成 |
| P1.8 配置文件统一 | 创建 `ServiceConfig` 基类，简化各服务配置 | ✅ 完成 |
| P1.9 统一错误处理 | 增强异常系统，30+ 标准错误码 | ✅ 完成 |
| P1.10 服务间调用配置化 | 所有 URL 可通过环境变量覆盖 | ✅ 完成 |
| P1.11 用户密码重置功能 | 三步重置流程（发送验证码、验证、确认）| ✅ 完成 |
| P1.11 服务账户调用历史 | 审计日志查询，支持分页和统计 | ✅ 完成 |

### ✅ 已完成的 P0 问题

| 问题 | 说明 | 状态 |
|------|------|------|
| P0.3 认证系统数据库化 | 实现数据库用户注册/登录/密码修改 | ✅ 完成 |
| P0.4 Token 黑名单 | Redis 支持已存在 | ✅ 验证完成 |
| P0.5 数据库连接池配置 | 已配置 | ✅ 验证完成 |

---

## 🎉 Phase 1 & Phase 2 完成情况 (2026-02-01)

### ✅ Phase 1: 代码质量基础 (已完成)

| 任务 | 状态 | 文件 |
|------|------|------|
| 环境变量默认值修复 | ✅ | `web/src/api/client.ts` |
| 创建配置常量文件 | ✅ | `web/src/config/constants.ts` |
| 环境变量文档 | ✅ | `web/.env.example` |
| 移除硬编码值 | ✅ | `Sso.tsx`, `Workspace.tsx` |

### ✅ Phase 2: 类型安全 (已完成)

| 组件 | 修复内容 |
|------|---------|
| `types/index.ts` | `NL2SQLQueryResponse.rows`, `AuditEvent.details` |
| `CleaningRules.tsx` | `any[]` → `CleaningRuleRecommendation[]` |
| `Catalog.tsx` | `any[]` → `DataAsset[]` |
| `Charts.tsx` | `any[]` → `Chart[]` |
| `Bi.tsx` | `any[]` → `Dashboard[]` |
| `DataSources.tsx` | `any[]` → `DataHubEntity[]` |
| `TaskMonitor.tsx` | `any[]` → `Project[]`, `TaskInstance[]` |
| `Pipelines.tsx` | `any[]` → `Pipeline[]` |
| `MetadataSync.tsx` | `any[]` → `ETLMapping[]` |

**测试结果**: 742/742 通过 ✅

详细报告: `docs/reports/completed/phase1-phase2-code-quality-2026-02-01.md`

## 总体进度

| 类别 | 总数 | 已完成 | 进行中 | 待开始 |
|------|------|--------|--------|--------|
| P0 高风险问题 | 5 | 3 | 0 | 2 |
| P1 中风险问题 | 6 | 6 | 0 | 0 |
| 组件测试 | 44 | 43 | 0 | 1 |
| E2E 测试基础设施 | 1 | 1 | 0 | 0 |
| P2 低风险问题 | 4 | 0 | 0 | 4 |
| P3 优化项 | 5 | 0 | 0 | 5 |

## 立即修复任务 (本周)

### ✅ 1. 修复 utils.ts 变量命名冲突

**状态**: 已完成
**完成时间**: 2026-02-01

**问题描述**:
`web/src/api/utils.ts:115-146` 中的 `handleApiError` 函数存在局部变量命名冲突，导致 4 个单元测试失败。

**修复方案**:
将局部变量 `message` 重命名为 `errorMsg`，避免与 antd 的 `message` 全局对象冲突。

**验证结果**:
```
✓ src/api/utils.test.ts (27 tests) 26ms
Test Files 1 passed (1)
Tests 27 passed (27)
```

**相关文件**:
- `web/src/api/utils.ts:124-136`

---

### ✅ 2. 实现 Search.tsx 双击跳转功能

**状态**: 已完成
**完成时间**: 2026-02-01

**问题描述**:
`web/src/pages/Assets/Search.tsx:450` 中存在 TODO 注释，资产搜索结果的双击跳转功能未实现。

**修复方案**:
1. 导入 `useNavigate` hook
2. 添加 `navigate` hook 到组件
3. 实现 `onDoubleClick` 事件处理函数

**验证结果**:
构建成功，无类型错误。

**相关文件**:
- `web/src/pages/Assets/Search.tsx:25,141,450-454`

---

## 短期计划任务 (本月)

### ✅ 3. 组件测试覆盖完成

**状态**: ✅ 已完成
**优先级**: P1
**完成时间**: 2026-02-01

**目标覆盖率**: 75%
**实际覆盖率**: 98% (43/44)

**所有组件测试** (43个):

#### Dashboard (4个) ✅
- [x] `Cockpit.test.tsx` - 10个测试用例
- [x] `Workspace.test.tsx` - 12个测试用例
- [x] `Notifications.test.tsx` - 15个测试用例
- [x] `Profile.test.tsx` - 16个测试用例

#### Planning (5个) ✅
- [x] `DataSources.test.tsx` - 9个测试用例
- [x] `Tags.test.tsx` - 9个测试用例
- [x] `MetadataBrowser.test.tsx` - 8个测试用例
- [x] `Lineage.test.tsx` - 7个测试用例
- [x] `Standards.test.tsx` - 9个测试用例

#### Collection (4个) ✅
- [x] `SyncJobs.test.tsx` - 8个测试用例
- [x] `ScheduleManage.test.tsx` - 7个测试用例
- [x] `TaskMonitor.test.tsx` - 7个测试用例
- [x] `EtlFlows.test.tsx` - 6个测试用例

#### Development (7个) ✅
- [x] `CleaningRules.test.tsx` - 7个测试用例
- [x] `QualityCheck.test.tsx` - 6个测试用例
- [x] `TransformConfig.test.tsx` - 6个测试用例
- [x] `FieldMapping.test.tsx` - 6个测试用例
- [x] `OcrProcessing.test.tsx` - 5个测试用例
- [x] `DataFusion.test.tsx` - 6个测试用例
- [x] `FillMissing.test.tsx` - 5个测试用例

#### Analysis (6个) ✅
- [x] `Bi.test.tsx` - 8个测试用例
- [x] `Charts.test.tsx` - 8个测试用例
- [x] `Pipelines.test.tsx` - 6个测试用例
- [x] `NL2SQL.test.tsx` - 7个测试用例
- [x] `Alerts.test.tsx` - 6个测试用例
- [x] `EtlLink.test.tsx` - 5个测试用例

#### Assets (5个) ✅
- [x] `Catalog.test.tsx` - 8个测试用例
- [x] `DataApiManage.test.tsx` - 9个测试用例
- [x] `MetadataSync.test.tsx` - 10个测试用例
- [x] `AssetDetail.test.tsx` - 3个测试用例
- [x] `Search.test.tsx` - 13个测试用例

#### Security (4个) ✅
- [x] `MaskRules.test.tsx` - 10个测试用例
- [x] `Sensitive.test.tsx` - 10个测试用例
- [x] `Permissions.test.tsx` - 8个测试用例
- [x] `Sso.test.tsx` - 7个测试用例

#### Support (3个) ✅
- [x] `Announcements.test.tsx` - 8个测试用例
- [x] `Invoices.test.tsx` - 5个测试用例
- [x] `Content.test.tsx` - 5个测试用例

#### Operations (5个) ✅
- [x] `Users.test.tsx` - 9个测试用例
- [x] `AuditLog.test.tsx` - 8个测试用例
- [x] `Monitor.test.tsx` - 7个测试用例
- [x] `ApiGateway.test.tsx` - 6个测试用例
- [x] `Tenants.test.tsx` - 6个测试用例

**未测试组件** (1个):
- [ ] `Login/index.tsx` - 简单表单组件（通过其他测试间接覆盖）

**测试结果**:
```
Test Files 61 passed (61)
Tests 742 passed (742)
Duration 33.13s
```

---

### 🔄 4. E2E P1 测试基础设施增强

**状态**: 进行中
**优先级**: P1

**当前通过率**: 22/96 (23%)

| 测试套件 | 通过数 | 总数 | 通过率 | 状态 |
|---------|--------|------|--------|------|
| Data Cleaning | 0 | 28 | 0% | 🔴 待服务可用 |
| Pipeline | 0 | 23 | 0% | 🔴 待服务可用 |
| Data API | 8 | 22 | 36% | 🟠 部分通过 |
| Sensitive Data | 11 | 14 | 79% | 🟢 基本完成 |

**E2E 测试分析**:

E2E 测试失败的主要原因：
1. **后端服务未运行** - 测试需要服务在端口 8010-8016 运行
2. **前端未运行** - 测试需要 localhost:3000 可访问
3. **部分功能未实现** - 部分测试的功能在 UI 中尚未实现

**已完成的改进** (2026-02-01):
- ✅ 创建服务健康检查工具 (`web/e2e/utils/service-check.ts`)
- ✅ 更新全局 setup 以检查服务可用性
- ✅ 创建测试辅助工具 (`web/e2e/utils/test-fixtures.ts`)
- ✅ 测试配置优化 - 减少并发工作进程避免资源争用

**服务健康检查功能**:
- 自动检测所有后端服务状态（Portal, NL2SQL, DataAPI, Cleaning, Metadata, Sensitive, Audit）
- 打印服务状态摘要
- 支持基于服务可用性跳过测试

**运行 E2E 测试的先决条件**:
1. 启动前端: `cd web && npm run dev` (端口 3000)
2. 启动后端服务: `make services-up` (端口 8010-8016)
3. 运行测试: `cd web/e2e && npm run e2e`

**下一步**:
- [ ] 在 CI/CD 中添加服务启动脚本
- [ ] 使用 Docker Compose 进行服务编排
- [ ] 添加 E2E 测试定时执行

---

## 中期计划任务 (下季度)

### 5. 生产环境部署验证

**状态**: 待开始
**优先级**: P0

**待验证项**:
- [ ] K3s 单机/多机部署脚本实际运行
- [ ] Helm Charts 配置正确性验证
- [ ] 各服务在 K8s 环境下的健康检查
- [ ] 服务间网络连通性测试
- [ ] 持久化存储挂载验证

---

### 6. 安全加固审查

**状态**: 待开始
**优先级**: P0

**待审查项**:
- [ ] SQL 注入防护审查
- [ ] XSS 防护审查
- [ ] CSRF 防护配置
- [ ] 敏感数据加密存储
- [ ] API 限流和防暴力破解
- [ ] 容器镜像安全扫描
- [ ] 依赖包漏洞检查

---

### 7. 代码重构

**状态**: 部分完成
**优先级**: P1

**已完成** (2026-02-01):
- [x] 修复类型安全问题（移除核心组件 `any` 类型）
- [x] 创建配置常量文件
- [x] 环境变量默认值修复

**待改进项**:
- [ ] 统一错误处理和状态管理
- [ ] 创建统一的 `useApiCall` hook
- [ ] 创建统一的错误处理组件

---

### 8. 外部组件集成

**状态**: 待开始
**优先级**: P1

| 组件 | 当前完成度 | 待实现功能 |
|------|-----------|-----------|
| Cube-Studio | 75% | Pipeline历史记录、计算资源管理 |
| DataHub | 67% | 元数据变更历史详情 |
| Superset | 50% | 图表创建功能、iframe 集成 |
| DolphinScheduler | 50% | 任务提交功能 |

---

## 低优先级任务

### 9. 缺失的系统功能

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 异步任务系统 | P1 | 待实现 |
| 批量数据读取优化 | P1 | 待实现 |
| 用户密码重置功能 | P1 | ✅ 已完成 |
| 服务账户调用历史记录 | P2 | ✅ 已完成 |

---

### ✅ P1.11 用户密码重置功能 (2026-02-01)

**状态**: 已完成

**新增端点**:
- `POST /auth/password/reset/code` - 发送密码重置验证码
- `POST /auth/password/reset/verify` - 验证重置验证码
- `POST /auth/password/reset/confirm` - 确认密码重置

**功能特性**:
- Redis 存储验证码，15 分钟过期
- 6 位数字验证码
- 开发模式直接返回验证码便于测试
- 生产模式预留邮件服务集成接口
- 密码强度验证（至少中等强度）

**相关文件**:
- `services/portal/models.py:210-242` - 新增请求/响应模型
- `services/portal/main.py:620-730` - 新增端点实现

---

### ✅ P1.11 服务账户调用历史 (2026-02-01)

**状态**: 已完成

**新增端点**:
- `GET /api/service-accounts/{name}/call-history` - 获取服务账户调用历史
- `GET /api/service-accounts/{name}/call-history/stats` - 获取调用统计摘要

**功能特性**:
- 从审计日志查询服务账户 API 调用记录
- 支持日期范围过滤（ISO 8601 格式）
- 支持子系统过滤
- 分页查询（默认 50 条/页，最大 500 条）
- 返回统计数据：总调用次数、成功率、平均响应时间
- 最近 30 天调用统计摘要

**相关文件**:
- `services/portal/models.py:400-432` - 新增响应模型
- `services/portal/routers/service_accounts.py:305-494` - 新增端点实现

---

### 10. 监控告警规则完善

**状态**: 待开始
**优先级**: P2

**待配置项**:
- [ ] CPU/内存使用率告警
- [ ] 磁盘空间告警
- [ ] API 响应时间告警
- [ ] 错误率告警
- [ ] 业务指标告警

---

### 11. CI/CD 流水线搭建

**状态**: 待开始
**优先级**: P2

**待实现**:
- [ ] GitHub Actions 工作流配置
- [ ] 自动化测试运行
- [ ] 代码覆盖率检查
- [ ] 自动化部署脚本
- [ ] 回滚机制

---

### 12. 文档完善

**状态**: 待开始
**优先级**: P2

**待补充文档**:
- [ ] 用户使用手册
- [ ] 运维操作手册
- [ ] 故障排查指南
- [ ] API 接口文档（自动生成）
- [ ] 架构决策记录（ADR）

---

## 优化建议 (P3)

### 13. 性能优化

| 优化项 | 预期收益 | 实施难度 | 状态 |
|--------|----------|----------|------|
| React.memo 优化组件渲染 | 中等 | 低 | 待实施 |
| 虚拟滚动处理大数据列表 | 高 | 中 | 待实施 |
| 动态导入减少初始包大小 | 高 | 低 | 待实施 |
| 图片懒加载 | 中等 | 低 | 待实施 |
| API 响应缓存 | 高 | 中 | 待实施 |

---

### 14. 长期优化项

- [ ] 多租户支持设计
- [ ] 国际化 (i18n) 支持
- [ ] 移动端适配方案
- [ ] PWA 支持

---

## 统计信息

### 按优先级统计

| 优先级 | 问题数 | 已完成 | 进行中 | 待开始 |
|--------|--------|--------|--------|--------|
| P0 (高风险) | 5 | 3 | 0 | 2 |
| P1 (中风险) | 6 | 6 | 0 | 0 |
| P2 (低风险) | 4 | 2 | 0 | 2 |
| P3 (优化) | 5 | 0 | 0 | 5 |

### 按模块统计

| 模块 | 问题数 | 状态 |
|------|--------|------|
| 测试 | 2 | 已完成 |
| 功能 | 3 | 已完成 |
| 安全 | 1 | 待开始 |
| 部署 | 1 | 待开始 |
| 代码质量 | 1 | 待开始 |
| 运维 | 2 | 待开始 |
| 优化 | 5 | 待开始 |

---

## 更新日志

### 2026-02-01 (第十一阶段) - P1 全部完成 ✅
- ✅ P1.11 用户密码重置功能 - 三步重置流程
  - `POST /auth/password/reset/code` - 发送验证码
  - `POST /auth/password/reset/verify` - 验证验证码
  - `POST /auth/password/reset/confirm` - 确认重置
- ✅ P1.11 服务账户调用历史 - 审计日志查询
  - `GET /api/service-accounts/{name}/call-history` - 调用历史
  - `GET /api/service-accounts/{name}/call-history/stats` - 统计摘要
- ✅ **P1 中风险问题全部完成** - 6/6 (100%)

### 2026-02-01 (第十阶段)
- ✅ P1.6 组件测试覆盖完成 - 98% (43/44)
- ✅ 所有 43 个业务组件测试文件创建完成
- ✅ 所有 742 个测试通过
- ✅ P1.8 配置文件统一 - 创建 `ServiceConfig` 基类
- ✅ P1.9 统一错误处理 - 增强异常系统
- ✅ P1.10 服务间调用配置化 - 所有 URL 可通过环境变量覆盖
- ✅ P0.3 认证系统数据库化 - 实现数据库用户注册/登录/密码修改
- ✅ P0.4 Token 黑名单 - Redis 支持已存在
- ✅ P0.5 数据库连接池配置 - 已配置
- ✅ 创建 E2E 测试辅助工具 (`test-fixtures.ts`)
- ✅ 更新全局 setup 以检查服务可用性

### 2026-02-01 (第九阶段)
- ✅ 创建 E2E 服务健康检查工具 (`service-check.ts`)
- ✅ 创建 E2E 测试辅助工具 (`test-fixtures.ts`)
- ✅ 更新全局 setup 以检查服务可用性

### 2026-02-01 (第八阶段)
- ✅ 创建 Users.test.tsx - 9个测试用例
- ✅ 创建 AuditLog.test.tsx - 8个测试用例
- ✅ 创建 Monitor.test.tsx - 7个测试用例
- ✅ 创建 Announcements.test.tsx - 8个测试用例
- ✅ 创建 MainLayout.test.tsx - 7个测试用例
- ✅ Operations 模块测试覆盖 3/5 完成
- ✅ Support 模块测试覆盖 1/3 完成
- ✅ Layout 模块测试覆盖完成 (1/1) ✅
- ✅ 组件测试覆盖率达到 64% (25/39)
- ✅ 所有 627 个测试通过

### 2026-02-01 (第七阶段)
- ✅ 创建 SyncJobs.test.tsx - 8个测试用例
- ✅ 创建 ScheduleManage.test.tsx - 7个测试用例
- ✅ 创建 Bi.test.tsx - 8个测试用例
- ✅ 创建 Charts.test.tsx - 8个测试用例
- ✅ 创建 Pipelines.test.tsx - 6个测试用例
- ✅ Collection 模块测试覆盖 2/4 完成
- ✅ Analysis 模块测试覆盖 3/6 完成
- ✅ 所有 587 个测试通过

### 2026-02-01 (第六阶段)
- ✅ 创建 MetadataBrowser.test.tsx - 8个测试用例
- ✅ 创建 Lineage.test.tsx - 7个测试用例
- ✅ 创建 Standards.test.tsx - 9个测试用例
- ✅ 创建 MetadataSync.test.tsx - 10个测试用例
- ✅ 创建 MaskRules.test.tsx - 10个测试用例
- ✅ Planning 模块测试覆盖完成 (5/5) ✅
- ✅ Assets 模块测试覆盖 4/5 完成
- ✅ Security 模块测试覆盖 2/4 完成
- ✅ 所有 550 个测试通过

### 2026-02-01 (第五阶段)
- ✅ 创建 Catalog.test.tsx - 8个测试用例
- ✅ 创建 Tags.test.tsx - 9个测试用例
- ✅ 创建 DataApiManage.test.tsx - 9个测试用例
- ✅ 创建 Sensitive.test.tsx - 10个测试用例
- ✅ Planning 模块测试覆盖 2/5 完成
- ✅ Assets 模块测试覆盖 3/5 完成
- ✅ Security 模块测试覆盖 1/4 完成
- ✅ 所有 507 个测试通过

### 2026-02-01 (第四阶段)
- ✅ 创建 Workspace.test.tsx - 12个测试用例
- ✅ 创建 DataSources.test.tsx - 9个测试用例
- ✅ 修复 Workspace.tsx 缺少 ApiOutlined 导入的bug
- ✅ Dashboard 模块测试覆盖完成 (4/4)
- ✅ 所有 473 个测试通过

### 2026-02-01 (第三阶段)
- ✅ 创建 Profile.test.tsx - 16个测试用例
- ✅ 创建 Notifications.test.tsx - 15个测试用例
- ✅ 所有 453 个测试通过

### 2026-02-01 (第二阶段)
- ✅ 修复 utils.ts 变量命名冲突 - 27个单元测试全部通过
- ✅ 实现 Search.tsx 双击跳转到资产详情页
- ✅ 创建 Search.test.tsx - 13个测试用例
- ✅ 创建 Cockpit.test.tsx - 10个测试用例
- ✅ 修复测试环境 ResizeObserver mock 问题
- ✅ 所有 423 个测试通过

### 2026-02-01 (第一阶段)
- ✅ 创建任务列表跟踪剩余问题
