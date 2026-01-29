# ONE-DATA-STUDIO-LITE 测试用例文档

## 概述

本目录包含 ONE-DATA-STUDIO-LITE 智能大数据平台的完整测试用例文档，按用户角色的全生命周期组织。

## 测试用例结构

| 文件 | 描述 | 用例数量 |
|------|------|----------|
| [00-通用测试用例.md](./00-通用测试用例.md) | 认证、健康检查、错误处理等通用功能测试 | ~30 |
| [01-系统管理员测试用例.md](./01-系统管理员测试用例.md) | 系统管理员全生命周期测试 | ~25 |
| [02-数据工程师测试用例.md](./02-数据工程师测试用例.md) | 数据工程师全生命周期测试 | ~40 |
| [03-数据分析师测试用例.md](./03-数据分析师测试用例.md) | 数据分析师全生命周期测试 | ~35 |
| [04-数据治理专员测试用例.md](./04-数据治理专员测试用例.md) | 数据治理专员全生命周期测试 | ~30 |
| [05-数据安全管理员测试用例.md](./05-数据安全管理员测试用例.md) | 数据安全管理员全生命周期测试 | ~35 |
| [06-业务用户测试用例.md](./06-业务用户测试用例.md) | 业务用户全生命周期测试 | ~25 |

---

## 用户角色定义

### 1. 系统管理员 (System Administrator)
- **代码**: ADM
- **职责**: 平台运维、用户管理、权限配置、系统监控
- **使用服务**: Portal, Cube-Studio, Audit Log

### 2. 数据工程师 (Data Engineer)
- **代码**: ENG
- **职责**: ETL开发、数据同步任务、数据管道构建
- **使用服务**: AI Cleaning, Metadata Sync, SeaTunnel, Hop, DolphinScheduler

### 3. 数据分析师 (Data Analyst)
- **代码**: ANA
- **职责**: 数据分析、报表制作、业务洞察
- **使用服务**: NL2SQL, Data API, Superset

### 4. 数据治理专员 (Data Steward)
- **代码**: STW
- **职责**: 元数据管理、数据标准制定、数据质量监控
- **使用服务**: DataHub, Metadata Sync, AI Cleaning

### 5. 数据安全管理员 (Security Administrator)
- **代码**: SEC
- **职责**: 敏感数据识别、脱敏规则配置、访问权限审计
- **使用服务**: Sensitive Detect, Audit Log, ShardingSphere

### 6. 业务用户 (Business User)
- **代码**: USR
- **职责**: 数据消费、报表查看、自助查询
- **使用服务**: Portal, NL2SQL, Data API, Superset(只读)

---

## 测试用例编号规则

```
TC-{角色代码}-{阶段编号}-{序号}
```

| 角色代码 | 说明 |
|----------|------|
| COM | 通用 (Common) |
| ADM | 系统管理员 |
| ENG | 数据工程师 |
| ANA | 数据分析师 |
| STW | 数据治理专员 |
| SEC | 数据安全管理员 |
| USR | 业务用户 |

---

## 测试环境

### 服务端口

| 服务 | 端口 | 健康检查 |
|------|------|----------|
| Portal | 8010 | GET /health |
| NL2SQL | 8011 | GET /health |
| AI Cleaning | 8012 | GET /health |
| Metadata Sync | 8013 | GET /health |
| Data API | 8014 | GET /health |
| Sensitive Detect | 8015 | GET /health |
| Audit Log | 8016 | GET /health |

### 测试账号

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| admin | admin123 | admin | 开发环境管理员账号 |

### 前置条件

1. 所有服务已启动并健康
2. 数据库连接正常
3. LLM 服务 (Ollama) 可用
4. DataHub/DolphinScheduler 等外部组件已部署

---

## 功能覆盖矩阵

确保所有 API 接口被测试用例覆盖：

### Portal 服务 (8010)

| 接口 | 方法 | 覆盖测试用例 |
|------|------|--------------|
| / | GET | TC-COM-01-01 |
| /health | GET | TC-COM-01-02 |
| /auth/login | POST | TC-COM-02-01 ~ 04 |
| /auth/logout | POST | TC-COM-02-05 |
| /api/subsystems | GET | TC-ADM-02-01 |

### NL2SQL 服务 (8011)

| 接口 | 方法 | 覆盖测试用例 |
|------|------|--------------|
| /health | GET | TC-COM-01-03 |
| /api/nl2sql/query | POST | TC-ANA-02-01 ~ 05, TC-USR-04-01 ~ 04 |
| /api/nl2sql/explain | POST | TC-ANA-02-06 ~ 07 |
| /api/nl2sql/tables | GET | TC-ANA-02-08 ~ 09 |

### AI Cleaning 服务 (8012)

| 接口 | 方法 | 覆盖测试用例 |
|------|------|--------------|
| /health | GET | TC-COM-01-04 |
| /api/cleaning/analyze | POST | TC-ENG-03-01 ~ 05 |
| /api/cleaning/recommend | POST | TC-ENG-04-01 ~ 04 |
| /api/cleaning/generate-config | POST | TC-ENG-04-05 ~ 08 |
| /api/cleaning/rules | GET | TC-ENG-04-09 |

### Metadata Sync 服务 (8013)

| 接口 | 方法 | 覆盖测试用例 |
|------|------|--------------|
| /health | GET | TC-COM-01-05 |
| /api/metadata/webhook | POST | TC-ENG-02-01 ~ 03 |
| /api/metadata/sync | POST | TC-ENG-02-04 ~ 05 |
| /api/metadata/mappings | GET | TC-ENG-02-06 |
| /api/metadata/mappings/{id} | PUT | TC-ENG-02-07 ~ 08 |

### Data API 服务 (8014)

| 接口 | 方法 | 覆盖测试用例 |
|------|------|--------------|
| /health | GET | TC-COM-01-06 |
| /api/data/{dataset_id} | GET | TC-ANA-01-01 ~ 04 |
| /api/data/{dataset_id}/schema | GET | TC-ANA-01-05 ~ 07 |
| /api/data/{dataset_id}/query | POST | TC-ANA-01-08 ~ 12 |
| /api/assets/search | GET | TC-ANA-01-13 ~ 16, TC-USR-02-01 ~ 04 |
| /api/assets/{asset_id} | GET | TC-ANA-01-17 ~ 18 |
| /api/assets/{asset_id}/subscribe | POST | TC-USR-06-01 ~ 03 |

### Sensitive Detect 服务 (8015)

| 接口 | 方法 | 覆盖测试用例 |
|------|------|--------------|
| /health | GET | TC-COM-01-07 |
| /api/sensitive/scan | POST | TC-SEC-01-01 ~ 06 |
| /api/sensitive/classify | POST | TC-SEC-02-01 ~ 04 |
| /api/sensitive/rules | GET | TC-SEC-03-01 ~ 02 |
| /api/sensitive/rules | POST | TC-SEC-03-03 ~ 05 |
| /api/sensitive/reports | GET | TC-SEC-01-07 |

### Audit Log 服务 (8016)

| 接口 | 方法 | 覆盖测试用例 |
|------|------|--------------|
| /health | GET | TC-COM-01-08 |
| /api/audit/log | POST | TC-ADM-05-01 ~ 02 |
| /api/audit/logs | GET | TC-ADM-05-03 ~ 07, TC-SEC-06-01 ~ 05 |
| /api/audit/logs/{id} | GET | TC-ADM-05-08 |
| /api/audit/stats | GET | TC-ADM-05-09, TC-SEC-06-06 |
| /api/audit/export | POST | TC-ADM-05-10 ~ 11, TC-SEC-07-01 ~ 02 |

---

## 测试执行指南

### 1. 环境准备

```bash
# 启动所有服务
make services-up

# 检查服务健康状态
make status
```

### 2. 执行测试

可使用以下工具执行测试：

- **cURL**: 命令行测试
- **Postman**: GUI 测试工具
- **pytest + httpx**: 自动化测试

### 3. 测试报告

建议使用以下格式记录测试结果：

| 用例编号 | 状态 | 执行时间 | 备注 |
|----------|------|----------|------|
| TC-XXX-XX-XX | PASS/FAIL | 2024-XX-XX | - |

---

## 测试优先级

| 级别 | 说明 | 标记 |
|------|------|------|
| P0 | 核心功能，必须通过 | 🔴 |
| P1 | 重要功能 | 🟡 |
| P2 | 一般功能 | 🟢 |
| P3 | 边界/异常测试 | ⚪ |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2024-01-29 | 初始版本，覆盖六大用户角色全生命周期 |
