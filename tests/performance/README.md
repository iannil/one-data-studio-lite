# 性能测试

本目录包含使用 Locust 编写的性能测试脚本。

## 安装

```bash
pip install locust
```

## 运行

### GUI 模式（推荐用于开发调试）

```bash
locust -f tests/performance/locustfile.py
```

然后访问 http://localhost:8088

### 命令行模式（推荐用于 CI/CD）

```bash
# 使用默认参数（100 用户，运行 60 秒）
bash tests/performance/run.sh

# 自定义参数
USERS=200 SPAWN_RATE=20 RUN_TIME=120s bash tests/performance/run.sh
```

### 直接使用 locust 命令

```bash
locust -f tests/performance/locustfile.py \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 60s \
    --host http://localhost:8010 \
    --html report.html
```

## 测试场景

### PortalUser
- 模拟 Portal 服务用户
- 包含登录、健康检查、列表查询等操作
- 权重: 健康检查(5), 列表查询(3), 用户信息(2), Token验证(1)

### NL2SQLUser
- 模拟自然语言查询用户
- 包含健康检查和查询操作
- 权重: 查询(3), 健康检查(1)

### DataAPIUser
- 模拟数据 API 访问用户
- 包含资产列表、资产详情、数据查询操作
- 权重: 资产详情(5), 健康检查(2), 列表查询(3)

## 性能指标

目标:
- API P95 响应时间 < 500ms
- API P99 响应时间 < 1000ms
- 支持至少 100 并发用户
- 错误率 < 1%
