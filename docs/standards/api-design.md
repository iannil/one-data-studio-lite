# API 设计规范

**版本**: 1.0
**更新日期**: 2026-01-30

---

## 概述

本文档定义 ONE-DATA-STUDIO-LITE 项目的 API 设计规范，确保前后端 API 一致性。

### 设计原则

1. **RESTful**: 遵循 REST 架构风格
2. **统一响应**: 所有 API 使用统一的响应格式
3. **版本控制**: 通过 URL 路径进行版本控制（如 `/v1/`）
4. **幂等性**: GET、PUT、DELETE 操作保持幂等
5. **安全性**: 所有 API 需要认证（除公开接口外）

---

## 统一响应格式

### 成功响应

```json
{
  "code": 20000,
  "message": "success",
  "data": {
    // 业务数据
  },
  "timestamp": 1706659200
}
```

### 错误响应

```json
{
  "code": 40001,
  "message": "参数校验失败",
  "data": null,
  "timestamp": 1706659200
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | int | 是 | 业务状态码，20000 表示成功 |
| message | string | 是 | 提示信息 |
| data | any | 否 | 业务数据，成功时返回，失败时可为 null |
| timestamp | int | 是 | Unix 时间戳（秒） |

---

## 状态码定义

### 成功类 (2xxxx)

| 状态码 | 说明 |
|--------|------|
| 20000 | 成功 |
| 20001 | 创建成功 |
| 20002 | 请求已接受 |
| 20003 | 无内容 |

### 客户端错误 (4xxxx)

| 状态码 | 说明 |
|--------|------|
| 40001 | 参数错误 |
| 40002 | 缺少必要参数 |
| 40003 | 格式错误 |
| 40004 | 参数校验失败 |
| 40100 | 未授权 |
| 40101 | Token 已过期 |
| 40102 | Token 无效 |
| 40300 | 权限不足 |
| 40400 | 资源不存在 |
| 40401 | 资源不存在（通用） |
| 40402 | 用户不存在 |
| 40403 | 配置不存在 |
| 41001 | 资源已存在 |
| 41002 | 操作不允许 |
| 41003 | 状态无效 |
| 41004 | 超出配额 |

### 服务端错误 (5xxxx)

| 状态码 | 说明 |
|--------|------|
| 50000 | 内部服务错误 |
| 50300 | 服务不可用 |
| 50400 | 网关超时 |

### 上游服务错误 (42xxx)

| 状态码 | 说明 |
|--------|------|
| 42000 | 外部服务错误（通用） |
| 42001 | 数据库错误 |
| 42002 | 缓存错误 |
| 42100 | SeaTunnel 错误 |
| 42101 | DataHub 错误 |
| 42102 | DolphinScheduler 错误 |
| 42103 | Superset 错误 |
| 42104 | ShardingSphere 错误 |
| 42105 | Hop 错误 |
| 42106 | Cube-Studio 错误 |

---

## URL 设计规范

### 版本控制

```
/api/v1/{resource}
```

- 使用 `v1`, `v2` 等表示版本
- 不使用小版本号（如 `v1.1`）
- 新版本向后兼容旧版本

### 资源命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 资源集合 | 小写复数 | `/api/v1/jobs`, `/api/v1/users` |
| 单个资源 | 小写单数 | `/api/v1/jobs/{id}` |
| 子资源 | 父资源/子资源 | `/api/v1/jobs/{id}/tasks` |
| 动作 | 动词 | `/api/v1/jobs/{id}/cancel` |

### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，从 1 开始 |
| page_size | int | 每页大小，默认 10 |
| sort | string | 排序字段，如 `created_at:desc` |
| filter | string | 过滤条件 |
| fields | string | 返回字段，逗号分隔 |

### 分页响应

```json
{
  "code": 20000,
  "message": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 10,
    "pages": 10
  },
  "timestamp": 1706659200
}
```

---

## HTTP 方法

| 方法 | 说明 | 幂等性 |
|------|------|--------|
| GET | 获取资源 | 是 |
| POST | 创建资源 | 否 |
| PUT | 全量更新资源 | 是 |
| PATCH | 部分更新资源 | 否 |
| DELETE | 删除资源 | 是 |

---

## 代理 API 规范

### 代理路径规范

```
/api/proxy/{service}/{version}/{resource}
```

| 参数 | 说明 |
|------|------|
| service | 服务名称，如 `seatunnel`, `datahub` |
| version | 版本号，如 `v1` |
| resource | 资源路径 |

### 示例

```
# SeaTunnel
GET    /api/proxy/seatunnel/v1/jobs
GET    /api/proxy/seatunnel/v1/jobs/{id}
POST   /api/proxy/seatunnel/v1/jobs
DELETE /api/proxy/seatunnel/v1/jobs/{id}

# ShardingSphere
GET    /api/proxy/shardingsphere/v1/mask-rules
POST   /api/proxy/shardingsphere/v1/mask-rules
PUT    /api/proxy/shardingsphere/v1/mask-rules
DELETE /api/proxy/shardingsphere/v1/mask-rules/{table}

# Hop
GET    /api/proxy/hop/v1/workflows
GET    /api/proxy/hop/v1/pipelines
POST   /api/proxy/hop/v1/pipelines/{name}/run
```

### 兼容旧版 API

保持向后兼容，旧版 API 路径继续可用：

```
# 旧版（逐步废弃）
GET /api/proxy/seatunnel/api/v1/job/list

# 新版（推荐）
GET /api/proxy/seatunnel/v1/jobs
```

---

## 请求规范

### Content-Type

```json
Content-Type: application/json
```

### 认证

```http
Authorization: Bearer {token}
```

### 请求体示例

```json
{
  "name": "example",
  "config": {
    "key": "value"
  }
}
```

---

## 后端实现规范

### 使用统一的响应模型

```python
from services.common.api_response import ApiResponse, success, error, ErrorCode

@router.get("/v1/jobs", response_model=ApiResponse)
async def list_jobs():
    try:
        jobs = await get_jobs()
        return success(data={"jobs": jobs, "total": len(jobs)})
    except Exception as e:
        return error(
            message=f"获取任务列表失败: {str(e)}",
            code=ErrorCode.INTERNAL_ERROR
        )
```

### 定义请求模型

```python
from pydantic import BaseModel

class JobCreateRequest(BaseModel):
    name: str
    config: dict
    priority: int = 0

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "example-job",
                    "config": {"source": "mysql", "sink": "elasticsearch"},
                    "priority": 1
                }
            ]
        }
    }
```

### 添加 OpenAPI 文档

```python
@router.get(
    "/v1/jobs/{job_id}",
    response_model=ApiResponse,
    summary="获取任务详情",
    description="根据任务 ID 获取任务的详细信息"
)
async def get_job(job_id: str):
    ...
```

---

## 前端实现规范

### API 函数定义

```typescript
import client from './client';
import type { ApiResponse } from './types';

export async function getJobs(): Promise<ApiResponse<JobsResponse>> {
  const resp = await client.get('/api/proxy/seatunnel/v1/jobs');
  return resp.data;
}

export async function getJob(id: string): Promise<ApiResponse<JobDetail>> {
  const resp = await client.get(`/api/proxy/seatunnel/v1/jobs/${id}`);
  return resp.data;
}
```

### 类型定义

```typescript
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data?: T;
  timestamp: number;
}

export interface JobsResponse {
  jobs: Job[];
  total: number;
}

export interface Job {
  jobId: string;
  jobName: string;
  jobStatus: 'RUNNING' | 'FINISHED' | 'FAILED';
  createTime: string;
}
```

### 错误处理

```typescript
import { ErrorCode } from './error-codes';

export function isSuccessResponse<T>(response: ApiResponse<T>): boolean {
  return response.code === 20000;
}

export function getErrorMessage(response: ApiResponse): string {
  return response.message || '未知错误';
}

// 使用示例
const response = await getJobs();
if (isSuccessResponse(response)) {
  console.log(response.data.jobs);
} else {
  console.error(getErrorMessage(response));
}
```

---

## 测试规范

### 单元测试

```python
import pytest
from httpx import AsyncClient

async def test_list_jobs():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get(
            "/api/proxy/seatunnel/v1/jobs",
            headers={"Authorization": "Bearer test-token"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 20000
        assert "jobs" in data["data"]
```

### 集成测试

```python
async def test_create_job():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/proxy/seatunnel/v1/jobs",
            json={"name": "test-job", "config": {}},
            headers={"Authorization": "Bearer test-token"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 20000
```

---

## 迁移指南

### 从旧版 API 迁移到新版 API

**后端**：

1. 创建新的 v1 版本 API 端点
2. 使用 `ApiResponse` 返回统一格式
3. 保留旧版 API 端点，调用 v1 实现并转换格式

**前端**：

1. 添加新的 `*V1` 函数
2. 逐步替换旧调用
3. 使用 `isSuccessResponse` 检查响应

### 示例

```typescript
// 旧版
export async function getJobs() {
  const resp = await client.get('/api/proxy/seatunnel/api/v1/job/list');
  return resp.data;  // 直接返回数据
}

// 新版
export async function getJobsV1(): Promise<ApiResponse<JobsResponse>> {
  const resp = await client.get('/api/proxy/seatunnel/v1/jobs');
  return resp.data;  // 返回完整响应
}

// 使用
const response = await getJobsV1();
if (isSuccessResponse(response)) {
  const { jobs, total } = response.data;
  console.log(jobs);
}
```

---

## 参考资料

- [RESTful API 设计指南](https://github.com/microsoft/api-guidelines)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [OpenAPI 规范](https://swagger.io/specification/)
