# 安全配置指南

## 概述

ONE-DATA-STUDIO-LITE 提供了多层安全保护机制，确保生产环境的安全性。

## 安全配置检查

### 方法 1：使用 API 端点

启动 Portal 服务后，访问以下端点检查安全配置：

```bash
curl http://localhost:8010/security/check
```

响应示例：

```json
{
  "security_level": "secure",
  "security_message": "安全配置良好",
  "score": 8,
  "max_score": 8,
  "is_production": false,
  "environment": "development",
  "token_status": {
    "jwt_secret_configured": true,
    "jwt_secret_strong": true,
    "datahub_token_configured": true,
    "dolphinscheduler_token_configured": true,
    "seatunnel_api_key_configured": true,
    "internal_token_configured": true,
    "webhook_secret_configured": true,
    "superset_weak_creds": false
  },
  "warnings": [],
  "recommendations": []
}
```

### 方法 2：使用 Makefile

```bash
make security-check
```

### 方法 3：启动时自动检查

Portal 服务启动时会自动检查安全配置并输出警告。

## 生成生产环境密钥

### 使用脚本生成

```bash
# 查看生成的密钥（终端输出）
make generate-secrets

# 直接导出为环境变量
make generate-secrets-env

# 写入 .env.production 文件
make generate-secrets-file
```

### 使用 Python 脚本

```bash
# export 格式输出
python scripts/generate_secrets.py --format export

# .env 文件格式
python scripts/generate_secrets.py --format env

# JSON 格式
python scripts/generate_secrets.py --format json

# 直接写入文件
python scripts/generate_secrets.py --env-file .env.production
```

## 必需的安全配置

### 1. JWT 密钥

```bash
# 生成 JWT 密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 设置环境变量
export JWT_SECRET=<生成的密钥>
```

### 2. 内部服务通信 Token

```bash
# 生成内部 Token
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 设置环境变量
export INTERNAL_TOKEN=<生成的Token>
```

### 3. Webhook 签名密钥

```bash
# 生成 Webhook 密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 设置环境变量
export META_SYNC_DATAHUB_WEBHOOK_SECRET=<生成的密钥>
```

### 4. 子系统认证 Token

#### DataHub Personal Access Token

1. 登录 DataHub Web UI
2. 进入 Settings → Access Tokens
3. 点击 "Generate Personal Access Token"
4. 复制 Token 并设置环境变量：

```bash
export PORTAL_DATAHUB_TOKEN=<your-datahub-token>
```

#### DolphinScheduler Token

1. 登录 DolphinScheduler Web UI
2. 进入 Security Center → Token Management
3. 点击 "Create Token"
4. 复制 Token 并设置环境变量：

```bash
export PORTAL_DOLPHINSCHEDULER_TOKEN=<your-ds-token>
```

#### Superset 凭据

生产环境必须修改默认凭据：

```bash
# 生成强密码
python -c "from services.common.security import generate_password; print(generate_password(20, use_special=False))"

# 设置环境变量
export SUPERSET_ADMIN_USER=admin
export SUPERSET_ADMIN_PASSWORD=<生成的强密码>
```

## 配置中心加密

如果启用配置中心，建议加密存储敏感配置：

```bash
# 生成加密密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 设置环境变量
export CONFIG_ENCRYPTION_KEY=<生成的密钥>
```

## 密码强度要求

- **最小长度**: 12 字符（生产环境推荐 16+）
- **字符类型**: 至少包含 3 种（大写、小写、数字、特殊字符）
- **禁止使用**: 常见密码、键盘序列、重复字符

## 环境变量优先级

配置加载优先级（从高到低）：

1. 环境变量
2. etcd 配置中心
3. 代码默认值

## 安全检查清单

部署到生产环境前，请确认：

- [ ] `JWT_SECRET` 已设置为强随机字符串（32+ 字符）
- [ ] `INTERNAL_TOKEN` 已设置用于服务间通信
- [ ] `SEA_TUNNEL_API_KEY` 已配置
- [ ] `META_SYNC_DATAHUB_WEBHOOK_SECRET` 已配置
- [ ] `PORTAL_DATAHUB_TOKEN` 已配置
- [ ] `PORTAL_DOLPHINSCHEDULER_TOKEN` 已配置
- [ ] Superset 默认凭据已修改
- [ ] `ENVIRONMENT=production` 已设置
- [ ] `CONFIG_ENCRYPTION_KEY` 已设置（如果使用配置中心）
- [ ] 数据库密码已修改为强密码

## 故障排查

### 警告：JWT_SECRET 使用默认值

```bash
export JWT_SECRET=$(openssl rand -hex 32)
```

### 警告：Superset 使用默认凭据

```bash
export SUPERSET_ADMIN_PASSWORD=$(python -c "from services.common.security import generate_password; print(generate_password(20, use_special=False))")
```

### 警告：Token 未配置

请参考各子系统 Token 获取方法进行配置。

## 工具函数

### Python 代码中使用

```python
from services.common.security import (
    generate_password,
    generate_jwt_secret,
    generate_webhook_secret,
    check_password_strength,
    mask_token,
)

# 生成密码
password = generate_password(16)

# 检查密码强度
strength, issues = check_password_strength(password)

# 掩码 Token
masked = mask_token("abcd1234efgh5678")
# 输出: abcd****5678
```
