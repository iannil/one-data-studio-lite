# ONE-DATA-STUDIO-LITE - 阶段四：监控和可观测性 - 完成报告

> **完成日期**: 2026-01-30
> **阶段**: Phase 4 - 监控和可观测性
> **状态**: ✅ 已完成

---

## 一、实施概述

### 1.1 目标

实现分布式追踪和日志聚合，提升系统可观测性，便于问题排查和性能分析。

### 1.2 实施内容

| 任务 | 状态 | 说明 |
|-----|------|------|
| OpenTelemetry 分布式追踪 | ✅ 完成 | 追踪中间件、装饰器、上下文管理 |
| Loki 日志聚合 | ✅ 完成 | 日志存储、查询、保留策略 |
| Promtail 日志采集 | ✅ 完成 | Docker 容器日志、服务日志采集 |
| Grafana 监控面板 | ✅ 完成 | 仪表板、数据源、告警规则 |
| 统一日志模块 | ✅ 完成 | JSON/文本格式化、日志辅助类 |

---

## 二、详细实现

### 2.1 OpenTelemetry 分布式追踪

**文件**: `services/common/telemetry.py`

**实现内容**:

```python
# 遥测设置
def setup_telemetry(service_name: str, endpoint: Optional[str])
    -> tuple[TracerProvider, MeterProvider]

# 追踪中间件
class TracingMiddleware:
    - 自动添加 trace_id 到响应头
    - 记录请求耗时
    - 创建 Span 用于追踪

# 装饰器
@traced(operation_name: str = None)  # 函数追踪
@timed(operation_name: str = None)   # 性能计时

# 追踪上下文
class TraceContext:
    - get_current_span_id()
    - get_current_trace_id()
    - inject_headers()
    - extract_headers()
```

**使用示例**:

```python
# 中间件集成
app.add_middleware(TracingMiddleware, service_name="portal")

# 装饰器使用
@traced("external_api_call")
async def call_external_api():
    ...

# 上下文追踪
trace_id = TraceContext.get_current_trace_id()
```

---

### 2.2 Loki 日志聚合

**文件**: `deploy/loki/config/loki-config.yaml`

**实现内容**:

| 配置项 | 值 | 说明 |
|-------|-----|------|
| 存储引擎 | TSDB | 时序数据库 |
| 索引周期 | 24h | 每日一个索引 |
| 保留策略 | 30d (INFO), 7d (DEBUG) | 分级保留 |
| ERROR 保留 | 永久 | 错误日志永久保留 |
| 压缩周期 | 24h | 自动压缩 |

**日志保留规则**:

```yaml
rules:
  - {level="ERROR"} → keep      # 永久保留
  - {job="portal"} → keep        # 永久保留
  - {level="DEBUG"} → delete     # 生产环境删除
```

---

### 2.3 Promtail 日志采集

**文件**: `deploy/loki/config/promtail/config.yaml`

**采集源**:

| 源 | 路径 | 标签 |
|----|------|------|
| Docker 容器 | unix:///var/run/docker.sock | service, subsystem |
| Portal | /var/log/portal/*.log | job=portal |
| NL2SQL | /var/log/nl2sql/*.log | job=nl2sql |
| AI Cleaning | /var/log/ai_cleaning/*.log | job=ai_cleaning |
| 系统日志 | /var/log/syslog, auth.log | job=system |

**标签结构**:

```
service: portal | nl2sql | ai_cleaning | metadata_sync | data_api | sensitive_detect | audit_log
subsystem: superset | datahub | dolphinscheduler | seatunnel | hop | shardingsphere | cube-studio
internal_service: nl2sql | ai_cleaning | metadata_sync | sensitive_detect | audit_log
level: DEBUG | INFO | WARN | ERROR | CRITICAL
```

---

### 2.4 Grafana 监控面板

**仪表板**:

1. **Service Health** (服务健康)
   - 服务状态卡片（UP/DOWN）
   - 日志级别分布趋势
   - 日志量统计
   - 服务健康概览表

2. **API Performance** (API 性能)
   - 响应时间统计（平均、P50、P95、P99）
   - 请求速率
   - 错误率趋势
   - 慢查询 Top 10

3. **Log Analysis** (日志分析)
   - 日志级别统计卡片
   - 日志量趋势
   - 日志分布饼图
   - 异常/超时日志检测
   - 最近错误日志

**数据源**:

| 名称 | 类型 | URL |
|-----|------|-----|
| Loki | loki | http://loki:3100 |
| Prometheus | prometheus | http://prometheus:9090 |

---

### 2.5 告警规则

**文件**: `deploy/loki/config/alert-rules.yml`

**规则分类**:

| 类别 | 规则示例 | 严重级别 |
|-----|---------|---------|
| 服务健康 | ServiceNoLogs (10分钟无日志) | critical |
| 错误率 | HighErrorRate (>5%) | warning |
| 错误率 | CriticalErrorRate (>15%) | critical |
| 异常检测 | ExceptionSpike (>50/2min) | warning |
| 超时检测 | TimeoutSpike (>20/5min) | warning |
| 连接失败 | ConnectionFailure (>10/1min) | critical |
| LLM 调用 | HighLLMFailureRate (>10/5min) | warning |
| 数据库 | DatabasePoolExhausted (>5/1min) | critical |
| API 延迟 | HighAPILatency (P95 > 3000ms) | warning |
| 资源 | HighMemoryUsage | critical |
| 资源 | DiskSpaceLow | critical |
| 安全 | HighAuthFailureRate (>50/5min) | warning |
| 安全 | SQLInjectionAttempt | critical |

---

### 2.6 统一日志模块

**文件**: `services/common/logging.py`

**功能**:

```python
# JSON 格式化器
class JsonFormatter:
    - 结构化日志输出
    - 自动添加时间、服务名、环境
    - 支持异常、追踪、上下文字段

# 纯文本格式化器
class PlainTextFormatter:
    - 人类可读格式
    - 支持颜色输出（开发环境）
    - 紧凑格式

# 日志设置
def setup_logging(service, level, environment, log_file, json_format)

# 上下文管理器
with log_context(logger, user_id="123", request_id="abc"):
    logger.info("...")  # 自动包含上下文

# 计时管理器
with log_duration(logger, "Database query"):
    ...  # 自动记录耗时

# 日志辅助类
LogHelper.log_request(method, path, status, duration_ms)
LogHelper.log_error(error, message)
LogHelper.log_external_call(service, endpoint, status, duration_ms)
```

---

## 三、Makefile 命令

```bash
# 监控系统
make monitoring-up      # 启动完整监控系统 (Loki + Promtail + Grafana)
make monitoring-down    # 停止监控系统
make monitoring-logs    # 查看监控系统日志
make monitoring-status  # 查看监控系统状态

# 单独控制
make loki-up            # 仅启动 Loki
make loki-down          # 停止 Loki
make loki-logs          # 查看 Loki 日志
make promtail-logs      # 查看 Promtail 日志
make grafana-up         # 仅启动 Grafana
make grafana-down       # 停止 Grafana
make grafana-logs       # 查看 Grafana 日志
```

---

## 四、部署步骤

### 4.1 启动监控系统

```bash
# 1. 创建网络（如果不存在）
docker network create one-data-studio-network

# 2. 启动监控系统
make monitoring-up

# 3. 等待服务启动
sleep 10

# 4. 访问 Grafana
# URL: http://localhost:3000
# 用户名: admin
# 密码: admin123
```

### 4.2 配置服务日志

```bash
# 1. 确保服务日志目录存在
mkdir -p /var/log/portal
mkdir -p /var/log/nl2sql
mkdir -p /var/log/ai_cleaning

# 2. 配置服务使用统一日志模块
# 在服务启动时调用:
# setup_logging(service="portal", level="INFO", json_format=True)
```

### 4.3 配置追踪

```bash
# 1. 安装 OpenTelemetry 依赖
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation

# 2. 启用追踪中间件
# 在 FastAPI 应用中:
# app.add_middleware(TracingMiddleware, service_name="portal")

# 3. 可选：部署 Jaeger
docker run -d -p 16686:16686 -p 14250:14250 jaegertracing/all-in-one:latest
```

---

## 五、验收标准

### 5.1 日志聚合

- [x] Loki 服务正常运行
- [x] Promtail 采集 Docker 容器日志
- [x] Promtail 采集服务日志文件
- [x] 日志包含正确的标签
- [x] 日志保留策略正确配置

### 5.2 监控面板

- [x] Grafana 可访问 (http://localhost:3000)
- [x] Loki 数据源配置正确
- [x] 仪表板自动加载
- [x] 仪表板显示正确数据
- [x] 日志查询功能正常

### 5.3 告警规则

- [x] 告警规则已配置
- [x] 告警规则语法正确
- [x] 告警严重级别正确

### 5.4 分布式追踪

- [x] 追踪中间件已实现
- [x] 装饰器已实现
- [x] 追踪上下文管理正常
- [x] 与 Jaeger 集成（预留）

---

## 六、遗留问题

| 问题 | 严重程度 | 计划 |
|-----|---------|-----|
| Prometheus 未部署 | ⚠️ 低 | 下一阶段部署 Prometheus 用于指标采集 |
| Jaeger 未部署 | ⚠️ 低 | 下一阶段部署 Jaeger 用于追踪可视化 |
| 告警通知未配置 | ⚠️ 低 | 需要配置告警通知渠道（邮件/钉钉/企微） |

---

## 七、下一步建议

1. **部署 Prometheus**: 用于采集系统和应用指标
2. **部署 Jaeger**: 用于分布式追踪可视化
3. **配置告警通知**: 集成钉钉/企微/邮件通知
4. **完善仪表板**: 根据实际使用情况调整仪表板
5. **性能优化**: 调整日志采样率，减少性能开销

---

## 八、相关文档

- [配置中心使用指南](../standards/config-center.md)
- [API 设计规范](../standards/api-design.md)
- [安全配置指南](../standards/security.md)
- [统一认证框架设计](../standards/unified-auth.md)
- [集成状态总览](../integration-status.md)

---

**报告完成时间**: 2026-01-30
**报告版本**: 1.0
