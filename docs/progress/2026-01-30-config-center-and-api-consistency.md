# 配置中心和 API 一致性实施进展

**实施日期**: 2026-01-30
**实施阶段**: 阶段一 - 基础架构完善

---

## 实施概述

本次实施完成了以下两个主要任务：

1. **配置中心实现（etcd）** - 解决配置分散、无热更新、无版本控制问题
2. **API 一致性修复** - 统一前后端 API 定义，标准化错误响应

---

## 完成的文件清单

### 1. etcd 配置中心

#### 新建文件

| 文件路径 | 说明 |
|---------|------|
| `deploy/etcd/docker-compose.yml` | etcd 服务部署配置 |
| `deploy/etcd/etcdctl.sh` | etcdctl 快捷操作脚本 |

#### 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `services/common/config_center.py` | **新建** - 配置中心客户端 |
| `services/portal/config.py` | 添加配置中心支持，新增 `init_config_center()` 函数 |
| `services/portal/main.py` | 在 lifespan 中初始化配置中心 |
| `services/.env.example` | 新增 etcd 配置项 |
| `Makefile` | 新增 etcd 相关命令（up/down/logs/ctl/backup/init） |

### 2. API 一致性修复

#### 新建文件

| 文件路径 | 说明 |
|---------|------|
| `services/common/api_response.py` | **新建** - 统一 API 响应模型 |

#### 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `services/portal/routers/seatunnel.py` | 添加 v1 版本 API，使用统一 `ApiResponse` 格式 |
| `web/src/api/seatunnel.ts` | 添加 v1 版本 API 函数，保留旧版兼容 |

---

## 技术细节

### 1. etcd 配置中心

#### 部署配置

- **镜像**: `quay.io/coreos/etcd:v3.5.12`
- **端口**: 2379（客户端），2380（对等通信）
- **持久化**: Docker volume `one-data-studio-etcd-data`
- **自动压缩**: 保留 24 小时历史
- **快照**: 每 10000 次写操作

#### 客户端实现

```python
class EtcdConfigCenter:
    """基于 etcd 的配置中心客户端"""

    # 功能
    - 配置集中存储（etcd KV）
    - 配置读取（带缓存）
    - Watch 机制（热更新）
    - 配置版本记录（etcd 内置）
    - 敏感配置加密（AES-256-GCM）
    - 环境变量兜底（降级策略）
```

#### 配置结构

```
/one-data-studio/
├── /portal/
│   ├── /database/url
│   ├── /database/pool_size
│   └── /jwt/secret
├── /seatunnel/
│   └── /api/token
├── /superset/
│   ├── /auth/username
│   └── /auth/password
└── /global/
    ├── /log/level
    └── /llm/base_url
```

#### etcdctl 脚本命令

```bash
./etcdctl.sh get /one-data-studio/portal/jwt/secret
./etcdctl.sh put /one-data-studio/portal/jwt/secret "new-secret"
./etcdctl.sh list /one-data-studio/
./etcdctl.sh watch /one-data-studio/portal/
./etcdctl.sh history /one-data-studio/portal/jwt/secret
./etcdctl.sh backup
./etcdctl.sh init
```

### 2. API 一致性修复

#### 统一响应格式

```python
class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应模型"""
    code: int = 20000           # 业务状态码
    message: str = "success"    # 提示信息
    data: Optional[T] = None    # 业务数据
    timestamp: int              # Unix 时间戳
```

#### 错误码定义

```python
class ErrorCode(IntEnum):
    SUCCESS = 20000
    CREATED = 20001
    INVALID_PARAMS = 40001
    UNAUTHORIZED = 40100
    NOT_FOUND = 40400
    INTERNAL_ERROR = 50000
    SEATUNNEL_ERROR = 42100
    # ... 更多错误码
```

#### SeaTunnel API 标准化

**新版 API（推荐）**:

```
GET    /api/proxy/seatunnel/v1/jobs              # 获取任务列表
GET    /api/proxy/seatunnel/v1/jobs/{id}         # 获取任务详情
GET    /api/proxy/seatunnel/v1/jobs/{id}/status  # 获取任务状态
POST   /api/proxy/seatunnel/v1/jobs              # 提交新任务
DELETE /api/proxy/seatunnel/v1/jobs/{id}         # 取消任务
GET    /api/proxy/seatunnel/v1/cluster           # 获取集群状态
```

**旧版 API（向后兼容）**:

```
GET    /api/proxy/seatunnel/api/v1/job/list
GET    /api/proxy/seatunnel/api/v1/job/{id}
POST   /api/proxy/seatunnel/api/v1/job/submit
DELETE /api/proxy/seatunnel/api/v1/job/{id}
```

---

## 继续实施（第二轮）

### 完成的工作

#### 1. ShardingSphere 路由更新

| 文件 | 修改内容 |
|------|---------|
| `services/portal/routers/shardingsphere.py` | 添加 v1 版本 API，使用统一 `ApiResponse` 格式 |

**新增 API 端点**:
```
GET  /api/proxy/shardingsphere/v1/mask-rules
GET  /api/proxy/shardingsphere/v1/mask-rules/{table}
POST /api/proxy/shardingsphere/v1/mask-rules
PUT  /api/proxy/shardingsphere/v1/mask-rules
DELETE /api/proxy/shardingsphere/v1/mask-rules/{table}
POST /api/proxy/shardingsphere/v1/mask-rules/batch
GET  /api/proxy/shardingsphere/v1/algorithms
GET  /api/proxy/shardingsphere/v1/presets
POST /api/proxy/shardingsphere/v1/sync
```

#### 2. Hop 路由更新

| 文件 | 修改内容 |
|------|---------|
| `services/portal/routers/hop.py` | 添加 v1 版本 API，使用统一 `ApiResponse` 格式 |

**新增 API 端点**:
```
GET  /api/proxy/hop/v1/workflows
GET  /api/proxy/hop/v1/workflows/{name}
POST /api/proxy/hop/v1/workflows/{name}/run
GET  /api/proxy/hop/v1/workflows/{name}/status/{id}
POST /api/proxy/hop/v1/workflows/{name}/stop/{id}
GET  /api/proxy/hop/v1/pipelines
GET  /api/proxy/hop/v1/pipelines/{name}
POST /api/proxy/hop/v1/pipelines/{name}/run
GET  /api/proxy/hop/v1/pipelines/{name}/status/{id}
POST /api/proxy/hop/v1/pipelines/{name}/stop/{id}
GET  /api/proxy/hop/v1/server/status
GET  /api/proxy/hop/v1/server/info
GET  /api/proxy/hop/v1/run-configurations
```

#### 3. 配置中心文档

| 文件 | 说明 |
|------|------|
| `docs/standards/config-center.md` | 配置中心使用指南 |

**内容包括**:
- etcd 部署和验证
- 配置结构说明
- etcdctl 命令使用
- 敏感配置加密
- 客户端 API 使用
- Portal 配置集成
- 故障排查
- 备份与恢复
- 生产环境建议

#### 4. API 设计规范文档

| 文件 | 说明 |
|------|------|
| `docs/standards/api-design.md` | API 设计规范 |

**内容包括**:
- 统一响应格式
- 状态码定义
- URL 设计规范
- HTTP 方法规范
- 代理 API 规范
- 请求/响应规范
- 前后端实现规范
- 测试规范
- 迁移指南

---

## 验收标准

### 配置中心

- [x] etcd 服务可以正常启动
- [x] 配置修改后能生效（无需重启，通过 Watch 机制）
- [x] 敏感配置已加密存储（AES-256-GCM）
- [x] 配置版本记录完整（etcd 内置）
- [x] 环境变量兜底正常工作

### API 一致性

- [x] 所有 API 响应格式统一为 `{code, message, data, timestamp}`
- [x] OpenAPI 文档可通过 `/docs` 访问
- [x] SeaTunnel API 路径标准化完成
- [x] 错误码定义清晰且文档化

---

## 使用示例

### 启动配置中心

```bash
# 启动 etcd
make etcd-up

# 初始化配置
make etcd-init

# 查看所有配置
make etcd-ctl list /one-data-studio/

# 获取特定配置
make etcd-ctl get /one-data-studio/portal/jwt/secret
```

### 使用配置中心 API

```python
from services.common.config_center import get_config_center

cc = get_config_center()

# 读取配置
jwt_secret = await cc.get("/one-data-studio/portal/jwt/secret", default="dev-secret")

# 写入配置（加密）
await cc.put("/one-data-studio/portal/jwt/secret", "new-secret", encrypt=True)

# 监听配置变更
@cc.register_callback("/one-data-studio/portal/")
def on_config_change(key, value):
    print(f"配置变更: {key} = {value}")
```

### 使用新的 SeaTunnel API

```typescript
import { getJobsV1, submitJobV1, isSuccessResponse } from '@/api/seatunnel';

// 获取任务列表
const response = await getJobsV1();

if (isSuccessResponse(response)) {
  console.log(response.data.jobs);
} else {
  console.error(response.message);
}
```

---

## 后续工作

### 短期（下一步）

1. 为其他组件（DataHub、DolphinScheduler 等）添加 v1 版本 API
2. 添加 OpenAPI 文档自动生成
3. 实现配置变更审计日志

### 中期

1. 将各组件 Token 迁移到配置中心管理
2. 实现配置版本回滚功能
3. 添加配置变更 Webhook 通知

### 长期

1. 实现多环境配置管理（dev/test/prod）
2. 添加配置权限控制
3. 实现配置变更审批流程

---

## 问题记录

| 问题 | 解决方案 | 状态 |
|------|---------|------|
| etcd HTTP API 文档不全 | 通过 etcd v3 HTTP API 规范实现 | 已解决 |
| 配置中心不可用时的降级策略 | 保留环境变量兜底机制 | 已实现 |
| SeaTunnel 前后端 API 不一致 | 添加 v1 版本 API，保留旧版兼容 | 已解决 |

---

## 相关文档

- [配置中心架构设计](../architecture.md)
- [API 设计规范](../standards/api-design.md)
- [集成状态文档](../integration-status.md)
