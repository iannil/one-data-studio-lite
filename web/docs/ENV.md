# Environment Variables Reference

本文档列出 ONE-DATA-STUDIO-LITE 前端相关的环境变量。

---

## 前端环境变量

前端项目使用 Vite 的环境变量系统。环境变量定义在 `.env` 文件中。

### 变量列表

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `/api` | 否 |
| `VITE_APP_TITLE` | 应用标题 | `ONE-DATA-STUDIO` | 否 |
| `VITE_APP_VERSION` | 应用版本 | `0.0.0` | 否 |

### 示例配置

```bash
# .env.development
VITE_API_BASE_URL=/api
VITE_APP_TITLE=ONE-DATA-STUDIO (Dev)
VITE_APP_VERSION=0.0.0

# .env.production
VITE_API_BASE_URL=https://api.example.com
VITE_APP_TITLE=ONE-DATA-STUDIO
VITE_APP_VERSION=1.0.0
```

---

## 后端环境变量

后端环境变量定义在项目根目录的 `.env.example` 文件中。

### 安全配置

| 变量名 | 说明 | 格式 | 必填 |
|--------|------|------|------|
| `JWT_SECRET` | JWT 签名密钥 | 32位随机字符串 | 是 |
| `JWT_EXPIRE_HOURS` | Token 有效期 | 小时数 (默认: 24) | 否 |
| `JWT_REFRESH_THRESHOLD_MINUTES` | Token 刷新阈值 | 分钟数 (默认: 30) | 否 |
| `ENVIRONMENT` | 环境标识 | `development` / `production` | 是 |
| `INTERNAL_TOKEN` | 服务间通信 Token | 32位随机字符串 | 是 |

### etcd 配置中心

| 变量名 | 说明 | 格式 | 必填 |
|--------|------|------|------|
| `ETCD_ENDPOINTS` | etcd 服务地址 | `http://host:port` | 否 |
| `ENABLE_CONFIG_CENTER` | 启用配置中心 | `true` / `false` | 否 |
| `CONFIG_CACHE_TTL` | 配置缓存过期时间 | 秒数 (默认: 60) | 否 |
| `CONFIG_ENCRYPTION_KEY` | 配置加密密钥 | Base64 编码的 Fernet key | 否 |

### 用户认证配置

| 变量名 | 说明 | 格式 | 必填 |
|--------|------|------|------|
| `DEV_USERS` | 开发环境用户 | JSON 格式 | 否 |

### 外部平台认证

| 变量名 | 说明 | 获取方式 |
|--------|------|---------|
| `PORTAL_DATAHUB_TOKEN` | DataHub Personal Access Token | DataHub Web UI → Settings → Access Tokens |
| `META_SYNC_DATAHUB_WEBHOOK_SECRET` | DataHub Webhook 签名密钥 | 自定义 (生产环境必填) |
| `PORTAL_DOLPHINSCHEDULER_TOKEN` | DolphinScheduler Token | DS Web UI → Security Center → Token Management |
| `PORTAL_SUPERSET_ADMIN_USER` | Superset 管理员用户名 | 默认: `admin` |
| `PORTAL_SUPERSET_ADMIN_PASSWORD` | Superset 管理员密码 | 自定义 (生产环境必改) |

### LLM 配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_BASE_URL` | Ollama API 地址 | `http://localhost:31434` |
| `LLM_MODEL` | 模型名称 | `qwen2.5:7b` |

### 子系统地址

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORTAL_CUBE_STUDIO_URL` | Cube-Studio 地址 | `http://localhost:30080` |
| `PORTAL_SUPERSET_URL` | Superset 地址 | `http://localhost:8088` |
| `PORTAL_DATAHUB_URL` | DataHub Web 地址 | `http://localhost:9002` |
| `PORTAL_DATAHUB_GMS_URL` | DataHub GMS 地址 | `http://localhost:8081` |
| `PORTAL_DOLPHINSCHEDULER_URL` | DolphinScheduler 地址 | `http://localhost:12345` |
| `PORTAL_HOP_URL` | Apache Hop 地址 | `http://localhost:8083` |
| `PORTAL_SEATUNNEL_URL` | SeaTunnel 地址 | `http://localhost:5802` |

### 二开服务地址

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORTAL_NL2SQL_URL` | NL2SQL 服务 | `http://localhost:8011` |
| `PORTAL_AI_CLEANING_URL` | AI 清洗服务 | `http://localhost:8012` |
| `PORTAL_METADATA_SYNC_URL` | 元数据同步服务 | `http://localhost:8013` |
| `PORTAL_DATA_API_URL` | 数据 API 服务 | `http://localhost:8014` |
| `PORTAL_SENSITIVE_DETECT_URL` | 敏感数据检测 | `http://localhost:8015` |
| `PORTAL_AUDIT_LOG_URL` | 审计日志服务 | `http://localhost:8016` |

### 其他配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORTAL_APP_PORT` | Portal 服务端口 | `8010` |
| `PORTAL_DEBUG` | 调试模式 | `false` |
| `DATABASE_URL` | 数据库连接 URL | - |

---

## 配置文件位置

```
one-data-studio-lite/
├── .env                    # 主配置文件 (不提交到 Git)
├── .env.example            # 配置模板
├── .env.development        # 开发环境配置
├── .env.production         # 生产环境配置
└── services/
    └── .env.example        # 服务配置模板
```

---

## 生成安全密钥

### JWT Secret

```bash
openssl rand -hex 32
```

### Config Encryption Key (Fernet)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Internal Token

```bash
openssl rand -hex 32
```

---

## 最佳实践

1. **永远不要**将 `.env` 文件提交到版本控制
2. **始终**提供 `.env.example` 作为模板
3. **生产环境**必须修改所有默认密钥和密码
4. **使用强随机字符串**作为 JWT Secret
5. **定期轮换**敏感凭证
