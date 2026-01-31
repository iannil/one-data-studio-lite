# 安全加固与 LLM 优化开发报告

**完成时间**: 2026-01-30
**执行人**: Claude Code

---

## 概述

本次开发完成了 ONE-DATA-STUDIO-LITE 的安全加固和 LLM 调用优化，解决了以下问题：

1. DataHub Webhook 无签名验证 → 添加 HMAC-SHA256 签名验证
2. Token 配置缺失 → 完善配置说明和启动检查
3. 硬编码凭据 → 移至环境变量配置
4. LLM 无重试机制 → 创建统一 LLM 客户端，支持重试和缓存
5. JSON 解析静默失败 → 改进错误处理，记录日志和提供 fallback

---

## 第一阶段：安全加固 ✅

### 1.1 DataHub Webhook 签名验证

**新增文件**: `services/common/webhook_security.py`

实现内容：
- `compute_signature()`: 计算 HMAC-SHA256 签名
- `verify_signature()`: 验证签名（使用 `hmac.compare_digest` 防时序攻击）
- `WebhookSignatureVerifier`: FastAPI 依赖注入类
- `create_webhook_verifier()`: 工厂函数，支持开发/生产环境区分

特性：
- 支持 `X-DataHub-Signature` 头（格式: `sha256=<hex>`）
- 开发环境允许无签名请求（记录警告）
- 生产环境强制签名验证

**修改文件**: `services/metadata_sync/config.py`

新增配置：
```python
DATAHUB_WEBHOOK_SECRET: str  # Webhook 签名密钥
ENVIRONMENT: str             # 环境标识
```

**修改文件**: `services/metadata_sync/main.py`

- 添加 `webhook_verifier` 依赖
- `receive_metadata_event` 端点现在验证签名
- 手动解析 JSON body（验证后）

### 1.2 Token 配置完善

**修改文件**: `services/.env.example`

新增配置项：
```
ENVIRONMENT=development
META_SYNC_DATAHUB_WEBHOOK_SECRET=
INTERNAL_TOKEN=
LLM_BASE_URL=http://localhost:31434
LLM_MODEL=qwen2.5:7b
DEV_USERS={"admin": {...}}
```

添加详细说明：
- 如何获取 DataHub Token
- 如何配置 Webhook Secret
- 如何配置开发用户

### 1.3 移除硬编码凭据

**修改文件**: `services/portal/config.py`

- 新增 `_get_dev_users()` 函数，从环境变量读取用户配置
- 新增 `DEV_USERS` 配置项
- `validate_security()` 新增用户配置检查
- 生产环境使用默认凭据会抛出异常

**修改文件**: `services/portal/main.py`

- 移除硬编码 `DEV_USERS` 字典
- 登录逻辑使用 `settings.DEV_USERS`

---

## 第二阶段：LLM 调用优化 ✅

### 2.1 统一 LLM 客户端

**新增文件**: `services/common/llm_client.py`

实现内容：
- `LLMConfig`: 配置模型（URL、模型名、重试策略、缓存策略）
- `LLMError`: 自定义异常，包含 code 和 retryable 属性
- `LLMResponse`: 响应模型，包含 cached 标志
- `LLMClient`: 主客户端类

特性：
- **重试机制**: 使用 tenacity 实现指数退避重试
  - 默认最多重试 3 次
  - 等待时间 1-10 秒指数增长
  - 仅对网络错误和 5xx 错误重试
- **缓存机制**: 使用 cachetools.TTLCache
  - 默认 TTL: 1 小时
  - 默认容量: 1000 条
  - 缓存键: `hash(model + system + prompt)`
- **便捷函数**: `call_llm()` 简化调用

### 2.2 重构 nl2sql 服务

**修改文件**: `services/nl2sql/main.py`

- 移除 `httpx` 直接调用
- 使用 `call_llm()` 函数
- 错误处理使用 `LLMError`

### 2.3 重构 ai_cleaning 服务

**修改文件**: `services/ai_cleaning/main.py`

- 使用统一 LLM 客户端
- 新增 `_parse_llm_json_response()` 函数
  - 记录警告日志（不再静默失败）
  - 支持提取 markdown 代码块中的 JSON
- JSON 解析失败时生成默认规则建议
  - 根据检测到的问题类型生成 fallback 规则

### 2.4 重构 sensitive_detect 服务

**修改文件**: `services/sensitive_detect/main.py`

- `classify_data` 端点使用 `call_llm()`
- 启用缓存（相同样本不重复调用）
- 错误时抛出 AppException 而非静默失败

---

## 文件变更汇总

### 新增文件

```
services/common/webhook_security.py    # Webhook 签名验证模块
services/common/llm_client.py          # 统一 LLM 客户端
docs/reports/completed/2026-01-30-security-llm-optimization.md  # 本报告
```

### 修改文件

```
services/metadata_sync/config.py       # 添加 WEBHOOK_SECRET、ENVIRONMENT
services/metadata_sync/main.py         # 添加签名验证
services/portal/config.py              # 添加 DEV_USERS 配置
services/portal/main.py                # 移除硬编码用户
services/nl2sql/main.py                # 使用 LLM 客户端
services/ai_cleaning/main.py           # 使用 LLM 客户端 + 改进错误处理
services/sensitive_detect/main.py      # 使用 LLM 客户端
services/.env.example                  # 完善配置说明
```

---

## 验证方案

### 第一阶段验证

```bash
# 1. 发送无签名 Webhook 请求（开发环境应警告但允许）
curl -X POST http://localhost:8013/api/metadata/webhook \
  -H "Content-Type: application/json" \
  -d '{"entity_urn":"urn:li:dataset:(urn:li:dataPlatform:mysql,test,PROD)","change_type":"UPSERT"}'

# 2. 发送错误签名 Webhook 请求（应返回 401）
curl -X POST http://localhost:8013/api/metadata/webhook \
  -H "Content-Type: application/json" \
  -H "X-DataHub-Signature: sha256=invalid" \
  -d '{"entity_urn":"urn:li:dataset:(urn:li:dataPlatform:mysql,test,PROD)","change_type":"UPSERT"}'

# 3. 发送正确签名 Webhook 请求
# 先计算签名: echo -n '<body>' | openssl dgst -sha256 -hmac '<secret>'
curl -X POST http://localhost:8013/api/metadata/webhook \
  -H "Content-Type: application/json" \
  -H "X-DataHub-Signature: sha256=<computed_signature>" \
  -d '{"entity_urn":"urn:li:dataset:(urn:li:dataPlatform:mysql,test,PROD)","change_type":"UPSERT"}'

# 4. 生产环境启动检查
ENVIRONMENT=production python -m services.portal.main
# 应检查 JWT_SECRET 和 DEV_USERS 配置
```

### 第二阶段验证

```bash
# 1. LLM 服务不可用时测试重试
# 停止 Ollama 服务后调用 NL2SQL，观察日志中的重试信息

# 2. 测试缓存
# 连续两次相同请求，第二次应从缓存返回（响应更快）
curl -X POST http://localhost:8011/api/nl2sql/query \
  -H "Authorization: Bearer <token>" \
  -d '{"question":"查询所有用户"}'

# 3. 测试 JSON 解析失败处理
# 观察 ai_cleaning 服务日志，解析失败应有警告
```

---

## 依赖更新

需要安装新依赖：

```bash
pip install tenacity cachetools
```

或更新 requirements.txt：

```
tenacity>=8.0.0
cachetools>=5.0.0
```

---

## 遗留问题

1. **SeaTunnel API 文档**: 尚未创建 API 映射文档
2. **API 版本管理**: 代理路由尚未添加版本前缀
3. **LLM 缓存持久化**: 当前使用内存缓存，重启后清空

---

## 下一步建议

1. 创建 SeaTunnel API 映射文档 (`docs/api/seatunnel-mapping.md`)
2. 考虑使用 Redis 实现 LLM 缓存持久化
3. 添加 LLM 调用指标监控（成功率、延迟、缓存命中率）
4. 实现用户数据库存储（替代 DEV_USERS 配置）
