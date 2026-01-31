# 配置中心使用指南

**版本**: 1.0
**更新日期**: 2026-01-30

---

## 概述

ONE-DATA-STUDIO-LITE 使用 etcd 作为配置中心，提供统一的配置管理、热更新和版本控制功能。

### 核心功能

- **配置集中存储**: 所有配置存储在 etcd KV 存储中
- **配置热更新**: Watch 机制监听配置变更，自动重新加载
- **配置版本控制**: etcd 内置版本管理，支持查看历史
- **敏感配置加密**: AES-256-GCM 加密存储敏感配置
- **环境变量兜底**: etcd 不可用时自动降级到环境变量

---

## 部署

### 快速启动

```bash
# 启动 etcd 配置中心
make etcd-up

# 初始化配置结构
make etcd-init
```

### 手动部署

```bash
cd deploy/etcd
docker compose up -d
```

### 验证部署

```bash
# 检查 etcd 健康状态
docker ps | grep etcd

# 使用 etcdctl 连接
make etcd-ctl list /one-data-studio/
```

---

## 配置结构

配置在 etcd 中的存储结构如下：

```
/one-data-studio/
├── /portal/                    # Portal 服务配置
│   ├── /database/
│   │   ├── url                 # 数据库连接 URL
│   │   └── pool_size           # 连接池大小
│   └── /jwt/
│       └── secret              # JWT 密钥（加密）
├── /seatunnel/                 # SeaTunnel 配置
│   └── /api/
│       └── token               # API Token（加密）
├── /superset/                  # Superset 配置
│   └── /auth/
│       ├── username            # 用户名
│       └── password            # 密码（加密）
├── /dolphinscheduler/          # DolphinScheduler 配置
│   └── /token                  # Token（加密）
└── /global/                    # 全局配置
    ├── /log/
    │   └── level               # 日志级别
    └── /llm/
        ├── base_url            # LLM 服务地址
        └── model               # 默认模型
```

---

## etcdctl 使用

### 基本命令

```bash
# 进入 etcdctl 交互模式
make etcd-ctl

# 或直接执行命令
bash deploy/etcd/etcdctl.sh <command> [arguments]
```

### 常用操作

```bash
# 获取配置
./etcdctl.sh get /one-data-studio/portal/jwt/secret

# 设置配置
./etcdctl.sh put /one-data-studio/portal/jwt/secret "my-secret-key"

# 删除配置
./etcdctl.sh del /one-data-studio/portal/jwt/secret

# 列出所有配置
./etcdctl.sh list /one-data-studio/

# 列出特定服务的配置
./etcdctl.sh list /one-data-studio/portal/

# 监控配置变更
./etcdctl.sh watch /one-data-studio/portal/

# 查看配置历史
./etcdctl.sh history /one-data-studio/portal/jwt/secret

# 备份配置
./etcdctl.sh backup
```

---

## 敏感配置加密

### 生成加密密钥

```bash
# Python 方式
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 或使用 OpenSSL 生成 Base64 编码的密钥
openssl rand -base64 32
```

### 配置加密密钥

将生成的密钥设置到环境变量：

```bash
export CONFIG_ENCRYPTION_KEY=<your-base64-key>
```

或在 `services/.env` 中配置：

```bash
CONFIG_ENCRYPTION_KEY=<your-base64-key>
```

### 加密存储配置

```python
from services.common.config_center import get_config_center

cc = get_config_center()

# 加密存储
await cc.put("/one-data-studio/portal/jwt/secret", "my-secret", encrypt=True)
```

存储后的值会带有 `ENC:` 前缀，表示已加密。

---

## 客户端 API 使用

### 基本使用

```python
from services.common.config_center import get_config_center

# 获取配置中心实例
cc = get_config_center()

# 读取配置
value = await cc.get("/one-data-studio/portal/jwt/secret", default="default-value")

# 写入配置
await cc.put("/one-data-studio/portal/jwt/secret", "new-value")

# 加密写入
await cc.put("/one-data-studio/portal/jwt/secret", "sensitive-value", encrypt=True)

# 删除配置
await cc.delete("/one-data-studio/portal/jwt/secret")

# 列出配置键
keys = await cc.list_keys("/one-data-studio/portal/")
```

### 类型转换

```python
# 整数
pool_size = await cc.get_int("/one-data-studio/portal/database/pool_size", default=10)

# 浮点数
timeout = await cc.get_float("/one-data-studio/portal/timeout", default=30.0)

# 布尔值
debug = await cc.get_bool("/one-data-studio/portal/debug", default=False)

# JSON
config = await cc.get_json("/one-data-studio/portal/features", default={})
```

### 配置监听

```python
from services.common.config_center import get_config_center

cc = get_config_center()

# 方式1: 注册回调函数
def on_jwt_change(key: str, value: str):
    print(f"JWT 配置变更: {key} = {value}")
    # 重新加载配置...

cc.register_callback("/one-data-studio/portal/jwt/", on_jwt_change)

# 方式2: 使用装饰器
from services.common.config_center import watch_callback

@watch_callback("/one-data-studio/portal/")
def on_config_change(key: str, value: str):
    print(f"配置变更: {key} = {value}")
```

---

## Portal 配置集成

### 自动加载

Portal 服务启动时会自动从 etcd 加载配置：

```python
# services/portal/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化配置中心
    await init_config_center()
    yield
```

### 运行时读取

```python
from services.portal.config import get_config

# 从配置中心读取配置（优先）或环境变量
jwt_secret = await get_config("jwt/secret", default="default-secret")
```

### 运行时写入

```python
from services.portal.config import set_config

# 写入配置到配置中心
success = await set_config("jwt/secret", "new-secret", encrypt=True)
```

---

## 故障排查

### etcd 无法连接

```bash
# 检查 etcd 容器状态
docker ps | grep etcd

# 查看 etcd 日志
make etcd-logs

# 测试连接
curl http://localhost:2379/health
```

### 配置未生效

1. 检查配置是否正确写入：
   ```bash
   ./etcdctl.sh get /one-data-studio/portal/jwt/secret
   ```

2. 检查服务日志是否有配置加载错误

3. 重启服务：
   ```bash
   make services-up
   ```

### 环境变量未生效

配置中心的优先级低于环境变量，如果环境变量存在，则不会使用配置中心的值。

检查环境变量：
```bash
env | grep -i jwt
```

---

## 备份与恢复

### 备份

```bash
# 使用 etcdctl 脚本备份
make etcd-backup

# 备份文件保存到 deploy/etcd/workspace/
```

### 恢复

```bash
# 停止 etcd
make etcd-down

# 恢复备份（手动执行 docker 命令）
docker run --rm -v $(pwd)/workspace:/workspace \
    -v one-data-studio-etcd-data:/etcd-data \
    quay.io/coreos/etcd:v3.5.12 \
    etcdctl snapshot restore /workspace/etcd-backup.db --data-dir /etcd-data

# 重新启动
make etcd-up
```

---

## 生产环境建议

### 1. 启用 TLS

生产环境建议启用 etcd TLS 加密通信：

```yaml
# deploy/etcd/docker-compose.yml
environment:
  ETCD_CERT_FILE: /etc/etcd/tls/server.crt
  ETCD_KEY_FILE: /etc/etcd/tls/server.key
  ETCD_CLIENT_CERT_AUTH: "true"
  ETCD_TRUSTED_CA_FILE: /etc/etcd/tls/ca.crt
volumes:
  - ./tls:/etc/etcd/tls:ro
```

### 2. 集群部署

使用 etcd 集群提高可用性：

```yaml
ETCD_INITIAL_CLUSTER: "etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380"
ETCD_INITIAL_CLUSTER_STATE: new
```

### 3. 定期备份

设置定时任务定期备份：

```bash
# crontab
0 2 * * * cd /path/to/project && make etcd-backup
```

### 4. 监控

使用 Prometheus + Grafana 监控 etcd：

```yaml
# 启用 etcd metrics
ETCD_METRICS: basic
```

---

## 参考资料

- [etcd 官方文档](https://etcd.io/docs/)
- [etcd API 文档](https://etcd.io/docs/latest/learning/api/)
- [etcd 安全配置](https://etcd.io/docs/latest/op-guide/security/)
