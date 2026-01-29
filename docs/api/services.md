# 二开服务 API 文档

本文档描述 ONE-DATA-STUDIO-LITE 二开微服务的 API 接口。

---

## 通用说明

### 认证

除健康检查接口外，所有 API 需要 JWT 认证：

```
Authorization: Bearer <token>
```

### 响应格式

成功响应：
```json
{
  "data": { ... }
}
```

错误响应：
```json
{
  "detail": "错误描述",
  "code": 400
}
```

---

## 1. Portal - 统一门户 (:8010)

### 健康检查
```
GET /health
```

### 用户登录
```
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

### 获取子系统列表
```
GET /api/subsystems
```

---

## 2. NL2SQL - 自然语言查询 (:8011)

### 自然语言转SQL
```
POST /api/nl2sql/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "查询最近7天的订单数量",
  "database": "default"
}
```

响应：
```json
{
  "sql": "SELECT COUNT(*) FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
  "explanation": "统计最近7天的订单记录数",
  "columns": ["count"],
  "data": [{"count": 1234}]
}
```

### 获取表结构
```
GET /api/nl2sql/schema?database=default
Authorization: Bearer <token>
```

---

## 3. AI Cleaning - AI清洗推荐 (:8012)

### 分析表数据质量
```
POST /api/cleaning/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "table_name": "user_data",
  "sample_size": 1000
}
```

响应：
```json
{
  "table_name": "user_data",
  "total_rows": 50000,
  "analyzed_rows": 1000,
  "quality_score": 75,
  "issues": [
    {
      "column": "email",
      "issue_type": "null_values",
      "description": "字段 email 存在 120 个空值",
      "affected_rows": 120,
      "severity": "medium"
    }
  ]
}
```

### AI推荐清洗规则
```
POST /api/cleaning/recommend
Authorization: Bearer <token>
Content-Type: application/json

{
  "table_name": "user_data",
  "sample_size": 1000
}
```

### 生成 SeaTunnel 配置
```
POST /api/cleaning/generate-config
Authorization: Bearer <token>
Content-Type: application/json

{
  "table_name": "user_data",
  "rules": [
    {
      "rule_id": "r1",
      "name": "填充空值",
      "target_column": "email",
      "rule_type": "fill",
      "config": {"fill_value": "unknown@example.com"}
    }
  ]
}
```

---

## 4. Metadata Sync - 元数据同步 (:8013)

### 触发元数据同步
```
POST /api/metadata/sync
Authorization: Bearer <token>
Content-Type: application/json

{
  "source_type": "mysql",
  "source_config": {
    "host": "localhost",
    "port": 3306,
    "database": "mydb"
  }
}
```

### 获取同步状态
```
GET /api/metadata/sync/{job_id}
Authorization: Bearer <token>
```

### 列出元数据变更
```
GET /api/metadata/changes?since=2025-01-01
Authorization: Bearer <token>
```

---

## 5. Data API - 数据资产网关 (:8014)

### 查询数据集
```
GET /api/data/{dataset_id}?page=1&page_size=50
Authorization: Bearer <token>
```

响应：
```json
{
  "dataset_id": "orders",
  "total": 50000,
  "page": 1,
  "data": [
    {"id": 1, "user_id": 101, "amount": 99.99}
  ]
}
```

### 获取数据集 Schema
```
GET /api/data/{dataset_id}/schema
Authorization: Bearer <token>
```

### 自定义查询
```
POST /api/data/{dataset_id}/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "sql": "SELECT user_id, SUM(amount) FROM orders GROUP BY user_id",
  "page": 1,
  "page_size": 100
}
```

### 搜索数据资产
```
GET /api/assets/search?query=用户&page=1
Authorization: Bearer <token>
```

### 订阅资产变更
```
POST /api/assets/{asset_id}/subscribe
Authorization: Bearer <token>
Content-Type: application/json

{
  "notify_url": "https://example.com/webhook",
  "events": ["schema_change", "data_update"]
}
```

---

## 6. Sensitive Detect - 敏感数据检测 (:8015)

### 扫描表敏感数据
```
POST /api/sensitive/scan
Authorization: Bearer <token>
Content-Type: application/json

{
  "table_name": "user_data",
  "sample_size": 100
}
```

响应：
```json
{
  "id": "rpt123",
  "table_name": "user_data",
  "scan_time": "2025-01-29T10:00:00Z",
  "total_columns": 10,
  "sensitive_columns": 3,
  "risk_level": "high",
  "fields": [
    {
      "column_name": "phone",
      "sensitivity_level": "high",
      "detected_types": ["phone"],
      "detection_method": "regex",
      "confidence": 0.95
    }
  ]
}
```

### LLM分类敏感数据
```
POST /api/sensitive/classify
Authorization: Bearer <token>
Content-Type: application/json

{
  "data_samples": ["13800138000", "张三", "110101199001011234"],
  "context": "用户注册信息"
}
```

### 管理检测规则
```
GET /api/sensitive/rules
POST /api/sensitive/rules
```

---

## 7. Audit Log - 审计日志 (:8016)

### 记录审计事件（内部调用）
```
POST /api/audit/log
Content-Type: application/json

{
  "subsystem": "data-api",
  "event_type": "api_call",
  "user": "admin",
  "action": "GET /api/data/orders",
  "resource": "/api/data/orders",
  "status_code": 200,
  "duration_ms": 45.2
}
```

### 查询审计日志
```
GET /api/audit/logs?subsystem=portal&user=admin&page=1
Authorization: Bearer <token>
```

### 获取审计统计
```
GET /api/audit/stats
Authorization: Bearer <token>
```

响应：
```json
{
  "total_events": 15000,
  "events_by_subsystem": {
    "portal": 5000,
    "data-api": 8000,
    "nl2sql": 2000
  },
  "events_by_type": {
    "api_call": 14000,
    "login": 1000
  }
}
```

### 导出审计日志
```
POST /api/audit/export
Authorization: Bearer <token>
Content-Type: application/json

{
  "format": "csv",
  "query": {
    "subsystem": "portal",
    "user": "admin"
  }
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或令牌过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
